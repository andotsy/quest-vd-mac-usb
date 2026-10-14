import hashlib
import io
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import patching
import release
import update
import upstream


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


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.known = upstream.manifests()
        self.m = self.known[max(self.known, key=upstream.version_tuple)]
        self.meta = {'version': self.m['version'], 'sha256': self.m['dmg_sha256'], 'size': self.m['size']}

    def test_duplicate_check_happens_without_downloading(self):
        with patch('upstream.download', side_effect=AssertionError('DMG fetched')):
            p = release.make_plan(self.meta, self.known, 'someone/fork', exists=lambda repo, tag: True)
            self.assertFalse(p['needs_build'])

    def test_new_patch_revision_can_release_same_meta_version(self):
        self.m['patch_revision'] += 1
        p = release.make_plan(self.meta, self.known, 'someone/fork', exists=lambda repo, tag: tag.endswith('usb.1'))
        self.assertTrue(p['needs_build'])

    def test_feed_downgrade_uses_known_official_build(self):
        self.meta['version'] = '109.0.0.2.108'
        p = release.make_plan(self.meta, self.known, 'someone/fork', exists=lambda *a: False)
        self.assertTrue(p['feed_behind'])
        self.assertEqual(p['version'], self.m['version'])

    def test_unknown_new_version_stops_before_release_lookup(self):
        self.meta['version'] = '999.0.0.1'
        with self.assertRaisesRegex(ValueError, 'compatibility review'):
            release.make_plan(self.meta, self.known, 'someone/fork', exists=lambda *a: self.fail('API lookup too early'))

    def test_replaced_upstream_binary_fails_closed(self):
        self.meta['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'different bytes'):
            upstream.select_manifest(self.meta, self.known)

    def test_published_kit_contains_source_only(self):
        with tempfile.TemporaryDirectory() as t:
            report = Path(t) / 'report.json'
            report.write_text(json.dumps({'release': upstream.tag_for(self.m), 'vendor_signature_verified': True,
                                         'local_signature_verified': True, 'config_smoke_passed': True}))
            release.package(self.m['version'], report, Path(t) / 'dist', 'example/fork')
            archive = next((Path(t) / 'dist').glob('*.zip'))
            with zipfile.ZipFile(archive) as z:
                for name in z.namelist():
                    self.assertFalse(any(x in name for x in ('.app/', '.dmg', '.dylib', '.apk', '.pem', '.p12')))
                self.assertEqual(json.loads(z.read('quest-vd-mac-usb/project.json'))['repository'], 'example/fork')
                self.assertEqual((z.getinfo('quest-vd-mac-usb/Install.command').external_attr >> 16) & 0o777, 0o755)


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

    def test_update_archive_cannot_escape(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'bad.zip'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('quest-vd-mac-usb/../../escaped', 'x')
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                update.extract_kit(p, Path(t) / 'out')


if __name__ == '__main__':
    unittest.main()
