# Build details

**Build DMG** runs manually in the repository where you start it, on a macOS ARM runner. No Releases are created.

1. Read Meta’s small version feed.
2. Pick Meta’s latest build and look for a successful, unexpired artifact.
3. If needed, download from Meta, verify its hash and vendor signature, then patch.
4. Read version and minimum macOS from the bundled app, build the Finder layout
   with a versioned volume name, and verify mounted metadata. Test drag-copy,
   Readme signing, quarantine removal, and app identity checks.
5. Upload the DMG directly as a file artifact; retention is 7 days.

The artifact key includes the upstream hash and build inputs. Unchanged runs link to the existing artifact before fetching the app. **Build again** bypasses reuse. API failures stop the run.

## Version selection

The newest reviewed version is a floor when Meta’s feed lags behind a rollout. A newer or changed release is built from the feed’s size and hash, with a warning listing the reviewed versions; Meta’s signature must verify and every patch pattern must match exactly once. An unreviewed URL stops before downloading.

The optional URL accepts a reviewed Meta binary, including regional CDN URLs with the same download ID. Every download still requires the exact size, hash, vendor signature, and original instructions.

## Updating the patch

Patches find their code by instruction shape: opcodes and constants must match, while registers, memory offsets, and branch targets may move. A pattern that matches zero or several times stops the build.

To review a new binary, check its capture, display, encoder, and transport paths, then add its exact metadata and patterns in `manifests/`. Refresh the patterns from that binary when Meta’s code changes. Increment `patch_revision` for patch changes.

```sh
python3 -m unittest discover -s tests
```

Sync the fork, then run **Build DMG**. CI verifies packaging; headset testing remains separate. Keys and vendor binaries stay out of Git.
