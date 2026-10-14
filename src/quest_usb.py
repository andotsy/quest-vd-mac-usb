#!/usr/bin/env python3
"""Download, verify, patch, and locally sign Meta's Mac host. Standard library only."""
import argparse
import datetime
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from patching import patch_executable
from upstream import APP_NAME, BUNDLE_ID, ROOT, download, manifests, sha256, tag_for, version_tuple

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


def install(built, destination, manifest):
    destination = destination.expanduser().absolute()
    if destination.name != APP_NAME + '.app':
        raise ValueError('Install destination must end with ' + APP_NAME + '.app')
    if destination.is_symlink():
        raise ValueError('Refusing a symlink install destination')
    if destination.exists():
        current = plistlib.loads((destination / 'Contents/Info.plist').read_bytes())
        if current.get('CFBundleIdentifier') not in ('com.meta.virtualdesktop', 'com.codex.metausb120test', BUNDLE_ID):
            raise ValueError('Destination is a different app; refusing replacement')
        if version_tuple(current['CFBundleVersion']) > version_tuple(manifest['version']):
            raise ValueError('Refusing to downgrade the installed Meta app')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stage on the same volume first. Installation needs no root when the
    # destination directory is writable. Normal quit restores physical displays.
    with tempfile.TemporaryDirectory(prefix='.quest-vd-usb-', dir=destination.parent) as staging:
        staged = Path(staging) / destination.name
        run('/usr/bin/ditto', built, staged)
        run('/usr/bin/codesign', '--verify', '--deep', '--strict', staged)
        helper = Path(staging) / 'quit-hosts'
        run('/usr/bin/xcrun', 'clang', '-fobjc-arc', '-framework', 'AppKit', ROOT / 'src/quit-hosts.m', '-o', helper)
        run(helper)
        backup = None
        if destination.exists():
            stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            backup_dir = destination.parent / 'Quest VD USB Backups' / stamp
            backup_dir.mkdir(parents=True)
            # No .app suffix: Launch Services should not offer this backup as
            # another live installation. Rename to .app only when rolling back.
            backup = backup_dir / (destination.name + '.backup')
            destination.rename(backup)
        try:
            staged.rename(destination)
        except Exception:
            if backup:
                backup.rename(destination)
            raise
    print('Installed:', destination)
    if backup:
        print('Previous app preserved:', backup)
    print('Open this app once in Finder. Grant Screen Recording and Accessibility to this new identity.')
    print('No app was launched automatically.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', help='Supported upstream version; defaults to newest reviewed manifest')
    parser.add_argument('--source-app', type=Path, help='Use an original, Meta-signed app instead of downloading')
    parser.add_argument('--dmg', type=Path, help='Use an already downloaded official DMG (checksum still required)')
    parser.add_argument('--output', type=Path, default=ROOT / 'build', help='Private local build directory')
    parser.add_argument('--install', action='store_true', help='Normally quit hosts, back up existing app, then install')
    parser.add_argument('--destination', type=Path, default=Path('/Applications') / (APP_NAME + '.app'))
    parser.add_argument('--identity', default=os.environ.get('QUEST_VD_SIGN_IDENTITY', '-'), help='Persistent local code-signing identity; default: ad-hoc')
    parser.add_argument('--make-dmg', action='store_true', help='Create a local DMG for personal use; never uploaded by CI')
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        parser.error('Building requires an Apple Silicon Mac (run Terminal natively, not with Rosetta)')
    run('/usr/bin/xcrun', '--find', 'clang', stdout=subprocess.DEVNULL)
    known = manifests()
    version = args.version or max(known, key=version_tuple)
    if version not in known:
        parser.error('Unsupported version; no files have been downloaded')
    manifest = known[version]
    output = args.output.expanduser().absolute()
    output.mkdir(parents=True, exist_ok=True)
    target = output / (APP_NAME + '.app')
    if target.exists():
        parser.error('Build output already exists. Choose a fresh --output directory.')
    if args.source_app and args.dmg:
        parser.error('Choose --source-app or --dmg')
    if args.source_app:
        report = build(args.source_app.absolute(), target, manifest, args.identity)
    else:
        dmg = args.dmg.absolute() if args.dmg else download(manifest, output / 'upstream.dmg')
        if dmg.stat().st_size != manifest['size'] or sha256(dmg) != manifest['dmg_sha256']:
            raise ValueError('DMG checksum/size mismatch')
        with tempfile.TemporaryDirectory(prefix='quest-vd-mount-') as mount:
            run('/usr/bin/hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', mount, dmg, stdout=subprocess.DEVNULL)
            try:
                report = build(Path(mount) / (APP_NAME + '.app'), target, manifest, args.identity)
            finally:
                run('/usr/bin/hdiutil', 'detach', mount, stdout=subprocess.DEVNULL)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    if args.make_dmg:
        with tempfile.TemporaryDirectory(prefix='quest-vd-dmg-') as stage:
            run('/usr/bin/ditto', target, Path(stage) / target.name)
            os.symlink('/Applications', Path(stage) / 'Applications')
            run('/usr/bin/hdiutil', 'create', '-srcfolder', stage, '-volname', APP_NAME,
                '-format', 'UDZO', output / (tag_for(manifest) + '-personal.dmg'), stdout=subprocess.DEVNULL)
    if args.install:
        install(target, args.destination, manifest)
    print('Verified local build:', target)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('Stopped:', error, file=sys.stderr)
        sys.exit(1)
