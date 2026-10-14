# Install

Download and open your **Build DMG** artifact, and run **Install.command**. It copies the app into Applications, signs it locally, and saves your previous copy in **Quest VD USB Backups**.

Open **Meta Quest Virtual Display**. Allow Accessibility and Screen Recording; restart when asked. Connect your Quest and choose the Mac’s USB entry.

If macOS blocks opening the installer or app, use **System Settings → Privacy & Security → Open Anyway**. The build isn’t notarized. [Apple’s guide](https://support.apple.com/en-us/102445) · [Signing](SIGNING.md)

## Options

Run these from the mounted DMG in Terminal:

```sh
# Verify without installing or stopping your session
./Install.command --check

# Install in your own Applications folder
./Install.command --destination "$HOME/Applications/Meta Quest Virtual Display.app"

# Reuse a local signing certificate
./Install.command --identity 'Your Code Signing Identity'
```

No Python, Xcode, or Command Line Tools are needed to install.

## Update or restore

Sync your fork and run **Build DMG** again. Install the new DMG the same way. Use this flow instead of Meta’s in-app updater, which can replace the patch.

To restore: quit the app, move it aside, and move your saved `.app.backup` into Applications. Remove the final `.backup` suffix. Keep one host running at a time.

## USB missing?

Use a data cable, quit other Meta hosts, then reopen the Quest client. A connected cable alone doesn’t confirm USB transport.
