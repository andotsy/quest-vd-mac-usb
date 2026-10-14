# Signing

The runner verifies Meta’s original signature and hashes before patching. The DMG contains an ad-hoc signed app. The **Readme** commands sign your installed copy again, verify it, and remove quarantine from that app only.

Local signing does not provide Apple notarization. System-wide Gatekeeper settings stay unchanged.

## Permissions

The bundle ID is `io.github.quest-vd-mac-usb`. Grant Accessibility and Screen Recording to the installed copy, then restart it. Microphone is optional.

An ad-hoc identity can change between builds, so updates may need permission again. To reuse a Code Signing certificate from your Keychain, replace `--sign -` in the Readme commands with `--sign 'Your Code Signing Identity'`.

A self-signed certificate stays local; it doesn’t provide Developer ID trust. The commands never upload keys or grant privacy permissions. [Apple: signing identities](https://developer.apple.com/library/archive/technotes/tn2206/)
