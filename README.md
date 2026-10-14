<p align="center">
  <img src="assets/hero.svg" alt="Meta Quest Virtual Display USB — enable USB transport and request 120 FPS" width="100%">
</p>

# Meta Quest Virtual Display USB

A patch for Meta's official Mac app that:

- **Enables its built-in USB transport** for wired desktop streaming to Quest.
- **Requests 120 FPS capture and encoding**, with 120 Hz virtual-display modes.

Tested on MacBook Pro M4 + Quest 3. The measured Quest session presented at **72 Hz**; delivered 120 Hz has not been verified. [Measurements](docs/PERFORMANCE.md).

**[Download the installer kit →](https://github.com/andotsy/quest-vd-mac-usb/releases/latest)**

## Install

Requires Apple Silicon, macOS 13.3+, Apple Command Line Tools, a USB data cable, and Meta's Quest Virtual Display client.

1. Download the ZIP and verify its checksum against `SHA256SUMS` from the release.
2. Extract it and run **Install.command**. If needed, install Apple's tools first with `xcode-select --install`.
3. Open **Meta Quest Virtual Display** from Applications. Grant Accessibility and Screen Recording, then restart the app if prompted.
4. Connect the cable and select your Mac's USB entry in the Quest client.

The installer downloads the supported app directly from Meta, verifies and patches it locally, and backs up your previous installation.

The result is locally signed, not notarized. If macOS blocks it, use **Privacy & Security → Open Anyway**. [Signing and permissions](docs/SIGNING.md) · [Advanced installation and rollback](docs/INSTALL.md).

## Updates

Run **Update.command** to install the latest reviewed release, or `./Update.command --check` to check only. Use it instead of Meta's in-app updater, which can replace the patch.

GitHub Actions checks Meta's version daily, skips existing releases before downloading, and builds verified installer kits. New Meta versions require compatibility review. [Pipeline details](docs/MAINTAINING.md).

<a id="fork-it-build-it-yourself"></a>

## Build your own

Fork this repository, enable Actions, and run **Check Meta and release installer**. Download your fork's kit and run it on your Mac. Its updater will follow your fork's releases.

## License

Independent project, unaffiliated with Meta. Releases contain patching tools only; Meta's app is downloaded directly from Meta. MIT covers this project's code. Meta's terms and applicable law still apply. [Distribution policy](docs/DISTRIBUTION.md).
