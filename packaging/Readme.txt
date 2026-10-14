Meta Quest Virtual Display USB

1. Quit Meta Quest Virtual Display if it is running.
2. Drag the app to Applications. Replace the previous copy if asked.
3. Paste this whole block into Terminal and press Return:

(
  set -eu
  quest_app="/Applications/Meta Quest Virtual Display.app"
  if [ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$quest_app/Contents/Info.plist")" != "io.github.quest-vd-mac-usb" ]; then
    echo "Copy the app from this DMG to Applications first."
    exit 1
  fi
  /usr/bin/codesign --verify --deep --strict "$quest_app"
  /usr/bin/codesign --force --deep --sign - "$quest_app"
  /usr/bin/codesign --verify --deep --strict "$quest_app"
  /usr/bin/xattr -dr com.apple.quarantine "$quest_app"
  echo "Ready. Open Meta Quest Virtual Display from Applications."
)

This signs your installed copy locally and removes its download quarantine.
It applies only to this app; no Xcode or extra tools needed.

Allow Accessibility and Screen Recording, then restart when asked.
Connect your Quest with a USB data cable and choose your Mac's USB entry.

Updates: sync your fork, then run Build DMG again.
Source & help: https://github.com/andotsy/quest-vd-mac-usb
