#!/usr/bin/env python3
"""GitHub release automation. Public assets contain project-owned source only."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

from upstream import ROOT, latest_metadata, manifests, select_manifest, tag_for, version_tuple


def gh(*args):
    return subprocess.run(['gh', *args], text=True, check=True, capture_output=True).stdout


def release_exists(repository, tag):
    # List releases instead of treating every failed lookup (including outages or
    # bad credentials) as "not found". A failed API request stops before download.
    releases = json.loads(gh('api', '--paginate', '--slurp', f'repos/{repository}/releases?per_page=100'))
    return any(item['tag_name'] == tag for page in releases for item in page)


def make_plan(metadata, known, repository, exists=release_exists):
    manifest = select_manifest(metadata, known)
    tag = tag_for(manifest)
    duplicate = exists(repository, tag)
    return {'tag': tag, 'version': manifest['version'], 'feed_version': metadata['version'],
            'needs_build': not duplicate,
            'reason': 'Release already exists; no DMG download.' if duplicate else 'New reviewed release; build required.',
            'feed_behind': version_tuple(metadata['version']) < version_tuple(manifest['version'])}


def plan(repository, output):
    result = make_plan(latest_metadata(), manifests(), repository)
    print(json.dumps(result, indent=2))
    Path(output).write_text(json.dumps(result, indent=2) + '\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            for key in ('tag', 'version', 'needs_build'):
                value = str(result[key]).lower() if isinstance(result[key], bool) else result[key]
                stream.write(f'{key}={value}\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(f"### {result['tag']}\n\n{result['reason']}\n\nMeta feed: {result['feed_version']}.\n")
            if result['feed_behind']:
                stream.write('The public feed trails a previously verified official download. No downgrade is attempted.\n')


def source_files():
    exact = ['README.md', 'LICENSE', 'NOTICE.md', 'Install.command', 'Update.command', '.gitignore', 'project.json']
    paths = [ROOT / name for name in exact]
    for directory, suffixes in [('src', {'.py', '.c', '.m', '.json'}), ('manifests', {'.json'}),
                                ('docs', {'.md'}), ('assets', {'.svg'}), ('tests', {'.py'}),
                                ('.github/workflows', {'.yml'})]:
        paths.extend(p for p in (ROOT / directory).glob('*') if p.is_file() and p.suffix in suffixes)
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise ValueError('Unexpected public source asset: ' + str(path))
        path.read_text() # Refuse binary data; vendor binaries are never eligible.
    return sorted(paths)


def package(version, report_path, output, repository):
    manifest = manifests()[version]
    tag = tag_for(manifest)
    report = json.loads(Path(report_path).read_text())
    if report.get('release') != tag or not all(report.get(k) is True for k in
        ('vendor_signature_verified', 'local_signature_verified', 'config_smoke_passed')):
        raise ValueError('Missing successful build verification; refusing release')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'quest-vd-mac-usb-{tag}.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for path in source_files():
            relative = path.relative_to(ROOT).as_posix()
            content = path.read_bytes()
            if relative == 'project.json':
                content = (json.dumps({'repository': repository}, indent=2) + '\n').encode()
            entry = zipfile.ZipInfo('quest-vd-mac-usb/' + relative)
            entry.external_attr = (0o100755 if path.suffix == '.command' else 0o100644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, content)
        z.writestr('quest-vd-mac-usb/release.json', json.dumps({'tag': tag, 'version': version}) + '\n')
    # Explicit allowlist. Do not upload the build directory, even on failure.
    public_manifest = output / 'manifest.json'
    public_manifest.write_text(json.dumps(manifest, indent=2) + '\n')
    public_report = output / 'verification.json'
    public_report.write_text(json.dumps(report, indent=2) + '\n')
    assets = [archive, public_manifest, public_report]
    checksums = output / 'SHA256SUMS'
    checksums.write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in assets))
    notes = output / 'release-notes.md'
    notes.write_text(f'''## Meta Quest Virtual Display USB — {tag}

Personal-use installer kit for Meta **{version}**, patch revision **{manifest['patch_revision']}**.

Download the ZIP, verify SHA256SUMS, extract it and run `Install.command` on an Apple Silicon Mac with Apple's Command Line Tools installed. The installer obtains Meta's app directly from Meta, checks its digest and original developer signature, applies the reviewed patch, and signs the result locally. It preserves the previous installation and does not launch a second host.

**No Meta app, DMG, APK, icons, or private signing keys are included.** The published artifact contains our source, patch manifest, and local installer. The app name stays **Meta Quest Virtual Display**; its bundle ID is `io.github.quest-vd-mac-usb`.

Native USB is enabled and 120 FPS is requested. **120 Hz presentation is not established**; the measured Quest session ran at 72 Hz. This is an independent community project, not affiliated with Meta. See the repository's legal and signing notes before use.

Verification: original vendor signature, exact executable hash, instruction guards, local code signature, and initializer smoke check passed. CI does not test a physical Quest or grant macOS privacy permissions.

[Install and update instructions](https://github.com/{repository}#install) · [Build it yourself](https://github.com/{repository}#fork-it-build-it-yourself)
''')
    print(archive)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('plan')
    p.add_argument('--repository', required=True)
    p.add_argument('--output', default='plan.json')
    p = commands.add_parser('package')
    p.add_argument('--repository', required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--output', default='dist')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        parser.error('Invalid repository')
    if args.command == 'plan':
        plan(args.repository, args.output)
    else:
        package(args.version, args.report, args.output, args.repository)


if __name__ == '__main__':
    main()
