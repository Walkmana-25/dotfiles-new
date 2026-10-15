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

## 1Password Service Account Token (fish)

fish 起動時に `load_env_files` が `~/.config/.env/*.env` を読み込みます。
1Password CLI の Service Account Token は、chezmoi/Git 管理外の
`~/.config/.env/1password.env` に保存してください。

```sh
umask 077
mkdir -p "$HOME/.config/.env"
chmod 700 "$HOME/.config/.env"
${EDITOR:-vi} "$HOME/.config/.env/1password.env"
chmod 600 "$HOME/.config/.env/1password.env"
```

ファイルには次の形式で1行だけ記載します。引用符や `export` は付けません。

```dotenv
OP_SERVICE_ACCOUNT_TOKEN=<1Password Service Account Token>
```

- このファイルやトークンを dotfiles、chezmoi のテンプレート、Git に追加しないでください。
- 読み込まれた環境変数は fish と、そこから起動する子プロセスに継承されます。fish の外から起動したプロセスには渡りません。
- ファイルがない場合、`OP_SERVICE_ACCOUNT_TOKEN` は設定されず、chezmoi は既存の account mode を使用します。
- トークンの値を端末やログに出力しないでください。漏えいした場合は 1Password で失効・再発行してください。
- 認証確認には `op user get --me` を使えます。トークンそのものを表示する必要はありません。

詳細: [Use a service account with the 1Password CLI](https://developer.1password.com/docs/service-accounts/use-with-1password-cli/)

## setupについてのメモ

### Macのsudoについて
次のサイトを参考にすべし
[Qiita](https://qiita.com/kawaz/items/0593163c1c5538a34f6f)

### Vicineのプラグイン

- https://www.vicinae.com/extensions/shyassassin/vscode-recents
- https://www.raycast.com/mblode/google-search
