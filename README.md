<p align="center">
  <img src="assets/hero.svg" alt="Meta Quest Virtual Display USB" width="100%">
</p>

# Meta Quest Virtual Display USB

A patch for Meta’s official Mac app: **USB streaming**, with a **120 FPS target**.

Tested on **M4 + Quest 3**. Delivered 120 Hz isn’t verified. [Measurements →](docs/PERFORMANCE.md)

## Get it

1. **[Fork this repo](https://github.com/andotsy/quest-vd-mac-usb/fork).** Enable Actions in your fork.
2. Run **Actions → Build DMG**, with the default options.
3. Download the run’s artifact, unzip it, and open the **DMG**.
4. Run **Install.command**, then open **Meta Quest Virtual Display** from Applications.

Allow Accessibility and Screen Recording, restart when asked, and connect your Quest with a USB data cable.

GitHub downloads, patches, and packages the latest reviewed Meta build. **No Xcode needed on your Mac.**

Apple Silicon · macOS 13.3+ · Meta’s Quest Virtual Display client

## Next time

**Sync your fork → run Build DMG again.** Unchanged builds are reused; artifacts last 7 days. New Meta versions need compatibility review.

Locally signed, not notarized. If macOS blocks it, use **Privacy & Security → Open Anyway**. [Install & signing](docs/INSTALL.md) · [Build details](docs/MAINTAINING.md)

Independent project. MIT covers our code; Meta’s terms still apply. Public-fork artifacts are downloadable by other signed-in users—use a private copy to restrict access. [Distribution](docs/DISTRIBUTION.md)
