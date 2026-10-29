# Publication verification — 2026-10-29

PASS — 5 regression tests plus Python compilation. The real ours/icon_line source definitions
are tested through AST extraction without importing Win32/Pillow or triggering downloads/INI writes.
SKIPPED — 1 real temporary-symlink case: Windows privilege error 1314; this is not counted as passed.

NOT RUN — applying/undoing icons in user folders, font downloads, Windows Explorer refresh/rendering.
The previous prefix-only implementation failed the quoted-resource and sibling-directory tests.

Source confidentiality/provenance review: complete explicit source allowlist; no user/runtime data copied.
