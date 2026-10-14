# Signing

The runner verifies Meta’s original signature and hashes before patching. The DMG contains an ad-hoc signed app; **Install.command** signs the installed copy again using macOS’s built-in tools.

This doesn’t provide notarization. Use Apple’s per-app **Open Anyway** option when needed. [Apple’s guide](https://support.apple.com/en-us/102445)

## Permissions

The bundle ID is `io.github.quest-vd-mac-usb`. Grant Accessibility and Screen Recording to the installed copy, then restart it. Microphone is optional.

An ad-hoc identity can change between builds, so updates may need permission again. For better continuity, use the same Code Signing certificate from your Keychain on each install:

```sh
security find-identity -v -p codesigning
./Install.command --identity 'Your Code Signing Identity'
```

A self-signed certificate stays local; it doesn’t provide Developer ID trust. The installer never uploads keys or grants privacy permissions. [Apple: signing identities](https://developer.apple.com/library/archive/technotes/tn2206/)
