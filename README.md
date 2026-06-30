> 🌐 **日本語版 README は [README.ja.md](README.ja.md) にあります。**

# review-artifact

**Read-only AI triage for experiment artifacts (logs, job outputs), plus diffs
and files.** Point it at a job's logs, a diff, or any files; it saves the review
as reproducible **Markdown / JSON**. **The reviewer never edits your repo.**

```text
Triage your experiment artifacts with a read-only AI.
Point it at a job's logs (meta.json, stderr, resource), a diff, or any files,
and save the review as reproducible Markdown/JSON — the reviewer never edits your repo.
```

- **Status:** v0.1.0 (pre-release) · MIT · pure standard library, no runtime dependencies
- **Verified:** 21 tests passing on Python 3.12 / Linux (WSL2), 2026-06-30 — see [Verification](#verification)
- **Known limitation:** real LLM backends are manually verified only; CI uses the fake backend (see [Known limitations](#known-limitations))

---

## Why

You ran a job; `meta.json` / `stderr` / `resource` don't immediately tell you if
it failed, timed out, or hit a bottleneck. `review-artifact` triages that with a
**read-only** AI and saves the result as an artifact — instead of letting an
agent mutate your repo. The primary use case is **experiment log triage**; diff
and file review are secondary.

## How it differs

| vs | what review-artifact adds |
|----|---------------------------|
| **fabric / llm / mods** | Target collectors (git diff, log bundle, files) + **outcome-aware JSON findings** + saved **artifact files**. Those tools stop at "text → AI → text". |
| **CodeRabbit / Copilot / PR bots** | **Local, read-only, artifact-first**, and centered on **experiment logs** — not server-side PR diffs. |

**The wedge:** you ran jobs whose `meta.json`/`stderr`/`resource` don't make the
failure or bottleneck obvious, and you want a read-only, structured triage saved
as an artifact. Diff review is supported but secondary.

## What makes the artifact trustworthy

1. **Read-only by contract** — the CLI only reads what it collects; the prompt
   tells the reviewer it cannot edit. No agent mutates your repo.
2. **Line citations are verified** — LLMs hallucinate file/line. Every cited
   `file`/`line` is checked against the actually-collected content; unverifiable
   ones are nulled (`line_verified: false`). Findings are always advisory.
3. **Secrets are skipped by default** — `.env`, `*.pem`, `*token*`, etc. are not
   collected unless you pass `--allow-sensitive`.

All three are demonstrated in [Verification](#verification).

## Install

```bash
cd review-artifact
pip install -e ".[dev]"
```

Requires Python 3.11+. No third-party runtime dependencies (pytest is dev-only).

## Quickstart (logs first)

```bash
# Primary: triage job artifacts with the fake backend (no API key needed)
review-artifact logs examples/sample-results --backend fake

# Inspect exactly what would be sent, without calling any AI
review-artifact logs examples/sample-results --dry-run

# With simonw/llm (install llm separately)
review-artifact logs results/latest --backend llm --language ja

# Secondary: diff / file review
review-artifact diff --dry-run
review-artifact files README.md --backend fake
```

Artifacts are written to `.review/` by default (`<ts>-<target>.md` / `.json`).

## Commands

```bash
review-artifact logs <dir>          # ★ primary: job/experiment log triage
review-artifact diff                # git diff review (secondary)
review-artifact files <paths...>    # file review
review-artifact ask "question" --files src/foo.cpp
```

## Output artifact (JSON, schema v1)

```json
{
  "schema_version": 1,
  "summary": "...",
  "findings": [
    {
      "severity": "medium",
      "title": "...",
      "body": "...",
      "file": null,
      "line": null,
      "line_verified": false,
      "confidence": "medium"
    }
  ],
  "open_questions": [],
  "raw_output": "..."
}
```

Markdown is for humans; JSON is for CI / bots / another AI. Findings are
**advisory** — file/line citations are verified against collected content when
possible, and unverified lines are nulled.

## Backends (multi-backend from v0.1)

| Backend | Description |
|---------|-------------|
| `llm` | [simonw/llm](https://github.com/simonw/llm) — **recommended default** |
| `codex` | `codex exec --sandbox read-only` |
| `custom` | any read-only command (prompt on stdin) |
| `fake` | fixed output for tests / CI (no network) |

See [docs/backends.md](docs/backends.md).

## Verification

Captured on **Python 3.12.3 / Linux 6.18 (WSL2) / 2026-06-30**.

### Test suite — 21 passing

```text
tests/test_artifacts.py  2   (artifact naming, markdown + json writers)
tests/test_cli.py        3   (logs/diff/files via fake backend)
tests/test_collect.py    7   (git/file/dir collectors, size limit, binary + secret skip)
tests/test_config.py     4   (defaults, TOML override, merge)
tests/test_findings.py   5   (JSON extraction, line verification valid/invalid/out-of-range)
                        ---
                         21   passed in 0.18s
```

### Behavioral checks (end-to-end, fake backend)

| Behavior | Command | Observed |
|----------|---------|----------|
| Log triage (primary) | `logs examples/sample-results --backend fake` | wrote `.review/…-logs….md` + `.json` |
| **Line verification** | fake cites `results/latest/stderr.txt:42` | collected file was `examples/sample-results/stderr.txt` → normalized to `file=null line=null line_verified=false` |
| Dry-run (no AI call) | `logs … --dry-run` | prints the exact collected bundle, calls nothing |
| **Secret guard** | `files .env --dry-run` | `skipped .env: sensitive` (needs `--allow-sensitive` to include) |
| Backend selection | `--backend bogus` | `invalid choice … (llm, codex, custom, fake)`, `exit=2` |

Representative output:

```console
$ review-artifact logs examples/sample-results --backend fake
wrote .review/20260630-235029-logs-examples-sample-results.md
wrote .review/20260630-235029-logs-examples-sample-results.json
# findings[0].file = null, line = null, line_verified = false
#   (the fake reviewer cited results/latest/stderr.txt:42, which was NOT collected)

$ review-artifact files .env --dry-run
--- COLLECTION NOTES ---
skipped .env: sensitive
```

CI runs the same suite on Python 3.12 with the fake backend (no API calls).

## Security

- Sends collected file contents to your configured AI backend.
- Skips sensitive-looking files by default (`.env`, `*.pem`, `*token*`, etc.).
- Use `--allow-sensitive` only when intentional.
- The secret guard is a helper, not a guarantee — review before sharing.
- See [docs/SECURITY.md](docs/SECURITY.md).

## Documentation

- [docs/configuration.md](docs/configuration.md) — `.review-artifact.toml`
- [docs/backends.md](docs/backends.md) — llm / codex / custom / fake
- [docs/prompts.md](docs/prompts.md) — prompt presets
- [docs/SECURITY.md](docs/SECURITY.md) — secret handling

Examples: [examples/sample-results](examples/sample-results) (fake-backend demo),
[examples/fugaku-results.toml](examples/fugaku-results.toml) (HPC config example).

## Pairs with runledger

```bash
runledger run -- ./solver < input.txt
review-artifact logs runs/latest      # read-only AI triage of the snapshot
```

## Known limitations

- **Real LLM backends (`llm`, `codex`) are manually verified only.** CI and the
  automated tests use the `fake` backend so no network/API call is made.
- **Read-only strength depends on the backend's sandbox.** The CLI itself only
  reads, but it cannot guarantee a backend won't take actions of its own.
- **Line verification and JSON findings are best-effort.** When the reviewer's
  JSON cannot be parsed, the artifact keeps `raw_output` with `findings: []`.

## Non-goals (v0.1)

Auto-fix / auto-commit, GitHub PR comment bot, web UI / TUI, full provider
abstraction, security-audit tooling.

## License

MIT — see [LICENSE](LICENSE).
