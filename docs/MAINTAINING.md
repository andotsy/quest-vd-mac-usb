# Build details

**Build DMG** runs manually in the repository where you start it, on a macOS ARM runner. No Releases are created.

1. Read Meta’s small version feed.
2. Match a reviewed manifest and look for a successful, unexpired artifact.
3. If needed, download from Meta, verify its hash and vendor signature, then patch.
4. Build the Finder layout; test drag-copy, Readme signing, quarantine removal, and app identity checks.
5. Upload the DMG directly as a file artifact; retention is 7 days.

The artifact key includes the upstream hash and build inputs. Unchanged runs link to the existing artifact before fetching the app. **Build again** bypasses reuse. API failures stop the run.

## Version selection

The newest reviewed version is a floor when Meta’s feed lags behind a rollout. A newer unknown version, changed hash, or unreviewed URL stops before downloading.

The optional URL accepts a reviewed Meta binary, including regional CDN URLs with the same download ID. Every download still requires the exact size, hash, vendor signature, and original instructions.

## Updating the patch

Review the new binary’s capture, display, encoder, and transport paths. Add its exact metadata and instruction edits in `manifests/`. Never carry offsets forward blindly. Increment `patch_revision` for patch changes.

```sh
python3 -m unittest discover -s tests
```

Sync the fork, then run **Build DMG**. CI verifies packaging; headset testing remains separate. Keys and vendor binaries stay out of Git.
