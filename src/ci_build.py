#!/usr/bin/env python3
"""Plan an artifact before downloading Meta's app; build only reviewed bytes."""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

from upstream import ROOT, latest_metadata, manifests, official_url, select_manifest, tag_for


def api(endpoint):
    result = subprocess.run(['gh', 'api', '--paginate', '--slurp', endpoint],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def url_key(url):
    parsed = urllib.parse.urlparse(official_url(url))
    ids = urllib.parse.parse_qs(parsed.query).get('id', [])
    if parsed.path.rstrip('/') == '/binaries/download' and len(ids) == 1 and ids[0].isdigit():
        return 'meta-binary:' + ids[0]
    return url


def choose_manifest(known, metadata=None, dmg_url=''):
    if dmg_url:
        key = url_key(dmg_url)
        matches = [m for m in known.values() if url_key(m['url']) == key]
        if len(matches) != 1:
            raise ValueError('This URL needs a reviewed manifest. Leave the URL blank to use the latest supported build.')
        return dict(matches[0], url=dmg_url)
    return select_manifest(metadata, known)


def artifact_name(manifest, root=ROOT):
    # The URL may rotate between Meta CDN regions; the pinned bytes define identity.
    digest = hashlib.sha256(manifest['dmg_sha256'].encode())
    normalized = dict(manifest)
    normalized.pop('url', None)
    digest.update(json.dumps(normalized, sort_keys=True).encode())
    paths = [*root.glob('src/*.py'), *root.glob('src/*.c'), *root.glob('src/*.m'),
             *root.glob('src/*.json'), *root.glob('packaging/*'),
             root / '.github/workflows/build.yml', root / 'NOTICE.md', root / 'LICENSE']
    for path in sorted(paths):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode() + b'\0' + path.read_bytes() + b'\0')
    return f'Quest-VD-USB-{tag_for(manifest)}-{digest.hexdigest()[:12]}.dmg'


def existing_artifact(repository, name, now=None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    now = now or dt.datetime.now(dt.timezone.utc)
    pages = api(f'repos/{repository}/actions/artifacts?name={urllib.parse.quote(name)}&per_page=100')
    for page in pages:
        for item in page['artifacts']:
            expires = dt.datetime.fromisoformat(item['expires_at'].replace('Z', '+00:00'))
            if item['name'] != name or item['expired'] or expires <= now:
                continue
            run_id = int(item['workflow_run']['id'])
            run = api(f'repos/{repository}/actions/runs/{run_id}')[0]
            if run['conclusion'] == 'success' and run['path'].split('@')[0] == '.github/workflows/build.yml':
                return {'id': item['id'], 'url': f'https://github.com/{repository}/actions/runs/{run_id}',
                        'expires_at': item['expires_at']}
    return None


def make_plan(repository, known, metadata=None, dmg_url='', rebuild=False, lookup=existing_artifact):
    manifest = choose_manifest(known, metadata, dmg_url)
    name = artifact_name(manifest)
    previous = None if rebuild else lookup(repository, name)
    return {'manifest': manifest, 'artifact_name': name, 'needs_build': previous is None,
            'previous': previous, 'feed_version': metadata['version'] if metadata else None}


def output(key, value):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write(f'{key}={value}\n')


def summary(message):
    print(message)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(message + '\n\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan')
    plan.add_argument('--repository', required=True)
    plan.add_argument('--dmg-url', default='')
    plan.add_argument('--rebuild', action='store_true')
    plan.add_argument('--output', type=Path, required=True)
    build = commands.add_parser('build')
    build.add_argument('--plan', type=Path, required=True)
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--dmg', type=Path, help='Already downloaded official DMG (development only)')
    build.add_argument('--verify-install', action='store_true', help='Runner only: test install and backup in a temporary folder')
    args = parser.parse_args()
    if args.command == 'plan':
        url = args.dmg_url.strip()
        metadata = None if url else latest_metadata()
        p = make_plan(args.repository, manifests(), metadata, url, args.rebuild)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(p, indent=2) + '\n')
        output('needs_build', str(p['needs_build']).lower())
        output('artifact_name', p['artifact_name'])
        if p['previous']:
            summary(f"Already built. [Download your DMG]({p['previous']['url']}).")
        else:
            print(f"Building Meta {p['manifest']['version']} + USB.")
        if metadata and metadata['version'] != p['manifest']['version']:
            summary(f"Meta’s feed reports {metadata['version']}; using the newer reviewed {p['manifest']['version']} build.")
    else:
        if platform.system() != 'Darwin' or platform.machine() != 'arm64':
            raise ValueError('Building requires an Apple Silicon Mac runner.')
        from quest_usb import build_dmg
        p = json.loads(args.plan.read_text())
        if not p['needs_build']:
            raise ValueError('This build is already available.')
        m = p['manifest']
        # Never trust edited/stale plan files as new patch manifests.
        reviewed = choose_manifest(manifests(), dmg_url=m['url'])
        if reviewed != m or artifact_name(m) != p['artifact_name']:
            raise ValueError('Build inputs changed. Run the plan step again.')
        dmg = build_dmg(m, args.output, args.dmg, args.verify_install, artifact_filename=p['artifact_name'])
        output('dmg', dmg)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Stopped: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        sys.exit(1)
