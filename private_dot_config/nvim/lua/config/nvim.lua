-- nvim settings here
--
vim.opt.number = true -- show line number
vim.opt.showmode = false -- disable show mode
vim.opt.cursorline = true -- show hilight
vim.opt.cursorcolumn = true -- show hilight
vim.opt.hlsearch = true -- show hiliight in search text
vim.opt.shiftwidth = 2 -- set indent 2
vim.opt.timeoutlen = 500
-- vim.opt.directory = "$HOME/.cache/nvim/swap"

-- specific system
vim.keymap.set("n", "<leader>t", "<cmd>Neotree toggle<CR>",  { desc = "show tree"})
