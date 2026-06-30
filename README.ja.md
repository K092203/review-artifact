> 🌐 **English README is at [README.md](README.md).**

# review-artifact

**実験成果物(ログ・ジョブ出力)・差分・任意ファイルを read-only の AI で triage する CLI。**
ジョブのログ・差分・ファイルを渡すと、レビュー結果を再現可能な **Markdown / JSON** として保存します。
**reviewer はあなたのリポジトリを書き換えません。**

```text
実験ログ・ジョブ成果・差分を、読み取り専用の AI に解析させ、結果を
Markdown / JSON の成果物として残す。reviewer はリポジトリを書き換えない。
「回したが何が起きたか分からないログ」の triage が主用途。
```

- **ステータス:** v0.1.0(プレリリース)· MIT · 標準ライブラリのみ、実行時の外部依存ゼロ
- **検証:** Python 3.12 / Linux (WSL2) 上でテスト21件 green(2026-06-30)— [検証結果](#検証結果)参照
- **既知の制約:** 実 LLM バックエンドは手動検証のみ。CI は fake バックエンドを使用([既知の制約](#既知の制約)参照)

---

## なぜ作るか

ジョブを回したものの、`meta.json` / `stderr` / `resource` を見ても、失敗したのか・timeout
したのか・ボトルネックに当たったのかが即座には分からない。`review-artifact` はそれを
**read-only** の AI で triage し、結果を成果物として保存します — エージェントにリポジトリを
書き換えさせる代わりに。主用途は**実験ログの triage**で、差分・ファイルレビューは副次的です。

## 既存ツールとの違い

| 比較対象 | review-artifact が足すもの |
|---|---|
| **fabric / llm / mods** | target collector(git diff / ログ束 / ファイル)+ **outcome 付き JSON findings** + **成果物ファイル保存**。これらは「テキスト → AI → テキスト」止まり。 |
| **CodeRabbit / Copilot / PR bot** | **ローカル・read-only・成果物優先**で、サーバ側 PR 差分ではなく**実験ログ**が中心。 |

**主対象(wedge):** `meta.json`/`stderr`/`resource` を見ても失敗・ボトルネックが即断できない
ジョブ群を、read-only で構造化 triage して成果物に残したい人。差分レビューは対応するが“ついで”。

## 成果物を信頼できるものにする3点

1. **契約として read-only** — CLI は収集対象を読むだけ。prompt でも「編集できない」と明示。
   エージェントがリポジトリを変更しない。
2. **行番号を検証する** — LLM は file/line を捏造する。引用された `file`/`line` を**実際に
   収集した内容に対して検証**し、確認できないものは null 化(`line_verified: false`)。
   findings は常に advisory。
3. **秘密情報は既定でスキップ** — `.env` / `*.pem` / `*token*` 等は `--allow-sensitive`
   を付けない限り収集しない。

3点とも[検証結果](#検証結果)で実証しています。

## インストール

```bash
cd review-artifact
pip install -e ".[dev]"
```

Python 3.11 以上が必要。実行時の外部依存はありません(pytest は開発用のみ)。

## クイックスタート(logs が主役)

```bash
# 主用途: fake バックエンドでジョブ成果を triage（API キー不要）
review-artifact logs examples/sample-results --backend fake

# AI を呼ばずに「何を送るか」だけ確認
review-artifact logs examples/sample-results --dry-run

# simonw/llm を使う場合（llm は別途インストール）
review-artifact logs results/latest --backend llm --language ja

# 副次: 差分 / ファイルレビュー
review-artifact diff --dry-run
review-artifact files README.md --backend fake
```

成果物は既定で `.review/` に出力されます(`<ts>-<target>.md` / `.json`)。

## コマンド

```bash
review-artifact logs <dir>          # ★ 主用途: ジョブ/実験ログの triage
review-artifact diff                # git diff レビュー（副次）
review-artifact files <paths...>    # ファイルレビュー
review-artifact ask "質問" --files src/foo.cpp
```

## 出力成果物（JSON, schema v1）

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

Markdown は人間向け、JSON は CI / bot / 別 AI 向け。findings は **advisory** で、
file/line は可能な限り収集内容に対して検証し、未検証の行は null 化します。

## バックエンド（v0.1 から multi-backend）

| バックエンド | 説明 |
|---|---|
| `llm` | [simonw/llm](https://github.com/simonw/llm) — **既定推奨** |
| `codex` | `codex exec --sandbox read-only` |
| `custom` | 任意の read-only コマンド（prompt を stdin で渡す） |
| `fake` | テスト/CI 用の固定出力（ネットワーク不要） |

詳細は [docs/backends.md](docs/backends.md)。

## 検証結果

**Python 3.12.3 / Linux 6.18 (WSL2) / 2026-06-30** で取得。

### テストスイート — 21件 green

```text
tests/test_artifacts.py  2   （成果物の命名, markdown + json writer）
tests/test_cli.py        3   （logs/diff/files を fake backend で）
tests/test_collect.py    7   （git/file/dir collector, サイズ上限, binary + 秘密 skip）
tests/test_config.py     4   （既定値, TOML 上書き, merge）
tests/test_findings.py   5   （JSON 抽出, 行検証 valid/invalid/範囲外）
                        ---
                         21   passed in 0.18s
```

### 振る舞いの確認（エンドツーエンド・fake backend）

| 振る舞い | コマンド | 観測結果 |
|---|---|---|
| ログ triage（主用途） | `logs examples/sample-results --backend fake` | `.review/…-logs….md` + `.json` を生成 |
| **行検証** | fake が `results/latest/stderr.txt:42` を引用 | 収集元は `examples/sample-results/stderr.txt` → `file=null line=null line_verified=false` に正規化 |
| dry-run（AI 非呼出） | `logs … --dry-run` | 収集 bundle をそのまま表示、何も呼ばない |
| **秘密ガード** | `files .env --dry-run` | `skipped .env: sensitive`（含めるには `--allow-sensitive`） |
| バックエンド選択 | `--backend bogus` | `invalid choice …（llm, codex, custom, fake）`、`exit=2` |

代表的な出力:

```console
$ review-artifact logs examples/sample-results --backend fake
wrote .review/20260630-235029-logs-examples-sample-results.md
wrote .review/20260630-235029-logs-examples-sample-results.json
# findings[0].file = null, line = null, line_verified = false
#   （fake reviewer は results/latest/stderr.txt:42 を引用したが、それは未収集）

$ review-artifact files .env --dry-run
--- COLLECTION NOTES ---
skipped .env: sensitive
```

CI は同じスイートを Python 3.12 + fake バックエンドで実行します(API 呼び出しなし)。

## セキュリティ

- 収集したファイル内容を、設定したバックエンドに送信します。
- 秘密らしきファイル(`.env`, `*.pem`, `*token*` 等)は既定でスキップ。
- `--allow-sensitive` は意図的なときだけ使用。
- 秘密ガードは補助であり完全な保証ではありません — 共有前に確認を。
- 詳細は [docs/SECURITY.md](docs/SECURITY.md)。

## ドキュメント

- [docs/configuration.md](docs/configuration.md) — `.review-artifact.toml`
- [docs/backends.md](docs/backends.md) — llm / codex / custom / fake
- [docs/prompts.md](docs/prompts.md) — prompt preset
- [docs/SECURITY.md](docs/SECURITY.md) — 秘密情報の扱い

例: [examples/sample-results](examples/sample-results)(fake バックエンドのデモ)、
[examples/fugaku-results.toml](examples/fugaku-results.toml)(HPC 設定例)。

## runledger との組み合わせ

[runledger](https://github.com/K092203/runledger) は review-artifact が triage する
run snapshot を生成します:

```bash
runledger run -- ./solver < input.txt
review-artifact logs runs/latest      # snapshot を read-only の AI で triage
```

## 既知の制約

- **実 LLM バックエンド(`llm`, `codex`)は手動検証のみ。** CI と自動テストは `fake`
  バックエンドを使い、ネットワーク/API 呼び出しを行いません。
- **read-only の強度はバックエンドの sandbox に依存。** CLI 自体は読むだけですが、
  バックエンドが独自に動作しないことまでは保証できません。
- **行検証と JSON findings は best-effort。** reviewer の JSON を parse できない場合は
  `raw_output` を保持し `findings: []` とします。

## 非目標（v0.1）

自動修正 / 自動 commit、GitHub PR コメント bot、web UI / TUI、provider の完全抽象化、
セキュリティ監査ツール化。

## ライセンス

MIT — [LICENSE](LICENSE) を参照。
