#!/usr/bin/env python3
"""Build the app and its self-contained installation DMG on a Mac runner."""
import json
import plistlib
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
    output = output.expanduser().absolute()
    if output.exists():
        raise ValueError('Choose a fresh build directory.')
    output.mkdir(parents=True)
    dmg = source_dmg.absolute() if source_dmg else download(manifest, output / 'upstream.dmg')
    if dmg.stat().st_size != manifest['size'] or sha256(dmg) != manifest['dmg_sha256']:
        raise ValueError('DMG checksum/size mismatch')
    stage = output / 'image'
    support = stage / 'Support'
    support.mkdir(parents=True)
    target = stage / (APP_NAME + '.app')
    with tempfile.TemporaryDirectory(prefix='quest-vd-source-') as mount:
        run('/usr/bin/hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', mount, dmg, stdout=subprocess.DEVNULL)
        try:
            report = build(Path(mount) / target.name, target, manifest)
        finally:
            run('/usr/bin/hdiutil', 'detach', mount, stdout=subprocess.DEVNULL)
    helper = support / 'prepare-install'
    run('/usr/bin/xcrun', 'clang', '-arch', 'arm64', '-mmacosx-version-min=13.3', '-fobjc-arc',
        '-Wall', '-Wextra', '-Werror', '-framework', 'AppKit', ROOT / 'src/quit-hosts.m', '-o', helper)
    run('/usr/bin/codesign', '--force', '--sign', '-', helper)
    for name in ('Install.command', 'Read Me.txt'):
        run('/usr/bin/ditto', ROOT / 'packaging' / name, stage / name)
    (stage / 'Install.command').chmod(0o755)
    for name in ('NOTICE.md', 'LICENSE'):
        run('/usr/bin/ditto', ROOT / name, support / name)
    (support / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    # codesign covers the complete app. These hashes cover the installer and support files.
    checked = [stage / 'Install.command', stage / 'Read Me.txt', *sorted(support.iterdir())]
    (support / 'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.relative_to(stage)}\n' for p in checked))
    dist = output / 'dist'
    dist.mkdir()
    filename = artifact_filename or (tag_for(manifest) + '.dmg')
    if Path(filename).name != filename or not filename.endswith('.dmg'):
        raise ValueError('Invalid artifact filename')
    result = dist / filename
    run('/usr/bin/hdiutil', 'create', '-srcfolder', stage, '-volname', 'Quest Virtual Display USB',
        '-format', 'UDZO', result, stdout=subprocess.DEVNULL)
    run('/usr/bin/hdiutil', 'verify', result, stdout=subprocess.DEVNULL)
    with tempfile.TemporaryDirectory(prefix='quest-vd-check-') as mount:
        run('/usr/bin/hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', mount, result, stdout=subprocess.DEVNULL)
        try:
            installer = Path(mount) / 'Install.command'
            run(installer, '--check')
            if verify_install:
                check_install(installer)
        finally:
            run('/usr/bin/hdiutil', 'detach', mount, stdout=subprocess.DEVNULL)
    print('DMG ready:', result.name)
    return result


def check_install(installer):
    """Exercise real installation and backup on the isolated runner, never the user's Applications."""
    with tempfile.TemporaryDirectory(prefix='quest-vd-install-test-') as temp:
        root = Path(temp)
        destination = root / (APP_NAME + '.app')
        run(installer, '--destination', destination)
        run('/usr/bin/codesign', '--verify', '--deep', '--strict', destination)
        run(destination / EXECUTABLE, '--usb-config-check', stdout=subprocess.DEVNULL)
        run(installer, '--destination', destination)
        backups = list((root / 'Quest VD USB Backups').glob('*/*.app.backup'))
        if len(backups) != 1:
            raise ValueError('Installer did not preserve the previous app.')
        run('/usr/bin/codesign', '--verify', '--deep', '--strict', backups[0])
        # A mistaken destination and a newer installed version must both survive untouched.
        info_path = destination / 'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        for change in ({'CFBundleIdentifier': 'example.unrelated'}, {'CFBundleVersion': '999.0.0.0'}):
            info_path.write_bytes(plistlib.dumps(dict(info, **change)))
            before = info_path.read_bytes()
            attempt = subprocess.run([str(installer), '--destination', str(destination)], capture_output=True)
            if attempt.returncode == 0 or info_path.read_bytes() != before:
                raise ValueError('Installer replacement guard failed.')
