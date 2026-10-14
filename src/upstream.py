"""Small metadata requests first; verified official downloads only."""
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEED = 'https://www.oculus.com/binary-info/7248432555245552/latest/?rc=LIVE&format=json'
APP_NAME = 'Meta Quest Virtual Display'
BUNDLE_ID = 'io.github.quest-vd-mac-usb'


def version_tuple(version):
    if not re.fullmatch(r'\d+(?:\.\d+){1,5}', version):
        raise ValueError('Invalid upstream version')
    return tuple(int(n) for n in version.split('.'))


def official_url(url):
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or '').lower()
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443)
            or not any(host == d or host.endswith('.' + d) for d in ('oculus.com', 'facebook.com', 'fbcdn.net', 'meta.com'))):
        raise ValueError('Refusing non-Meta HTTPS download: ' + url)
    return url


class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_official(url):
    official_url(url)
    request = urllib.request.Request(url, headers={'User-Agent': 'Quest-VD-Mac-USB/1', 'Cache-Control': 'no-cache'})
    return urllib.request.build_opener(OfficialRedirects()).open(request, timeout=60)


def latest_metadata():
    with open_official(FEED) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Metadata too large')
    data = json.loads(raw)
    version_tuple(data['version'])
    official_url(data['url'])
    if not re.fullmatch(r'[0-9a-f]{64}', data['sha256']) or not 0 < data['size'] < 2_000_000_000:
        raise ValueError('Invalid upstream digest or size')
    return data


def manifests():
    return {p.stem: json.loads(p.read_text()) for p in (ROOT / 'manifests').glob('*.json')}


def tag_for(manifest):
    version_tuple(manifest['version'])
    revision = manifest['patch_revision']
    if not isinstance(revision, int) or revision < 1:
        raise ValueError('Invalid patch revision')
    return f"meta-{manifest['version']}-usb.{revision}"


def select_manifest(metadata, known):
    """Do not downgrade during phased rollouts; unknown newer releases fail closed."""
    newest = max(known, key=version_tuple)
    candidate = max(metadata['version'], newest, key=version_tuple)
    if candidate not in known:
        raise ValueError(f"Meta {candidate} needs compatibility review. No DMG downloaded; current release retained.")
    manifest = known[candidate]
    if metadata['version'] == candidate and (metadata['sha256'] != manifest['dmg_sha256'] or metadata['size'] != manifest['size']):
        raise ValueError('Meta replaced this version with different bytes; compatibility review required')
    return manifest


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(manifest, target):
    target = Path(target)
    if target.exists():
        if target.stat().st_size == manifest['size'] and sha256(target) == manifest['dmg_sha256']:
            return target
        raise ValueError('Existing download does not match manifest; choose a new output directory')
    partial = target.with_suffix('.partial')
    try:
        with open_official(manifest['url']) as response, partial.open('xb') as stream:
            total = 0
            for chunk in iter(lambda: response.read(1024 * 1024), b''):
                total += len(chunk)
                if total > manifest['size']:
                    raise ValueError('Download larger than verified manifest')
                stream.write(chunk)
        if total != manifest['size'] or sha256(partial) != manifest['dmg_sha256']:
            raise ValueError('Official download checksum/size mismatch')
        partial.rename(target)
    finally:
        partial.unlink(missing_ok=True)
    return target
