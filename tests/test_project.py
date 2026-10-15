import hashlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import patching
import ci_build
import upstream
import quest_usb


def synthetic_binary():
    # Artificial Mach-O fixture, not copied from Meta. One file-backed segment.
    b = bytearray(0x1200)
    struct.pack_into('>II', b, 0, 0xcafebabe, 1)
    struct.pack_into('>IIIII', b, 8, 0x0100000c, 0, 0x200, 0x1000, 9)
    struct.pack_into('<IIIIIIII', b, 0x200, 0xfeedfacf, 0x0100000c, 0, 2, 1, 152, 0, 0)
    struct.pack_into('<II', b, 0x220, 0x19, 152)
    struct.pack_into('<QQQQ', b, 0x220 + 24, 0x100000000, 0x1000, 0, 0x1000)
    struct.pack_into('<I', b, 0x220 + 64, 1)
    struct.pack_into('<I', b, 0x220 + 72 + 48, 0x400)
    b[0x600:0x604] = b'ABCD'
    m = {'executable_sha256': hashlib.sha256(b).hexdigest(), 'patches': [
        {'address': '0x100000400', 'before': b'ABCD'.hex(), 'after': b'EFGH'.hex(), 'purpose': 'fixture'}]}
    return b, m


class PatchingTests(unittest.TestCase):
    def test_patch_and_loader_command_without_changing_length(self):
        b, m = synthetic_binary()
        result, report = patching.patch_executable(b, m)
        self.assertEqual(result[0x600:0x604], b'EFGH')
        self.assertEqual(len(result), len(b))
        self.assertIn(b'@executable_path/libQuestVDUSB.dylib\0', result)
        self.assertEqual(len(report), 1)
        with self.assertRaisesRegex(ValueError, 'hash'):
            patching.patch_executable(result, m)

    def test_unknown_hash_and_instruction_refused(self):
        b, m = synthetic_binary()
        m['patches'][0]['before'] = '00000000'
        with self.assertRaisesRegex(ValueError, 'instruction'):
            patching.patch_executable(b, m)
        b[0] = 0
        with self.assertRaisesRegex(ValueError, 'hash'):
            patching.patch_executable(b, m)

    def test_header_padding_is_not_overwritten(self):
        b, m = synthetic_binary()
        b[0x200 + 32 + 152] = 1
        m['executable_sha256'] = hashlib.sha256(b).hexdigest()
        with self.assertRaisesRegex(ValueError, 'padding'):
            patching.patch_executable(b, m)

    def test_malformed_segment_is_rejected(self):
        b, m = synthetic_binary()
        struct.pack_into('<Q', b, 0x220 + 48, 0xffffffff)
        m['executable_sha256'] = hashlib.sha256(b).hexdigest()
        with self.assertRaisesRegex(ValueError, 'Segment outside'):
            patching.patch_executable(b, m)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.known = upstream.manifests()
        self.m = self.known[max(self.known, key=upstream.version_tuple)]
        self.meta = {'version': self.m['version'], 'sha256': self.m['dmg_sha256'], 'size': self.m['size']}

    def test_duplicate_check_does_not_download(self):
        with patch('upstream.download', side_effect=AssertionError('DMG fetched')):
            p = ci_build.make_plan('someone/fork', self.known, self.meta, lookup=lambda *a: {'id': 1})
            self.assertFalse(p['needs_build'])

    def test_patch_revision_changes_artifact_identity(self):
        before = ci_build.artifact_name(self.m)
        self.m['patch_revision'] += 1
        self.assertNotEqual(before, ci_build.artifact_name(self.m))

    def test_build_inputs_change_artifact_identity(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / 'packaging').mkdir()
            script = root / 'packaging/Readme.html'
            script.write_text('first')
            before = ci_build.artifact_name(self.m, root)
            script.write_text('second')
            self.assertNotEqual(before, ci_build.artifact_name(self.m, root))

    def test_rebuild_skips_lookup(self):
        p = ci_build.make_plan('someone/fork', self.known, self.meta, rebuild=True,
                              lookup=lambda *a: self.fail('lookup'))
        self.assertTrue(p['needs_build'])

    def test_api_failure_stops_plan(self):
        def fail(*args):
            raise RuntimeError('API unavailable')
        with self.assertRaisesRegex(RuntimeError, 'API unavailable'):
            ci_build.make_plan('someone/fork', self.known, self.meta, lookup=fail)

    def test_expired_or_failed_artifacts_are_not_reused(self):
        base = {'name': 'matching', 'id': 4, 'expired': False,
                'expires_at': '2999-01-01T00:00:00Z', 'workflow_run': {'id': 123}}
        cases = [dict(base, expired=True), dict(base, expires_at='2000-01-01T00:00:00Z')]
        for item in cases:
            with patch('ci_build.api', return_value=[{'artifacts': [item]}]) as api:
                self.assertIsNone(ci_build.existing_artifact('someone/fork', 'matching'))
                self.assertEqual(api.call_count, 1)
        for conclusion, path in [('failure', '.github/workflows/build.yml'), ('success', '.github/workflows/other.yml')]:
            with patch('ci_build.api', side_effect=[[{'artifacts': [base]}], [{'conclusion': conclusion, 'path': path}]]):
                self.assertIsNone(ci_build.existing_artifact('someone/fork', 'matching'))
        with patch('ci_build.api', side_effect=[[{'artifacts': [base]}], [{'conclusion': 'success', 'path': '.github/workflows/build.yml'}]]):
            self.assertEqual(ci_build.existing_artifact('someone/fork', 'matching')['id'], 4)

    def test_lagging_feed_uses_newer_reviewed_version(self):
        self.meta['version'] = '109.0.0.2.108'
        m = ci_build.choose_manifest(self.known, self.meta)
        self.assertEqual(m['version'], self.m['version'])

    def test_unknown_new_version_stops_before_artifact_lookup(self):
        self.meta['version'] = '999.0.0.1'
        with self.assertRaisesRegex(ValueError, 'compatibility review'):
            ci_build.make_plan('someone/fork', self.known, self.meta,
                              lookup=lambda *a: self.fail('lookup too early'))

    def test_replaced_binary_is_refused(self):
        self.meta['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'different bytes'):
            ci_build.choose_manifest(self.known, self.meta)

    def test_regional_url_reuses_same_build(self):
        url = self.m['url'].replace('securecdn-iev1-1', 'securecdn-other')
        m = ci_build.choose_manifest(self.known, dmg_url=url)
        self.assertEqual(m['url'], url)
        self.assertEqual(ci_build.artifact_name(m), ci_build.artifact_name(self.m))

    def test_unknown_url_is_refused_before_lookup(self):
        for url in ('https://example.org/app.dmg', 'https://oculus.com/binaries/download/?id=999'):
            with self.assertRaises(ValueError):
                ci_build.make_plan('someone/fork', self.known, dmg_url=url,
                                  lookup=lambda *a: self.fail('lookup too early'))


class PackagingMetadataTests(unittest.TestCase):
    def test_minimum_os_includes_library_without_lowering_vendor_requirement(self):
        self.assertEqual(quest_usb.minimum_macos({}), '13.3')
        self.assertEqual(quest_usb.minimum_macos({'LSMinimumSystemVersion': '12.0'}), '13.3')
        self.assertEqual(quest_usb.minimum_macos({'LSMinimumSystemVersion': '15.0'}), '15.0')
        self.assertEqual(quest_usb.minimum_macos({'LSMinimumSystemVersion': '13.3',
                         'LSMinimumSystemVersionByArchitecture': {'arm64': '14.0'}}), '14.0')
        with self.assertRaises(ValueError):
            quest_usb.minimum_macos({'LSMinimumSystemVersion': 'unknown'})


class ReadmeTests(unittest.TestCase):
    def test_command_decodes_shell_characters_without_page_javascript(self):
        html = '<code id="repair-command">test 1 &lt; 2 &amp;&amp; echo "ready"</code><script>copy()</script>'
        self.assertEqual(quest_usb.readme_command(html), 'test 1 < 2 && echo "ready"')

    def test_missing_empty_or_duplicate_commands_are_rejected(self):
        for html in ('<p>No command</p>', '<code id="repair-command"></code>',
                     '<code id="repair-command">one</code><code id="repair-command">two</code>'):
            with self.assertRaises(ValueError):
                quest_usb.readme_command(html)


class DownloadTests(unittest.TestCase):
    def test_official_url_boundaries(self):
        upstream.official_url('https://securecdn-iev1-1.oculus.com/binaries/download/?id=1')
        for url in ('http://oculus.com/a', 'https://oculus.com.evil.test/a', 'https://eviloculus.com',
                    'file:///tmp/foo', 'https://name:secret@oculus.com/a'):
            with self.assertRaises(ValueError):
                upstream.official_url(url)

    def test_bad_download_never_becomes_usable_dmg(self):
        m = {'url': 'https://oculus.com/a', 'size': 4, 'dmg_sha256': hashlib.sha256(b'good').hexdigest()}
        with tempfile.TemporaryDirectory() as t, patch('upstream.open_official', return_value=io.BytesIO(b'bad!')):
            target = Path(t) / 'upstream.dmg'
            with self.assertRaisesRegex(ValueError, 'checksum'):
                upstream.download(m, target)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix('.partial').exists())

    def test_cached_verified_download_avoids_network(self):
        with tempfile.TemporaryDirectory() as t, patch('upstream.open_official', side_effect=AssertionError('network used')):
            p = Path(t) / 'upstream.dmg'
            p.write_bytes(b'good')
            upstream.download({'size': 4, 'dmg_sha256': hashlib.sha256(b'good').hexdigest()}, p)

    def test_download_does_not_delete_another_partial_file(self):
        with tempfile.TemporaryDirectory() as t, patch('upstream.open_official', side_effect=AssertionError('network used')):
            p = Path(t) / 'upstream.dmg'
            partial = p.with_suffix('.partial')
            partial.write_bytes(b'another running download')
            with self.assertRaises(FileExistsError):
                upstream.download({}, p)
            self.assertEqual(partial.read_bytes(), b'another running download')



if __name__ == '__main__':
    unittest.main()
