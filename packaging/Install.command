#!/bin/bash
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin

HERE="$(cd -- "$(dirname -- "$0")" && pwd -P)"
APP='Meta Quest Virtual Display.app'
SOURCE="$HERE/$APP"
DESTINATION="/Applications/$APP"
IDENTITY="${QUEST_VD_SIGN_IDENTITY:--}"
CHECK=false
STAGING=''
BACKUP=''
COMMITTED=false

fail() { printf '%s\n' "$*" >&2; exit 1; }
cleanup() {
    status=$?
    if [[ "$COMMITTED" == false && -n "$BACKUP" && ! -e "$DESTINATION" ]]; then
        mv -- "$BACKUP" "$DESTINATION" || printf 'Restore your previous app from: %s\n' "$BACKUP" >&2
    fi
    if [[ -n "$STAGING" ]]; then rm -rf -- "$STAGING"; fi
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check) CHECK=true; shift ;;
        --destination) [[ $# -ge 2 ]] || fail 'Missing destination.'; DESTINATION="$2"; shift 2 ;;
        --identity) [[ $# -ge 2 && -n "$2" ]] || fail 'Missing signing identity.'; IDENTITY="$2"; shift 2 ;;
        *) fail 'Usage: Install.command [--check] [--destination /path/to/app] [--identity certificate]' ;;
    esac
done

[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || fail 'Requires an Apple Silicon Mac.'
[[ "$DESTINATION" == /* && "${DESTINATION##*/}" == "$APP" ]] || fail "Choose an absolute path ending in $APP."
[[ ! -L "$DESTINATION" ]] || fail 'The destination is a symlink. Choose a regular folder.'
(cd "$HERE" && shasum -a 256 -c Support/SHA256SUMS >/dev/null)
codesign --verify --deep --strict "$SOURCE"
codesign --verify --strict "$HERE/Support/prepare-install"
[[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$SOURCE/Contents/Info.plist")" == io.github.quest-vd-mac-usb ]] || fail 'Unexpected app identity.'
VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$SOURCE/Contents/Info.plist")"
if [[ "$CHECK" == true ]]; then
    printf 'Verified. Meta %s + USB.\n' "$VERSION"
    exit 0
fi

"$HERE/Support/prepare-install" --validate "$DESTINATION" "$VERSION"
PARENT="$(dirname -- "$DESTINATION")"
mkdir -p -- "$PARENT"
[[ -w "$PARENT" ]] || fail 'This folder is not writable. Use --destination with your own Applications folder.'
STAGING="$(mktemp -d "$PARENT/.quest-vd-usb.XXXXXXXX")"
printf 'Installing Meta Quest Virtual Display…\n'
ditto "$SOURCE" "$STAGING/$APP"
codesign --force --deep --sign "$IDENTITY" "$STAGING/$APP"
codesign --verify --deep --strict "$STAGING/$APP"
"$HERE/Support/prepare-install" --quit
# Recheck after staging in case another installer changed the destination.
[[ ! -L "$DESTINATION" ]] || fail 'The destination changed. Run the installer again.'
"$HERE/Support/prepare-install" --validate "$DESTINATION" "$VERSION"
if [[ -e "$DESTINATION" ]]; then
    BACKUP_DIR="$PARENT/Quest VD USB Backups/$(date +%Y%m%d-%H%M%S)-$$"
    mkdir -p -- "$BACKUP_DIR"
    BACKUP="$BACKUP_DIR/$APP.backup"
    mv -- "$DESTINATION" "$BACKUP"
fi
mv -- "$STAGING/$APP" "$DESTINATION"
COMMITTED=true
printf '\nReady. Open %s\n' "$DESTINATION"
printf 'Allow Accessibility and Screen Recording when asked.\n'
if [[ -n "$BACKUP" ]]; then printf 'Previous app saved in Quest VD USB Backups.\n'; fi
