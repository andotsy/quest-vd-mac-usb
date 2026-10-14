# Why releases contain an installer kit, not Meta's app

Meta Quest Virtual Display is proprietary software. Its public download being
free does not by itself grant permission to redistribute it or derivative builds.
Meta's supplemental terms, section 2.1, restrict copying, modification, derivative
works, distribution, and reverse engineering unless authorized, with qualifications
for applicable law. Applicability and legal exceptions depend on the circumstances.

Sources, checked 2026-10-14:

- [Meta Platforms Technologies supplemental terms](https://www.meta.com/legal/supplemental-terms-of-service/)
- [Regional terms consulted, section 2.1](https://www.meta.com/de/legal/supplemental-terms-of-service/)
- [GitHub Acceptable Use Policies, intellectual property](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies#3-intellectual-property-authenticity-and-private-information)

No permission to redistribute this app was identified. GitHub permitting release
uploads technically is not permission from a copyright holder. A public Actions
artifact is also a distribution; moving a DMG there does not solve the issue.

## What this project publishes

- Original installer/patcher source and artwork under MIT.
- Version metadata, hashes, and minimal instruction edits needed by the patcher.
- An installer ZIP containing that source, plus checksums and a verification report.

It does not publish Meta executables, app bundles, frameworks, APKs, DMGs, icons,
decompiled application code, credentials, or signing keys. Each user downloads
the official app directly from Meta and builds a local copy. CI does the same in
an ephemeral runner to verify a release, then removes the vendor files without
uploading them.

This reduces redistribution exposure. It is **not a legal opinion or a guarantee**
that creating or using a patch is permitted under every applicable agreement or
law. A fork does not obtain additional rights to Meta's software. If you need a
definitive legal basis for public patched-app distribution, obtain Meta's written
permission and advice from a qualified lawyer familiar with your jurisdiction.

No license, payment, authentication, or macOS privacy-consent checks are bypassed.
The project enables existing transport configuration and changes frame-rate
instructions. The project name identifies compatibility; it does not imply Meta
endorsement. Existing vendor copyright notices remain in locally built apps.
