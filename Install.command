#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
  printf '%s\n' 'Install Apple Command Line Tools first: xcode-select --install' 'Then run this installer again.'
  exit 1
fi
build_dir="$HOME/Library/Caches/io.github.quest-vd-mac-usb/build-$(date +%Y%m%d-%H%M%S)-$$"
printf '%s\n' 'This builds Meta’s app locally, then normally quits existing hosts and backs up the previous installation.'
/usr/bin/python3 src/quest_usb.py --output "$build_dir" --install "$@"
