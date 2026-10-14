# Maintaining a reviewed patch

## Release decisions happen before app downloads

The Linux check job fetches Meta's small `binary-info` JSON and lists existing
GitHub releases. A matching `meta-<version>-usb.<revision>` tag, including a draft,
skips the macOS job entirely. API failures stop the run instead of being mistaken
for an absent release. A concurrency group serializes publishers in a repository.

The newest reviewed manifest is a floor during phased rollouts. If the feed is
older, retain that version. If the feed announces a newer version without a
manifest, fail visibly before downloading any DMG and retain the existing release.
A changed hash/size under the same upstream version also requires review.

## Supporting a new upstream version

1. Retrieve public version metadata. Download the original app directly from Meta
   for local analysis, and verify its Apple Developer ID signature and team ID.
2. Establish the new executable layout and relevant capture, display-mode, and
   encoder code paths. Review the semantics; do not carry offsets over blindly.
3. Add `manifests/<version>.json` with the exact official URL, DMG size/hash,
   executable hash, instruction addresses, before/after bytes, and patch revision.
4. Review the configuration gates, duplicate guard, and upstream update behavior.
   Meta may change the native USB implementation or remove it entirely.
5. Run the unit tests and local build. Check privacy grants and a real headset
   session separately. CI cannot prove USB streaming or delivered frame rate.
6. Commit the reviewed manifest and code. The workflow validates the artifact and
   publishes the source kit if that release tag does not already exist.

For a patcher change against the same Meta version, increment `patch_revision`.
Do not replace or delete an existing release to reuse its tag. Release checksums
identify bytes but are not a separate publisher signature; repository access must
be protected accordingly. Build inputs are pinned, but local compiler/signing
differences mean the final app is not promised to be byte-for-byte reproducible.

## Verify the publisher

```sh
python3 -m unittest discover -s tests -v
python3 src/release.py plan --repository YOUR_ACCOUNT/quest-vd-mac-usb
python3 src/quest_usb.py --output /path/to/new-private-build
python3 src/release.py package --version 110.0.0.1.108 \
  --report /path/to/new-private-build/verification.json \
  --repository YOUR_ACCOUNT/quest-vd-mac-usb --output dist
```

`package` uses a text-source allowlist. Do not replace it with an upload of the
workspace, build directory, or wildcard app archives. Do not add proprietary
binaries to Git, Git LFS, Actions artifacts, caches, Releases, or Pages.

## Updater and identities

`project.json` selects the release repository. The package step rewrites it to
the current fork, so a fork's updater stays with that fork. Bundle ID remains
`io.github.quest-vd-mac-usb` unless a maintainer intentionally changes it. Such a
change requires fresh macOS privacy grants. Keep a persistent signing identity
when practical; never commit its private key.

Known silent-updater configuration switches and Sparkle automatic-update
preferences are disabled in the patched host. The upstream manual update command
is not removed. Advise users to update through the release kit.
