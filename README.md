<p align="center">
  <img src="assets/hero.svg" alt="Meta Quest Virtual Display USB — your Mac, through one cable, into your space" width="100%">
</p>

<p align="center">
  <a href="https://github.com/andotsy/quest-vd-mac-usb/releases/latest"><strong>Get the installer kit ↗</strong></a>
  &nbsp; · &nbsp;
  <a href="#install">Install</a>
  &nbsp; · &nbsp;
  <a href="#updates">Updates</a>
  &nbsp; · &nbsp;
  <a href="#fork-it-build-it-yourself">Build your own</a>
</p>

<p align="center">
  <img alt="Tests" src="https://github.com/andotsy/quest-vd-mac-usb/actions/workflows/test.yml/badge.svg">
  <img alt="Release checks" src="https://github.com/andotsy/quest-vd-mac-usb/actions/workflows/release.yml/badge.svg">
  <img alt="Platform: Apple Silicon" src="https://img.shields.io/badge/Apple_Silicon-macOS_13.3%2B-131d2c?style=flat-square">
</p>

# Meta Quest Virtual Display USB

**The familiar Quest desktop window. A wired connection to your Mac.**

A small, inspectable patch kit for Meta Quest Virtual Display on Apple Silicon. It enables the Mac app's existing native USB transport and requests a higher capture frame rate. Keep Meta's normal Quest window, desktop controls, and display handling, with a cable carrying the desktop session.

Independent community project. **Not affiliated with, endorsed by, or supported by Meta.** Meta's software is downloaded directly from Meta; it is not included in this repository or its release assets.

### One cable. The same desktop.

| | What you get |
|:--|:--|
| **Native USB** | Activates the transport already present in Meta's host. No adb install, adb server, custom tunnel, or patched Quest APK. |
| **A normal Quest window** | Uses the official Virtual Display client and its existing Horizon interface. |
| **120 FPS requested** | Patches capture, virtual-display modes, and encoder expectations. Actual delivery depends on the Mac, cable, client, and headset runtime. |
| **A finished identity** | App name: **Meta Quest Virtual Display**. Bundle ID: `io.github.quest-vd-mac-usb`. |
| **Reproducible patch inputs** | Pinned official DMG hash, Meta developer-signature check, executable hash, and exact instruction guards. |
| **Updates you control** | Daily upstream checks; reviewed releases only. Installation backs up the previous app. |

> **120 FPS is a target, not a benchmark result.** Native USB was observed on a MacBook Pro M4 + Quest 3. In that session, the Mac requested 120 FPS while Horizon presented at **72 Hz**. This project does not claim verified 1440p at 120 Hz, and it does not force the Quest refresh rate. [Measurements →](docs/PERFORMANCE.md)

## Install

Requires an **Apple Silicon Mac**, macOS 13.3 or later, Apple Command Line Tools, a USB data cable, and Meta's official Quest Virtual Display client. Only M4 + Quest 3 has been tested. Meta account/pairing requirements still apply.

1. Download the versioned installer ZIP and `SHA256SUMS` from [Releases](https://github.com/andotsy/quest-vd-mac-usb/releases/latest). The ZIP contains our source and installer, not Meta's app.
2. Compare the ZIP's SHA-256 with the matching entry in `SHA256SUMS`. For example, run `shasum -a 256 ~/Downloads/quest-vd-mac-usb-*.zip`.
3. Extract the ZIP. Review the code if desired. If you do not have Apple's build tools, run `xcode-select --install` once and let that installation finish.
4. Double-click **Install.command**, or run `./Install.command` in the extracted directory. It downloads the exact reviewed Meta version, verifies it, builds locally, normally quits existing Meta hosts, and installs the app in `/Applications`. An active desktop session will disconnect during replacement.
5. Open **Meta Quest Virtual Display** from Applications. Grant **Accessibility** and **Screen Recording** to this copy. Microphone access is optional. Restart the app after granting screen recording if prompted.
6. Connect the USB data cable, open Virtual Display on the Quest, and select the Mac's USB entry when shown.

The running app is self-contained. Build tools are needed to create or update it, not to run it. The installer never launches another Meta host automatically.

**Gatekeeper:** the rebuilt app is locally signed, not notarized by Apple. If macOS blocks it, attempt to open it, then use **System Settings → Privacy & Security → Open Anyway** for this app, where available. Leave Gatekeeper enabled. [Signing and permissions →](docs/SIGNING.md)

For a local DMG, an alternate installation folder, a persistent signing identity, or rollback instructions, see [Advanced installation](docs/INSTALL.md).

## Updates

Keep the extracted kit. Run **Update.command** whenever you want to update. It checks the latest GitHub release before fetching an installer, skips an already installed release, verifies the release ZIP checksum, then downloads the corresponding app directly from Meta and rebuilds it locally. It refuses to downgrade an installed upstream version. A Meta update is available here only after its patch has been reviewed.

To check without installing:

```sh
./Update.command --check
```

You can also watch this repository's **Releases** and download each new kit manually. Use this updater instead of Meta's in-app **Check for Updates**, which can install an unpatched host. The patch disables the known silent-update switches and Sparkle automatic checks; manually requesting a Meta update is still outside this update flow.

### How the release pipeline works

```text
Meta version metadata → release already exists? → stop, no DMG download
                     → unsupported newer build? → stop for compatibility review
                     → reviewed new release → download from Meta
                                            → validate signature + hashes
                                            → patch + sign + smoke-test on macOS
                                            → publish source installer + checksums
```

The workflow runs daily at **08:23 UTC**, on relevant pushes, and through **Run workflow**. Release tags combine the Meta version and patch revision, such as `meta-110.0.0.1.108-usb.1`. Serialized runs prevent competing publishers. A new patch revision can release against the same Meta version.

**Upstream rollouts can lag:** during initial setup, Meta's public feed advertised 109 while a verified official 110 download was already available. The project preserves the newest reviewed version rather than downgrading. New executable layouts are never patched with old offsets. [Maintenance guide →](docs/MAINTAINING.md)

## Fork it. Build it yourself.

Want a clean build from code you can inspect?

1. Fork this repository.
2. Review `src/`, the version manifest, and the workflow.
3. Enable Actions in your fork, then run **Check Meta and release installer**.
4. Download your fork's release kit and build on your Mac. Packaged update settings automatically point to your fork.

No Meta credentials, Apple signing keys, or personal access token are required by the workflow. It uses the fork's scoped `GITHUB_TOKEN`. Public workflow assets contain **only this project's source, manifests, checksums, and verification report**. The downloaded and patched Meta app exists only on the temporary runner and is removed; it is never uploaded as a release or Actions artifact.

You can also build straight from a checkout:

```sh
git clone https://github.com/andotsy/quest-vd-mac-usb.git
cd quest-vd-mac-usb
python3 -m unittest discover -s tests -v
./Install.command
```

For a forked checkout, change `project.json` to your fork before using `Update.command`. A packaged fork release does this automatically.

## Distribution and rights

**Free to download does not mean free to redistribute.** Meta's supplemental terms restrict modification and distribution absent authorization, subject to applicable law. Publishing only our patching tools avoids hosting Meta's proprietary app; it does **not** establish that every use of the tools is authorized in every jurisdiction.

We do not publish patched Meta DMGs. If you need to redistribute the app itself, obtain appropriate permission from Meta and legal advice for your situation. This project's MIT license covers our original code only. [Distribution policy and sources →](docs/DISTRIBUTION.md)

---

Made for a less wireless desktop. **Small patch. Visible source. Your own build.**
