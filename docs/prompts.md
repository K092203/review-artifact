# Prompts

Built-in presets live in `src/review_artifact/presets/`:

| Preset | Use case |
|--------|----------|
| `experiment_analysis` | **Primary** — HPC/job meta, stderr, resource triage |
| `log_analysis` | Build/test/runtime log failure analysis |
| `code_review` | Git diff / source review (secondary) |

Select with `--prompt`:

```bash
review-artifact logs results/latest --prompt experiment_analysis
```

All presets include read-only instructions and require a JSON findings block in the reviewer output.

Findings are **advisory**. File/line citations are best-effort and verified against collected content when possible.
