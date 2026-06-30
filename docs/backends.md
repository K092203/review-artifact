# Backends

v0.1 supports four backends:

## `llm` (default, recommended)

Uses [simonw/llm](https://github.com/simonw/llm). Configure model via TOML or CLI:

```toml
[backend]
name = "llm"
command = "llm -m gpt-4o"
```

## `codex`

Uses Codex CLI in read-only sandbox mode:

```bash
codex exec --sandbox read-only <prompt>
```

## `custom`

Any read-only command that accepts prompt on stdin:

```toml
[backend]
name = "custom"
command = "my-reviewer --readonly"
prompt_stdin = true
```

## `fake`

Returns fixed output for tests and CI. No external AI call.

```bash
review-artifact logs examples/sample-results --backend fake
```

## Read-only guarantee

This CLI only **reads** files you point it at. Actual sandbox strength depends on the backend you choose. See [security.md](security.md).
