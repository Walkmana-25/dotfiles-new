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

## Colima

- `~/.colima/_templates/default.yaml` と `~/.colima/default/colima.yaml` はchezmoiから一方向に適用する。
- `colima start --edit` などでColima設定を変更した後は、`chezmoi re-add ~/.colima/default/colima.yaml` でソースへ取り込む。
- `disk` は作成済みVMでは縮小できないため、既存VMの現在値以上にすること。
- CPUは8、メモリはchezmoiテンプレート評価時にホストメモリの1/4を自動計算する。
- VM作成後にzram swapをメモリの50%・zstd・`vm.swappiness=100`で構成する。Colimaを常時起動しない運用では、`run_onchange_` スクリプトは起動中のVMのみ再起動し、停止中は次回起動時に反映する。
- `vmType` は作成後変更できない。既存VMを `vz` に切り替える場合は、`disk` の値を維持したままVMを削除して再作成する。

## Credential Scan

commit時に [gitleaks](https://github.com/gitleaks/gitleaks) がステージングされた差分を自動スキャンし、APIキーやパスワード等のcredentialを検出します。

- 検出された場合は **commitがブロック** されます
- 1Passwordテンプレート (`{{ onepasswordRead "op://..." }}`) は偽陽性除外済みです
- 誤検出の場合は `.gitleaks.toml` の allowlist を編集してください

## setupについてのメモ

### Macのsudoについて
次のサイトを参考にすべし
[Qiita](https://qiita.com/kawaz/items/0593163c1c5538a34f6f)

### Vicineのプラグイン

- https://www.vicinae.com/extensions/shyassassin/vscode-recents
- https://www.raycast.com/mblode/google-search
