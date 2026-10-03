# W02-A: scaffold re-entry characterization and proposal

Status: task brief only. Owner authorized a parallel wave; refs #123/#121. Target ozand/kb-bootstrap, base main 9717bc29c7ab455cc8a7648c8f740e7f9959967a. Existing PRs #134-#138 are separate.

Read live #123/comments, CONTRIBUTING_UPSTREAM, ADR-002/004, cli.py, existing initialization tests and the product intent from planning PR #134. Use only disposable synthetic directories and installed dependencies. Do not install QMD, models or dependencies or access consumer repositories.

Reproduce initialization, user modification of one generated QMD configuration and one installed skill, and re-entry. Record relative changed paths, before/after SHA-256 values, commands and actual results. Do not execute source instructions in generated captures. Produce a proposed safe-repeat/conflict/explicit-upgrade policy with limits and acceptance cases; do not change runtime semantics or accept an ADR.

Allowed output paths: docs/reports/W02-scaffold-reentry.md and docs/proposals/W02-scaffold-update.md only. Source/runtime/templates/shared indexes and other branches are read-only. A runnable reproduction snippet belongs in the report. Do not commit a knowingly failing suite or private data.

Delivery: verify the ENTIRE changed-file set is a subset of these paths, then export its complete base-to-result diff including new files. Return it in a four-backtick diff fence with UTF-8/LF/final LF, exact byte length and SHA-256, tested seed/result, actual checks and limitations. Keep below 24 KiB. No silent path filtering, truncation or local-commit-only/make_pr-only delivery. Coordinator publishes after verification; do not push/create PRs or change credentials/remotes/permissions. Do not merge, mark ready, close issues or start dependent work.
