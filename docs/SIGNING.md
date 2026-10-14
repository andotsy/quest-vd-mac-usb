# Signing, Gatekeeper, and permissions

The installer first verifies Meta's unmodified Developer ID signature and pinned
hashes. Patching invalidates that signature. It then signs the result locally.
This signature lets macOS validate the rebuilt code's integrity; it does not make
the result an Apple-notarized or official Meta release.

## Opening a local build

After attempting to open the app, macOS may offer **System Settings → Privacy &
Security → Open Anyway**. Approve this specific app only after reviewing its
source and origin. This is Apple's documented exception mechanism. Do not disable
Gatekeeper, SIP, or privacy protections, and do not use blanket quarantine-removal
commands. If the alert specifically reports malware or a damaged artifact,
investigate the cause instead of treating it as a routine unsigned-app prompt.

The source kit can also be obtained with `git clone` and built locally. Building
locally avoids distributing a modified vendor app; it is not notarization and
does not guarantee that macOS will show no prompt.

Source: [Apple — Safely open apps on your Mac](https://support.apple.com/en-us/102445).

## A stable bundle ID is necessary, but not sufficient

The production bundle ID is `io.github.quest-vd-mac-usb`. Moving from an old test
ID or Meta's original ID requires new **Accessibility** and **Screen Recording**
grants. Microphone permission is optional. Select the actual app in Applications,
then restart it after granting screen recording. Do not edit the TCC database.

By default, builds use an **ad-hoc signature**. Its identity can change when the
executable changes, so later updates may require permission grants again even
though the bundle ID and filename are unchanged. We do not promise otherwise.

For better identity continuity, use the same persistent code-signing certificate
for every build. A locally created certificate is enough for local signing;
it does not provide Developer ID trust. Use Keychain Access's Certificate Assistant
to create a self-signed **Code Signing** certificate for your own builds, protect
its private key, and follow macOS's certificate trust prompts if needed. Then list
available identities with:

```sh
security find-identity -v -p codesigning
```

Pass the same certificate's identity on installation and updates:

```sh
./Install.command --identity 'Your Local Code Signing Identity'
./Update.command --identity 'Your Local Code Signing Identity'
```

Alternatively export `QUEST_VD_SIGN_IDENTITY` in the Terminal session used to run
both commands. Certificate/requirement continuity improves the chance of retaining
grants, but macOS and managed-device policy still decide. The installer never
uploads signing keys, adds system-wide trust, or grants itself privacy permissions.

See [Apple TN2206 — Code Signing In Depth](https://developer.apple.com/library/archive/technotes/tn2206/)
and [TN3127 — Inside code signing: requirements](https://developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements).

## What would remove normal unsigned-distribution friction?

An authorized redistributor could sign with their own **Developer ID Application**
certificate, use the hardened runtime with appropriate entitlements, submit for
notarization, and staple the ticket. This requires Apple Developer Program access
and does not replace permission to distribute Meta's code. A self-signed or ad-hoc
certificate cannot provide the same trust. This project has neither bundled
Developer ID credentials nor a notarized patched-app download.

Source: [Apple — Developer ID](https://developer.apple.com/developer-id/).
