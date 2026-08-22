# Downstream push safety

Push configuration is explicit operator setup. `kb-bootstrap` does not change Git
remotes, credentials, `remote.pushDefault`, or branch `pushRemote` automatically.

## Precedence

For `git push` without an explicit remote:

1. `branch.<name>.pushRemote` applies to the current branch when configured.
2. Otherwise `remote.pushDefault` applies to the checkout.
3. If neither is configured, Git's other push resolution rules apply and may be
   ambiguous in a multi-remote consumer checkout.

Therefore downstream repositories should use consumer `origin` at both levels:

```bash
git config --local remote.pushDefault origin
git config --local branch.<branch>.pushRemote origin
```

## Verify before a downstream push

```bash
kb-bootstrap doctor --repo example/consumer-project
git config --local --get remote.pushDefault
git config --local --get branch.<branch>.pushRemote
git remote get-url --push origin
git push --dry-run
```

The two config commands must print `origin`. Do not include a push URL in receipts;
it may contain credentials. Record only the sanitized repository identity, branch,
commit, and dry-run result.

## Explicit upstream contribution

Upstream changes use the separate checkout/worktree described in
[`CONTRIBUTING_UPSTREAM.md`](CONTRIBUTING_UPSTREAM.md). From that checkout, name
the push remote and branch explicitly:

```bash
kb-bootstrap doctor --repo ozand/kb-bootstrap
git push --dry-run origin feat/example-upstream-change
git push -u origin feat/example-upstream-change
gh pr create \
  --repo ozand/kb-bootstrap \
  --base main \
  --head feat/example-upstream-change
```

For a fork, replace `origin` with the explicitly verified fork remote and provide
`owner:branch` to `--head`.

Never change the consumer checkout's default push target to perform upstream work.
Do not modify remote URLs, credentials, or force-push settings as part of this
workflow.
