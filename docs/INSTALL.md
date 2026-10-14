# Advanced installation

Run commands from the extracted kit or repository root. Python uses only its
standard library. Apple's Command Line Tools provide the compiler and Python on
supported Macs.

## Build without installing

```sh
python3 src/quest_usb.py --output "$HOME/Desktop/quest-usb-build"
```

The output includes the app and `verification.json`. The smoke check exits before
Meta starts its host. It does not launch the GUI or ask for privacy permissions.
Use a new output directory each time; the tool refuses to overwrite a build.

## Make a personal DMG

```sh
python3 src/quest_usb.py --output "$HOME/Desktop/quest-usb-dmg-build" --make-dmg
```

This creates a DMG locally. Do not upload it to this public project or a public
fork without appropriate distribution permission. GitHub's Actions workflow
deliberately never publishes this DMG.

## Use an official installer you already downloaded

```sh
python3 src/quest_usb.py --dmg '/path/to/official.dmg' --output '/path/to/new-build'
```

The DMG must match the manifest exactly. `--source-app '/path/to/original.app'`
is also supported; the tool verifies the vendor signature, version, and executable
hash before copying. A previously patched app is not a valid source.

## Install somewhere else

```sh
./Install.command --destination "$HOME/Applications/Meta Quest Virtual Display.app"
```

Use one installation location consistently. The original and patched apps have
different top-level bundle IDs but share some upstream settings, helpers, and
protocol registrations. This is not complete side-by-side isolation. The patch
guards against starting a second desktop host; the unmodified app does not know
about that guard. Avoid starting it while the patched host is running. Launching
through Meta's existing login helper has not been validated for the new identity;
open the exact app in Finder instead.

## Backups and rollback

The installer builds and validates first, normally quits hosts, and then moves an
existing installation into `Quest VD USB Backups/<timestamp>/` beside the install
destination. The backup ends in `.app.backup` so macOS does not treat it as another
launchable app. Failed replacement restores the old app. Backups are never
silently deleted.

To roll back: quit the current app normally, move it out of Applications, move the
chosen backup back, and remove only the final `.backup` suffix. Open the restored
app. Do not run both. Physical-screen restoration happens through the host's
normal quit path; the installer does not kill it or fake blackout with a cover window.

## USB troubleshooting

- Use a cable that carries data. A charging connection alone does not establish USB streaming.
- Quit other Meta hosts before opening this one. A rejected duplicate exits immediately.
- Reopen the Quest client and select the Mac's USB entry when available.
- Check the Mac logs for a native USB session; cable presence alone is not proof of transport.
- The pipeline cannot test headset connectivity. Rebuilding does not force a 120 Hz Horizon compositor.

The patch does not replace Meta's screen-layout, aspect-ratio, blackout, or Quest
toolbar implementation. Those behaviors remain controlled by the upstream apps.
