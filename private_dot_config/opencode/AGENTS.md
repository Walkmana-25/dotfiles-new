# context-mode — MANDATORY routing rules

context-mode tools (`ctx_*`) are available to every agent. These rules protect the context window from flooding — one unrouted command can dump 56 KB into context. Follow them in every task.

## Think in Code — MANDATORY

To analyze / count / filter / compare / search / parse / transform data: **write code** via `ctx_execute(language, code)` and `console.log()` only the answer. Do NOT read raw data into context. PROGRAM the analysis — do not COMPUTE it by reading raw bytes. Pure JavaScript works with Node.js built-ins (`fs`, `path`, `child_process`). Use `try/catch`, handle `null`/`undefined`. One script replaces ten tool calls.

## BLOCKED — do NOT attempt

### curl / wget — BLOCKED
Shell `curl` / `wget` are intercepted and blocked. Do NOT retry.
Use: `ctx_fetch_and_index(url, source)` or `ctx_execute(language: "javascript", code: "const r = await fetch(...)" )`.

### Inline HTTP — BLOCKED
`fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, `http.request(` are intercepted. Do NOT retry.
Use: `ctx_execute(language, code)` — only stdout enters context.

### Direct web fetching (non-MCP) — BLOCKED
`curl`, `wget`, inline `fetch()`/`requests` are blocked. Do NOT use them.
MCP tools (`mcp__mcps__*`) are NOT blocked — use them for web search/scraping as described below.
Fallback: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)`.

## REDIRECTED — use sandbox

### Shell (>20 lines of output)
Use shell ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`.
Otherwise: `ctx_batch_execute(commands, queries)` or `ctx_execute(language: "shell", code: "...")`.

### File reading (for analysis)
Reading to **edit** → reading the file is correct (Edit needs the exact bytes).
Reading to **analyze / explore / summarize** → `ctx_execute_file(path, language, code)`.

### grep / search (large results)
Use `ctx_execute(language: "shell", code: "grep ..." )` inside the sandbox.

## Tool selection hierarchy

0. **MEMORY**: `ctx_search(sort: "timeline")` — after resume or compaction, check prior context before asking the user.
1. **GATHER**: `ctx_batch_execute(commands, queries)` — runs all commands in parallel, auto-indexes each, and returns matching sections. ONE call replaces 30+. Each command is `{label: "header", command: "..."}`.
2. **FOLLOW-UP**: `ctx_search(queries: ["q1", "q2", ...])` — batch all questions into one array, ONE call (default relevance mode).
3. **PROCESSING**: `ctx_execute(language, code)` | `ctx_execute_file(path, language, code)` — runs in a sandbox, only stdout enters context.
4. **WEB SEARCH**: `mcp__mcps__searxng_web_search` — first choice for web searches. Privacy-focused metasearch.
5. **WEB SCRAPE**: `mcp__mcps__firecrawl_scrape` — scrape web pages (handles JS rendering). Use instead of `ctx_fetch_and_index` for web pages.
6. **DEEPWIKI**: `mcp__mcps__ask_question` / `mcp__mcps__read_wiki_structure` / `mcp__mcps__read_wiki_contents` — query GitHub repo documentation and code structure via DeepWiki.
7. **WEB FALLBACK**: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` — use only when MCP tools are unavailable or unsuitable (e.g., local files, non-HTTP URLs).
8. **INDEX**: `ctx_index(content, source)` — store in FTS5 for later search.

## Parallel I/O batches

For multi-URL fetches or multi-command batches, **always** pass `concurrency: N` (1-8):
- `ctx_batch_execute(commands: [3+ network commands], concurrency: 5)` — gh, dig, docker inspect, multi-region cloud queries.
- `ctx_fetch_and_index(requests: [{url, source}, ...], concurrency: 5)` — multi-URL batch fetch.

**Use concurrency 4-8** for I/O-bound work (network calls, API queries). **Keep concurrency 1** for CPU-bound work (npm test, build, lint) or commands that share state (ports, lock files, same-repo writes).

## Summary discipline

Return only the answer, never raw tool output. Prefer one `ctx_batch_execute` call over many sequential reads. Keep responses concise — context is a shared, finite resource.

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
