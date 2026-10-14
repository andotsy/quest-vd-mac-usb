# Install

1. Download and open your **Build DMG** artifact.
2. Quit Meta Quest Virtual Display, then drag the app to **Applications**.
3. Open **Readme** in the DMG. Paste its command block into Terminal.
4. Open **Meta Quest Virtual Display** from Applications.

Allow Accessibility and Screen Recording, then restart when asked. Connect your Quest with a USB data cable and choose your Mac’s USB entry.

The commands use built-in macOS tools to sign the installed app and remove its download quarantine. No installer executable, Xcode, or extra tools. [Signing](SIGNING.md)

## Updates

Sync your fork and run **Build DMG** again. Install the new DMG the same way, replacing the previous copy. Keep a copy yourself if you want to roll back. Meta’s automatic updater is disabled to preserve the patch.

## USB missing?

Use a data cable, quit other Meta hosts, then reopen the Quest client. Keep one host running at a time. A connected cable alone doesn’t confirm USB transport.
