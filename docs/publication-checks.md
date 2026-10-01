# Publication checks — 2026-10-01

This report records the checks performed when preparing the project for public review.
It is a snapshot, not a guarantee about future commits or all possible vulnerabilities.

## Repository and history

- The public `origin/main` was fetched before comparison; it pointed to `d38a3e9`.
- Local history at `ee45255` was 116 commits ahead of that public version.
- Gitleaks 8.30.1 was downloaded from the official GitHub release and its archive
  was checked against the release SHA-256 checksum list.
- `gitleaks git . --log-opts=--all --redact=100` found no secrets.
- In addition to scanning diffs, all reachable historical blobs, commits and tags
  were exported and scanned in full: 128 commits, 222 blobs, 2 annotated tag objects.
  This scan also found no secrets. Binary assets were not OCR-scanned.
- Historical tracked filenames were checked for browser profiles, credentials,
  runtime settings/history and logs; none of those runtime files were tracked.
- A separate scan of the clean publication file set found no secrets.
- Local Chrome session files do contain sensitive data. They remain ignored and
  are excluded from the publication copy. Raw local scan reports are also ignored.

The scanner uses known patterns and heuristics. These results do not rule out
unknown credential formats, all personal data, unreachable/deleted Git objects,
or security defects in application behavior. Normal Git author metadata remains
in history. No history rewriting or credential rotation was needed for the
published file set based on these findings.

## Reproducibility

The previously unpublished `usage_widget_common` dependency is now bundled in this
repository, along with its tests. The imports no longer modify `sys.path` to load
a sibling checkout. The original shared-library checkout was left unchanged.

Validation used a separate copy of the publishable files in a directory with no
sibling `usage_widget_common`, plus a newly created Python 3.14 virtual environment:

- Dependencies installed from `requirements-dev.txt` successfully.
- `python -m pip check`: no broken requirements.
- `python -m pytest -q`: **90 passed**.
- `python demo.py --screenshot ...`: launched the actual Tkinter UI and saved its
  window successfully, without account login or browser/network fetching.
- A regression test separately imports the application from a temporary standalone
  copy and asserts that the bundled package is the one loaded.

GitHub Actions is configured to run the suite on Windows with Python 3.12.
Live ChatGPT authentication and usage fetching were not re-tested during this
publication task. Automated tests mock network calls; the demo uses synthetic data.

## Screenshots and sharing

The English and Russian screenshots were captured from the actual application UI
using the offline demo, inspected visually, and contain only synthetic values.
The demo redirects local state to a temporary folder and does not connect to the
running widget's single-instance listener or create an extra tray icon.

Share the GitHub repository URL or its source ZIP. Do not archive the local working
folder: it also contains ignored browser sessions and other private runtime data.
