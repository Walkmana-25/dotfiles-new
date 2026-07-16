# dotfiles-new

## Setup

```sh
chezmoi apply
```
または:
```sh
git config core.hooksPath .githooks
```
もしくは:

```sh
make setup
```

## Credential Scan

commit時に [gitleaks](https://github.com/gitleaks/gitleaks) がステージングされた差分を自動スキャンし、APIキーやパスワード等のcredentialを検出します。

- 検出された場合は **commitがブロック** されます
- 1Passwordテンプレート (`{{ onepasswordRead "op://..." }}`) は偽陽性除外済みです
- 誤検出の場合は `.gitleaks.toml` の allowlist を編集してください

## Macのsudoについて
次のサイトを参考にすべし
[Qiita](https://qiita.com/kawaz/items/0593163c1c5538a34f6f)
