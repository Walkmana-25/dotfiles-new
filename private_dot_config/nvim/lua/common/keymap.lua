
-- keyconfig
vim.g.mapleader = " "
vim.g.maplocalleader = " "


-- save leader + w
vim.api.nvim_set_keymap('n', '<leader>w', ':<C-u>w<CR>', {noremap = true})


-- easymotion keybind is plugins folder




--コンマの後ろに自動的にスペースを挿入
vim.api.nvim_set_keymap('i', ',', ',<Space>', {noremap = true})
