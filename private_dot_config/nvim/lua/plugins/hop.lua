return {
    -- like easymotion plugin
    -- leader leader w
    'smoka7/hop.nvim',
    version = "*",
    opts = {
        keys = 'etovxqpdygfblzhckisuran'
    }, 
    keys = {
      {"<leader><leader>w",  "<cmd>HopWord<CR>",  mode="n",  desc  = "Hop Word"},
      {"<leader><leader>l",  "<cmd>HopLine<CR>",  mode="n",  desc  = "Hop Line"},
      {"<leader><leader>c",  "<cmd>HopAnywhereCurrentLine<CR>", mode="n",  desc  = "Hop Anywhere Current Line"},
      {"<leader><leader>b",  "<cmd>HopBack<CR>", mode="n", desc="Hop Word Back"}
    },
    config = function(_, opts)
        require('hop').setup(opts)
        
        local hop = require('hop')
        local hint = require('hop.hint')

        vim.api.nvim_create_user_command('HopBack', function()
          hop.hint_words({ hint_position = hint.HintPosition.END, hint_offset = 1 })
        end, {desc = "Hop Word Back"})
    end,
}