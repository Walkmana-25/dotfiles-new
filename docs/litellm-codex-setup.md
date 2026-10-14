# Codex への LiteLLM gateway 接続セットアップ (chezmoi 管理メモ)

Codex CLI / ChatGPT デスクトップアプリの接続先を litellm gateway (lapis-dev) に
入れ替えた手順と、運用・トラブルシュートのメモ。
(元々 skill として作成していた内容を docs に移動したもの)

## 管理対象の現構成

- `~/.codex/config.toml` — chezmoi modify テンプレート
  (`.chezmoitemplates/codex-personal` / `codex-personal-modify`) が生成
  - `model_provider = "litellm"` / `model = "zai/glm-5.3-flash"` / `model_reasoning_effort = "high"`
  - URL / credential は **chezmoi apply 時に** `onepasswordRead` で一度だけ解決し
    平文展開する (codex 起動時に 1Password CLI を実行しない)
  - `base_url = <1Password url>/v1`, `wire_api = "responses"`
  - `[mcp_servers.mcps]` = `<1Password url>/mcp` + `Authorization: Bearer <credential>`
    (server名 `mcps` は opencode 構成と整合のため維持)
- 1Password: vault `TOKEN` / item `litellm` / fields `credential` と `url`
  (url はベースURL・末尾スラッシュあり — テンプレート側で trim して `/v1` `/mcp` を付与)
- モデルカタログ: `private_dot_codex/models.json` ← 自動生成
  (`scripts/gen-codex-model-catalog.py`)。**手編集しない**

## モデルカタログの再生成 (gateway 側の登録が変わったとき)

1. `python3 scripts/gen-codex-model-catalog.py`
   - `/v1/models` + `/model/info` (GET のみ) を取得して `private_dot_codex/models.json` を再生成
   - 非テキスト系を除外 (tts / whisper / embedding / image / sora / realtime /
     moderation / computer-use / deep-research / テスト用 `t-*` など)
   - GLM 系 (裸名エイリアス含む) は ZAI 由来の属性を踏襲 (1M context / low-high-max)
   - 登録数は gateway 側の入れ替えで大きく変動する (実際に 193 → 132 → 7 が発生)
2. `chezmoi apply ~/.codex/models.json`

## トラブルシュート実績

- **unknown model**: 旧 slug (接頭辞なし `glm-5.3` 等) が旧スレッドに残っていた、
  または gateway から削除されたモデルが選ばれていた。
  gateway 登録名の確認は **GET のみ** (`/v1/models` / `/model/info`)。
  勝手に `POST /v1/responses` を大量に叩いて検査しない (quota 消費が大きい)
- **401 Authentication Error**: litellm virtual key のローテーション。
  `chezmoi apply` で再展開すれば直る (短時間で数回ローテする例あり)
- **TOML parse error (`Bearer "sk-..."` など)**: modify テンプレートの
  `Authorization = "Bearer %q"` という書き方の `%q` 二重引用符。
  正: `Authorization = %q` に `print "Bearer " $key` を渡す
- テンプレート regex が効かない: 句読点が全角 (`構成。`) だと
  ASCII `.` (`\.`) パターンではマッチしない

## 検証ワークフロー

1. `chezmoi diff ~ | grep -vE 'Bearer|experimental_bearer'` — 差分確認は
   secret 相当行を必ず除外して表示する (応答に生のキーを出さない)
2. `python3 -c "import tomllib; tomllib.load(open('/Users/yuuta/.codex/config.toml','rb'))"` — TOML 検証
3. codex 再起動: CLI は `Ctrl+C` → 起動し直し、ChatGPT デスクトップアプリは
   `⌘Q` で完全終了してから再起動 (config / models.json は起動時に読み込まれ、
   ホットリロードされない)

## 補足・スコープ

- `model` / `model_reasoning_effort` 行は apply 時に既定値へリセットされる設計
  (codex 内での /model 選択は永続しない)。変更するなら modify テンプレート調整
- opencode 側 (`mcps` = lapis-mcp) は本変更のスコープ外 (維持)。
  `op://TOKEN/lapis-mcp-1/*`・`zai-api-key` アイテムは削除しない
- mimo 系 (`opencode-go/mimo-*`, mode: chat) も `/v1/responses` 経由で動作することを
  gateway ブリッジ対応後に確認済み (streaming 200)
