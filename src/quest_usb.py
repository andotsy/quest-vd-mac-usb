#!/usr/bin/env python3
"""Build the app and its self-contained installation DMG on a Mac runner."""
import json
import plistlib
import shlex
import subprocess
import tempfile
from pathlib import Path

from patching import patch_executable
from upstream import APP_NAME, BUNDLE_ID, ROOT, download, sha256, tag_for

EXECUTABLE = Path('Contents/MacOS') / APP_NAME
VENDOR_REQUIREMENT = '=anchor apple generic and certificate leaf[subject.OU] = "V9WTTPBFK9" and identifier "com.meta.virtualdesktop"'


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def build(source, target, manifest, identity='-'):
    if target.exists():
        raise ValueError('Output app already exists; use a fresh build directory')
    info = plistlib.loads((source / 'Contents/Info.plist').read_bytes())
    if info['CFBundleVersion'] != manifest['version'] or info['CFBundleIdentifier'] != 'com.meta.virtualdesktop':
        raise ValueError('Expected the original Meta app at the supported version')
    run('/usr/bin/codesign', '--verify', '--deep', '--strict', '-R', VENDOR_REQUIREMENT, source)
    patched, changes = patch_executable((source / EXECUTABLE).read_bytes(), manifest)
    run('/usr/bin/ditto', source, target)
    (target / EXECUTABLE).write_bytes(patched)
    info.update(CFBundleName=APP_NAME, CFBundleDisplayName=APP_NAME, CFBundleIdentifier=BUNDLE_ID,
                LSArchitecturePriority=['arm64'], LSRequiresNativeExecution=True,
                SUEnableAutomaticChecks=False, SUAutomaticallyUpdate=False, SUAllowsAutomaticUpdates=False,
                QuestVDUSBRelease=tag_for(manifest))
    info.pop('ApplicationIdentifier', None)
    (target / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    overrides = json.loads((ROOT / 'src/overrides.json').read_text())
    # These existing Meta switches disable both silent-update implementations.
    for key in ('frl_mqrd_silent_update_enabled', 'frl_mqrd_silent_update_phase_2'):
        overrides['remote_desktop_mqrd_default:' + key] = {'type': 'boolean', 'value': 'false'}
    (target / 'Contents/Resources/usb-overrides.json').write_text(json.dumps(overrides, indent=2) + '\n')
    for name in ('LICENSE', 'NOTICE.md'):
        run('/usr/bin/ditto', ROOT / name, target / 'Contents/Resources' / ('QuestVDUSB-' + name))
    library = target / 'Contents/MacOS/libQuestVDUSB.dylib'
    run('/usr/bin/xcrun', 'clang', '-arch', 'arm64', '-mmacosx-version-min=13.3', '-dynamiclib', '-O2',
        '-Wall', '-Wextra', '-Werror', ROOT / 'src/USBConfig.c', '-o', library,
        '-framework', 'CoreFoundation', '-install_name', '@executable_path/libQuestVDUSB.dylib')
    # All modified code is re-signed locally. This intentionally removes Meta's
    # original trust identity; no claim of notarization is made for the result.
    run('/usr/bin/codesign', '--force', '--deep', '--sign', identity, target)
    run('/usr/bin/codesign', '--verify', '--deep', '--strict', target)
    smoke = run(target / EXECUTABLE, '--usb-config-check', capture_output=True, text=True).stdout.strip()
    if not smoke.startswith('Quest VD USB configuration: '):
        raise ValueError('Bundled initializer did not run')
    return {'release': tag_for(manifest), 'upstream_version': manifest['version'],
            'bundle_id': BUNDLE_ID, 'app_name': APP_NAME, 'upstream_executable_sha256': manifest['executable_sha256'],
            'patched_executable_sha256': sha256(target / EXECUTABLE), 'patches': changes,
            'vendor_signature_verified': True, 'local_signature_verified': True,
            'config_smoke_passed': True, 'signing': 'ad-hoc' if identity == '-' else 'local identity',
            'performance': 'Requests 120 FPS; does not establish delivered FPS or headset refresh rate.'}


def build_dmg(manifest, output, source_dmg=None, verify_install=False, artifact_filename=None):
    import dmgbuild

    output = output.expanduser().absolute()
    if output.exists():
        raise ValueError('Choose a fresh build directory.')
    output.mkdir(parents=True)
    dmg = source_dmg.absolute() if source_dmg else download(manifest, output / 'upstream.dmg')
    if dmg.stat().st_size != manifest['size'] or sha256(dmg) != manifest['dmg_sha256']:
        raise ValueError('DMG checksum/size mismatch')
    stage = output / 'image'
    stage.mkdir()
    target = stage / (APP_NAME + '.app')
    with tempfile.TemporaryDirectory(prefix='quest-vd-source-') as mount:
        run('/usr/bin/hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', mount, dmg, stdout=subprocess.DEVNULL)
        try:
            report = build(Path(mount) / target.name, target, manifest)
        finally:
            run('/usr/bin/hdiutil', 'detach', mount, stdout=subprocess.DEVNULL)
    readme = stage / 'Readme.txt'
    run('/usr/bin/ditto', ROOT / 'packaging/Readme.txt', readme)
    readme.chmod(0o644)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    dist = output / 'dist'
    dist.mkdir()
    filename = artifact_filename or (tag_for(manifest) + '.dmg')
    if Path(filename).name != filename or not filename.endswith('.dmg'):
        raise ValueError('Invalid artifact filename')
    result = dist / filename
    background = output / 'dmg-background'
    run('/usr/bin/xcrun', 'swift', '-warnings-as-errors', ROOT / 'packaging/dmg-background.swift',
        background, manifest['version'])
    dmgbuild.build_dmg(str(result), 'Quest Virtual Display USB', settings={
        'format': 'UDZO', 'files': [str(target), str(readme)],
        'symlinks': {'Applications': '/Applications'},
        # Leave room for Finder's optional tab and status bars.
        'background': str(background.with_suffix('.png')), 'window_rect': ((160, 180), (760, 600)),
        'icon_locations': {target.name: (190, 214), 'Applications': (570, 214), 'Readme.txt': (380, 402)},
        'hide_extensions': ['Readme.txt'],
        'default_view': 'icon-view', 'icon_size': 88, 'text_size': 13,
        'include_icon_view_settings': True, 'include_list_view_settings': False,
        'arrange_by': None, 'grid_spacing': 90, 'scroll_position': (0, 0), 'label_pos': 'bottom',
        'show_icon_preview': False, 'show_status_bar': False, 'show_tab_view': False,
        'show_toolbar': False, 'show_pathbar': False, 'show_sidebar': False,
    })
    run('/usr/bin/hdiutil', 'verify', result, stdout=subprocess.DEVNULL)
    with tempfile.TemporaryDirectory(prefix='quest-vd-check-') as mount:
        run('/usr/bin/hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', mount, result, stdout=subprocess.DEVNULL)
        try:
            mounted = Path(mount)
            visible = {p.name for p in mounted.iterdir() if not p.name.startswith('.')}
            if visible != {target.name, 'Applications', 'Readme.txt'}:
                raise ValueError('Unexpected visible DMG contents: ' + repr(visible))
            if not (mounted / 'Applications').is_symlink() or (mounted / 'Applications').readlink() != Path('/Applications'):
                raise ValueError('Applications shortcut is missing or incorrect')
            if not (mounted / '.DS_Store').is_file() or not (mounted / '.background.tiff').is_file():
                raise ValueError('Finder layout or arrow background is missing')
            if (mounted / 'Readme.txt').stat().st_mode & 0o111:
                raise ValueError('Readme must be plain text, not executable')
            run('/usr/bin/codesign', '--verify', '--deep', '--strict', mounted / target.name)
            if verify_install:
                check_install(mounted)
        finally:
            run('/usr/bin/hdiutil', 'detach', mount, stdout=subprocess.DEVNULL)
    print('DMG ready:', result.name)
    return result


def check_install(mounted):
    """Test a drag-copy and the actual Readme commands without touching /Applications."""
    readme = (mounted / 'Readme.txt').read_text()
    start = readme.index('\n(\n') + 1
    end = readme.index('\n)\n', start) + 2
    script = readme[start:end]
    assignment = 'quest_app="/Applications/' + APP_NAME + '.app"'
    if script.count(assignment) != 1:
        raise ValueError('Cannot locate the Readme destination for isolated testing')
    with tempfile.TemporaryDirectory(prefix='quest-vd-install-test-') as temp:
        root = Path(temp)
        destination = root / (APP_NAME + '.app')
        run('/usr/bin/ditto', mounted / destination.name, destination)
        script = script.replace(assignment, 'quest_app=' + shlex.quote(str(destination)))
        # Exercise both macOS shells, including a second run with no quarantine left.
        for path in (destination, destination / EXECUTABLE):
            run('/usr/bin/xattr', '-w', 'com.apple.quarantine', '0081;00000000;QuestVDUSB-CI;', path)
        for shell in ('/bin/zsh', '/bin/bash'):
            run(shell, '-c', script)
            run('/usr/bin/codesign', '--verify', '--deep', '--strict', destination)
            attributes = run('/usr/bin/xattr', '-lr', destination, capture_output=True, text=True).stdout
            if 'com.apple.quarantine:' in attributes:
                raise ValueError('Readme commands did not remove quarantine')
            run(destination / EXECUTABLE, '--usb-config-check', stdout=subprocess.DEVNULL)
        # A different app must fail before any signing or attribute changes.
        info_path = destination / 'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info_path.write_bytes(plistlib.dumps(dict(info, CFBundleIdentifier='example.unrelated')))
        before = sha256(destination / EXECUTABLE)
        attempt = subprocess.run(['/bin/zsh', '-c', script], capture_output=True)
        if attempt.returncode == 0 or sha256(destination / EXECUTABLE) != before:
            raise ValueError('Readme app identity guard failed')
    print('Verified drag-copy, Readme signing in zsh/bash, quarantine removal, and app identity guard.')
