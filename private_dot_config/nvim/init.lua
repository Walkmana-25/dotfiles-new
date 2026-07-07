require("common.config")
require("common.keymap")

-- load Vscode Settings
if vim.g.vscode == 1 then
  require("vsconfig.common")

  require("vsconfig.lazy")
  require("vsconfig.vscode")
else
  -- load nvim settings
  --
  -- スワップファイルの保存場所を設定
  -- `stdpath('cache')` を使ってホーム展開の問題を避ける
  local cache_dir = vim.fn.stdpath("cache")
  local swap_path = cache_dir .. "/swap"

  -- ディレクトリが存在しない場合に作成する
  if vim.fn.isdirectory(swap_path) == 0 then
    vim.fn.mkdir(swap_path, "p")
  end

  -- 'directory'オプションに設定（末尾に // を付けて一意のファイル名生成を有効にする）
  vim.opt.directory = swap_path .. "//"
  -- require("nvim-config.common")
  -- require("nvim-config.nvim")
  -- require("nvim-config.lazy")

  -- Load LazyVim
  require("config.lazy")
end
