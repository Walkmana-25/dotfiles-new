-- common settings here

-- 文字エンコーディング設定
vim.opt.encoding = "utf-8"
vim.opt.fileencoding = "utf-8"
vim.opt.fileencodings = "utf-8,iso-2022-jp,euc-jp,sjis"

-- クリップボード設定（macOSでLANGを強制する）
if vim.fn.has("mac") == 1 then
  vim.g.clipboard = {
    name = "macOS-clipboard",
    copy = {
      ["+"] = "env LANG=ja_JP.UTF-8 pbcopy",
      ["*"] = "env LANG=ja_JP.UTF-8 pbcopy",
    },
    paste = {
      ["+"] = "env LANG=ja_JP.UTF-8 pbpaste",
      ["*"] = "env LANG=ja_JP.UTF-8 pbpaste",
    },
    cache_enabled = 0,
  }
end

-- if not vscode, clipboard unnamedplus
vim.opt.clipboard = "unnamedplus"

-- Linux System Setting
if vim.fn.has("linux") == 1 then
    -- Deactivate IME when leaving insert mode
        vim.api.nvim_create_autocmd("InsertLeave", {
        pattern = "*",
        command = "call system('fcitx5-remote -c')",
    })
end
