vim.treesitter.language.register("sql", "codebase_panel")

-- 注册用户命令
vim.api.nvim_create_user_command("Codebase", require("codebase-semantic-search").open_codebase_panel, { nargs = 0, desc = "Opens the Codebase panel." })
