#!/usr/bin/env python3
"""Explicit, user-run updates from versioned GitHub releases; no background agent."""
import argparse
import hashlib
import json
import os
import plistlib
import re
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from upstream import APP_NAME, BUNDLE_ID, ROOT, version_tuple


def github_url(url):
    p = urllib.parse.urlparse(url)
    host = p.hostname or ''
    if p.scheme != 'https' or p.username or p.password or p.port not in (None, 443) or not (
        host in ('github.com', 'api.github.com', 'objects.githubusercontent.com', 'release-assets.githubusercontent.com')
    ):
        raise ValueError('Unexpected GitHub asset URL')
    return url


class GitHubRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        github_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, limit):
    request = urllib.request.Request(github_url(url), headers={'User-Agent': 'Quest-VD-Mac-USB/1'})
    with urllib.request.build_opener(GitHubRedirects()).open(request, timeout=60) as response:
        result = response.read(limit + 1)
    if len(result) > limit:
        raise ValueError('Release asset too large')
    return result


def tag_tuple(tag):
    match = re.fullmatch(r'meta-(\d+(?:\.\d+){1,5})-usb\.(\d+)', tag)
    if not match:
        raise ValueError('Unrecognized release tag')
    return version_tuple(match[1]), int(match[2])


def extract_kit(archive, destination):
    with zipfile.ZipFile(archive) as z:
        total, names = 0, set()
        for entry in z.infolist():
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename or
                    not path.parts or path.parts[0] != 'quest-vd-mac-usb' or
                    stat.S_ISLNK(entry.external_attr >> 16) or entry.filename in names):
                raise ValueError('Unsafe release archive entry')
            names.add(entry.filename)
            total += entry.file_size
            if total > 20 * 1024 * 1024 or len(names) > 500:
                raise ValueError('Unexpected release archive size')
        z.extractall(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check version metadata only, without installing')
    parser.add_argument('--destination', type=Path, default=Path('/Applications') / (APP_NAME + '.app'))
    parser.add_argument('--identity', default=os.environ.get('QUEST_VD_SIGN_IDENTITY', '-'))
    args = parser.parse_args()
    repository = json.loads((ROOT / 'project.json').read_text())['repository']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid project repository')
    release = json.loads(fetch(f'https://api.github.com/repos/{repository}/releases/latest', 1024 * 1024))
    tag = release['tag_name']
    latest = tag_tuple(tag)
    info_path = args.destination.expanduser() / 'Contents/Info.plist'
    if info_path.exists():
        installed = plistlib.loads(info_path.read_bytes())
        old_tag = installed.get('QuestVDUSBRelease')
        if old_tag and installed.get('CFBundleIdentifier') == BUNDLE_ID and tag_tuple(old_tag) >= latest:
            print('Already current:', old_tag, '— no app download.')
            return
        if version_tuple(installed['CFBundleVersion']) > latest[0]:
            print('Installed Meta version is newer than this project release. No downgrade or download.')
            return
    print('Available:', tag, f'https://github.com/{repository}/releases/tag/{tag}')
    if args.check:
        return
    filename = f'quest-vd-mac-usb-{tag}.zip'
    assets = {a['name']: a for a in release['assets']}
    sums = fetch(assets['SHA256SUMS']['browser_download_url'], 100_000).decode()
    digest = next((line.split()[0] for line in sums.splitlines() if len(line.split()) == 2 and line.split()[1] == filename), None)
    if not digest or not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('Missing release checksum')
    payload = fetch(assets[filename]['browser_download_url'], 10 * 1024 * 1024)
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError('Installer checksum mismatch')
    with tempfile.TemporaryDirectory(prefix='quest-vd-update-') as temp:
        archive = Path(temp) / filename
        archive.write_bytes(payload)
        extract_kit(archive, temp)
        kit = Path(temp) / 'quest-vd-mac-usb'
        metadata = json.loads((kit / 'release.json').read_text())
        if metadata['tag'] != tag:
            raise ValueError('Release archive tag mismatch')
        build_parent = Path.home() / 'Library/Caches' / BUNDLE_ID
        build_parent.mkdir(parents=True, exist_ok=True)
        build_dir = tempfile.mkdtemp(prefix=tag + '-', dir=build_parent)
        subprocess.run([sys.executable, str(kit / 'src/quest_usb.py'), '--version', metadata['version'],
                        '--output', build_dir, '--install', '--destination', str(args.destination.expanduser()),
                        '--identity', args.identity], check=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print('Update stopped:', error, file=sys.stderr)
        sys.exit(1)
