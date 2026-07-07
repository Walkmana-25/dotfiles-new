-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local map = vim.keymap.set

-- set ctrl + jkhl to leader to hjkl
map("n", "<Leader>j", "<C-j>", { desc = "Move to window below", remap = true })
map("n", "<Leader>k", "<C-k>", { desc = "Move to window up", remap = true })
map("n", "<Leader>h", "<C-h>", { desc = "Move to window Left", remap = true })
map("n", "<Leader>l", "<C-l>", { desc = "Move to window Right", remap = true })
