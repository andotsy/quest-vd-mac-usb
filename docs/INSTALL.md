# Install

1. Download and open your **Build DMG** artifact.
2. Quit Meta Quest Virtual Display, then drag the app to **Applications**.
3. Open **Readme.html** in the DMG and click **Copy command**. Open the **Terminal** shortcut, paste with **⌘V**, and press **Return**.
4. Open **Meta Quest Virtual Display** from Applications.

Allow Accessibility and Screen Recording, then restart when asked. Connect your Quest with a USB data cable and choose your Mac’s USB entry.

The guide works offline with built-in styling and a copy button. If clipboard access is blocked, it selects the command for manual copying.

The commands use built-in macOS tools to sign the installed app and remove its download quarantine. No installer executable, Xcode, or extra tools. [Signing](SIGNING.md)

## Updates

Sync your fork and run **Build DMG** again. Install the new DMG the same way, replacing the previous copy. Keep a copy yourself if you want to roll back. Meta’s automatic updater is disabled to preserve the patch.

## USB missing?

Use a data cable, quit other Meta hosts, then reopen the Quest client. Keep one host running at a time. A connected cable alone doesn’t confirm USB transport.
