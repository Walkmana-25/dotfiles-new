# AGENTS.md

## Codex model catalog の更新方法

- 更新対象は手編集しない。`scripts/gen-codex-model-catalog.py` で chezmoi ソースを再生成する。

```sh
python3 scripts/gen-codex-model-catalog.py
chezmoi diff ~ | grep -vE "Bearer|experimental_bearer"   # secret を除外して差分確認
chezmoi apply
```

- 生成後に codex (CLI / ChatGPT デスクトップアプリ) を再起動する。`models.json` は起動時読み込みでホットリロードされない。
- 前提・詳細・トラブルシュートは `README.md` の「Codex model catalog の更新」と `docs/litellm-codex-setup.md` を参照。
