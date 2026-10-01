# Bundled usage_widget_common

These stdlib-only helpers are included so a fresh clone runs independently.
They originate from the author's shared widget library, revision `08acaf0`.
They are distributed as part of this project under the root MIT license.

Modules: classified fetch errors, retry-once policy, sensitive-field redaction,
and primary/fallback/retained-data selection. Tests live in `tests/common`.
Changes to the separate development library are not pulled in automatically;
update this copy and run the full test suite when syncing shared changes.
