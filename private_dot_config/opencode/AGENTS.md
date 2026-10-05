# opencode 運用ルール (global)

このファイルは opencode の全セッション・全agentに注入される運用ルールである。
コンテキスト保護は設定 (`tool_output`: max_lines 2000 / max_bytes 20KB) と、
以下の行動規範によって担保する (context-mode プラグインは撤去済みのため ctx_* ツールは存在しない)。

## Output discipline (出力抑制)

- コマンド出力が大きいと予想される場合は `| head -50` / `| wc -l` / `grep` で必要部分のみ取得する。
  複合コマンド (`&&` / `|` / `;` / `$(...)`) は分解され、全要素が許可対象である必要がある点に注意。
- 生のダンプ (ファイル全体・長いログ・JSON全体) を応答に貼らない。要約して報告する。
- サブagentは必ず下記の Structured Return 形式で返す。

## Shell permissions

- デフォルトは **ask**。許可リスト外のコマンドはユーザーに確認ダイアログが出る。
- 許可リスト内のコマンドは無確認で実行できる。可能な限り許可リスト内で目的を達成すること。
- 複合コマンドは各要素がすべて許可されている必要がある (1つでも ask/deny なら全体がブロックされる)。
- `bash -c` / `sh -c` / `eval` / `sudo` / `su` / `curl` / `wget` / `ssh` / `scp` / `sftp` は明示 deny。
  スクリプト実行やネットワーク取得が必要な場合はユーザーに依頼すること。
- 権限ルールは後勝ち (last match wins): 各agentの permissions 配列は
  catch-all ask → allow群 → deny群 の順に定義されている。詳細は各 `agents/*.md` の frontmatter。
- **限界の認識**: glob権限は完全なセキュリティ境界ではない。
  `find -exec` / `awk` のリダイレクト / `sort -o` / `cat x > file` 等の書き込みベクタや、
  リダイレクト込みで1文としてマッチされる性質上、読み取り系agent (explorer / tech-researcher / reviewer) の
  「read-only」は editツール拒否 + 行動規範による保証である。破壊的操作は避けること。

## Web / MCP hierarchy (優先順位)

Web検索・スクレイピングは MCP ツール (`mcp__mcps__*`) を使う (shell の curl/wget は deny)。

1. **WEB SEARCH**: `mcp__mcps__searxng_web_search` — first choice for web searches. Privacy-focused metasearch.
2. **WEB SCRAPE**: `mcp__mcps__firecrawl_scrape` — scrape web pages (handles JS rendering).
3. **DEEPWIKI**: `mcp__mcps__ask_question` / `mcp__mcps__read_wiki_structure` / `mcp__mcps__read_wiki_contents` — query GitHub repo documentation and code structure via DeepWiki.

(注: `mcp__mcps__*` は tech-researcher のみ allow。他のagentは delegate to @tech-researcher。)

## Structured Return (MANDATORY for all subagents)

All subagents MUST use structured return format. This prevents long outputs from flooding the orchestrator's context.

### Standard format
```
summary: <結論・成果を数行（最大5-10行）で>
key_findings: <要点3-5個（箇条書き）>
artifact_path: <出力が大きい（目安: 2KB超、または詳細な調査/レビュー/実装結果）場合のみ、詳細をファイルに書き出しそのパス。小さい場合は省略可>
```

### Exception
本当に短い一問一答（数行で終わるもの）の場合は、構造化フォーマットを省略して直接返してよい。
