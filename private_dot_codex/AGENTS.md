# Codex 運用ルール (global)

このファイルは Codex の全セッションに注入される運用ルールである。
コンテキスト保護は本ファイルの行動規範によって担保する
(Codex には opencode の tool_output 相当の設定がないため、出力抑制は規律で行う)。
global + project の AGENTS.md 合計で 32KiB 制限 (project_doc_max_bytes) の
対象になるため、本ファイルは簡潔に保つこと。

## Plan First, Ask First (最重要)

- 何かを変更する前に、必ず実行計画を日本語のテキストとして提示し、
  ユーザーの承認を取る。「明らかに小さい」「自明」は例外にならない。
  承認を得るまで実装・編集に入らない。
- git の状態変更操作 (add / commit / push / pull / fetch / stash / checkout /
  restore / switch / branch / tag / merge / rebase 等) は rules の prompt による
  ユーザー承認を得た上で、必ず自分自身で実行する。サブエージェントに委譲しない。
- 不明点 (API 仕様・ライブラリの使い方・設定の shape・エラーの意味) は推測せず、
  tech_researcher サブエージェントに調査を委譲してから計画する。

## サブエージェント (~/.codex/agents/*.toml)

| agent | 用途 | sandbox |
|---|---|---|
| explorer | コードベース探索・証拠 (ファイル/行) 付きの事実収集 | read-only |
| coder | 指示に基づく実装 (最小変更・規約遵守) | workspace-write |
| reviewer | コード+テストのレビュー (severity / verdict 報告) | read-only |
| tech_researcher | 技術調査 (公式 docs 一次情報・出典 URL 付き) | read-only |

- 自明な軽作業 (タイポ修正、1-2 行の修正、簡単な質問、git status 確認) は
  委譲せず自分で行う。
- 委譲時は Objective / Output format / Tool & context guidance / Task boundaries
  の 4 点を必ず含める。欠けるとサブエージェントが暴走する。
- 読み取り系サブエージェントは read-only sandbox で動くが、`find -exec` や
  リダイレクト等の書き込みベクタは残る。破壊的な操作は避けること。

## Output discipline (出力抑制)

- コマンド出力が大きいと予想される場合は `| head -50` / `| wc -l` / `grep` で
  必要部分のみ取得する。
- 生のダンプ (ファイル全体・長いログ・JSON 全体) を応答に貼らない。要約して報告する。
- サブエージェントは必ず下記の Structured Return 形式で返す。

## Structured Return (MANDATORY for all subagents)

### Standard format

```
summary: <結論・成果を数行（最大5-10行）で>
key_findings:
- <要点3-5個を箇条書き>
artifact_path: <出力が大きい（目安: 2KB超）場合のみ詳細をファイルに書き出しそのパス。小さい場合は省略可>
```

### Exception
本当に短い一問一答（数行で終わるもの）の場合は、構造化フォーマットを省略して直接返してよい。

## Web / MCP hierarchy (優先順位)

Web 検索・スクレイピングは **mcps MCP server** のツールを使う
(shell の curl/wget は rules で forbidden)。

1. **WEB SEARCH**: mcps の searxng_web_search — web 検索の第一選択。プライバシー重視メタ検索。
2. **WEB SCRAPE**: mcps の firecrawl_scrape — JS レンダリング対応のスクレイピング。
3. **DEEPWIKI**: mcps の ask_question / read_wiki_structure / read_wiki_contents —
   GitHub リポジトリのドキュメント・コード構造への質問。

(注: mcps MCP server は tech_researcher が使い、他のサブエージェントは
tech_researcher に委譲する。explorer / coder / reviewer は web アクセスせず
ローカルの調査・実装に徹する。)
