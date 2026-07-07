# dotfiles-new

## Setup

```sh
git config core.hooksPath .githooks
```
または:

```sh
make setup
```

## Credential Scan

commit時に [gitleaks](https://github.com/gitleaks/gitleaks) がステージングされた差分を自動スキャンし、APIキーやパスワード等のcredentialを検出します。

- 検出された場合は **commitがブロック** されます
- 1Passwordテンプレート (`{{ onepasswordRead "op://..." }}`) は偽陽性除外済みです
- 誤検出の場合は `.gitleaks.toml` の allowlist を編集してください
