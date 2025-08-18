local Job = require("plenary.job")

-- 创建一个命名空间，用于管理这个插件的所有 extmark
local codebase_ns = vim.api.nvim_create_namespace("codebase_panel_ns")
-- print("Namespace created with ID:", codebase_ns)
local codebase_panel_buf = nil
local codebase_config = nil

---@param virt_lines 虚拟行内容
---@param line number 行号(0-based index)
local function set_extmarks(virt_lines, line)
	vim.api.nvim_buf_set_extmark(codebase_panel_buf, codebase_ns, line, 0, {
		virt_lines = virt_lines,
		virt_lines_leftcol = false,
		virt_lines_above = true,
		virt_lines_overflow = "scroll",
		right_gravity = false,
	})
end

local function commit_function()
	assert(codebase_panel_buf, "Codebase panel buffer not found")
	local extmarks = vim.api.nvim_buf_get_extmarks(codebase_panel_buf, codebase_ns, 0, -1, {})
	-- print("Codebase namespace:", codebase_ns)

	local database_name = vim.api.nvim_buf_get_lines(codebase_panel_buf, extmarks[2][2], extmarks[3][2], false)
	-- concatenate the lines into a single string, remove \n and space at the beginning and end
	database_name = table.concat(database_name, "\n")
	database_name = database_name:gsub("^%s*(.-)%s*$", "%1") -- 去除首尾空格

	local user_query_text = vim.api.nvim_buf_get_lines(codebase_panel_buf, extmarks[3][2], extmarks[4][2], false)
	user_query_text = table.concat(user_query_text, "\n")

	local sql = vim.api.nvim_buf_get_lines(codebase_panel_buf, extmarks[4][2], extmarks[5][2], false)
	sql = table.concat(sql, "\n")

	-- clear the line below "Results"
	vim.api.nvim_buf_set_lines(codebase_panel_buf, extmarks[5][2], -1, false, { "" })
	-- run command
	local command = "codebase"
	local args = { "search", "--dbname", database_name, "--query_text", user_query_text, "--sql", sql }
	Job:new({
		command = command,
		args = args,
		cwd = "~",

		-- 回调函数，处理标准输出
		on_stdout = function(self, lines)
			-- lines 是一个 Lua 表，包含所有输出行
			if codebase_panel_buf == nil then
				return
			end
			print("on_stdout", lines)
			vim.schedule_wrap(function()
				vim.api.nvim_buf_set_lines(codebase_panel_buf, -1, -1, false, { lines })
			end)()
		end,

		-- 回调函数，处理标准错误
		on_stderr = function(self, lines)
			if codebase_panel_buf == nil or lines == nil then
				return
			end
			vim.schedule_wrap(function()
				vim.api.nvim_buf_set_lines(codebase_panel_buf, -1, -1, false, { "--- [stderr] " .. lines })
			end)()
		end,

		-- 回调函数，在命令完成后执行
		on_exit = function(self, code, signal)
			if codebase_panel_buf == nil then
				return
			end
			print("on_exit", code, signal)
			vim.schedule_wrap(function()
				vim.api.nvim_buf_set_lines(codebase_panel_buf, -1, -1, false, {
					"--- Command finished with exit code: " .. code .. " ---",
				})
			end)()
		end,
	}):start()
end

local function run_codebase_config_async()
	return vim.system({ "codebase", "config" }, { text = true }, function(obj)
		codebase_config = vim.json.decode(obj.stdout)
	end)
end

local M = {}

-- 定义一个函数来创建和设置 UI
function M.open_codebase_panel()
	if vim.fn.executable("codebase") == 0 then
		vim.notify("codebase command not found. Please install it first.", vim.log.levels.ERROR)
		return
	end

	local codebase_config_async_command = run_codebase_config_async()
	if codebase_panel_buf and vim.api.nvim_buf_is_valid(codebase_panel_buf) then
		-- 如果缓冲区已经存在且有效，直接切换到该缓冲区
		vim.cmd("vsplit")
		vim.api.nvim_set_current_buf(codebase_panel_buf)
		return
	end

	-- create a buffer and configure it
	codebase_panel_buf = vim.api.nvim_create_buf(false, true)
	vim.api.nvim_set_option_value("buftype", "nofile", { buf = codebase_panel_buf }) -- 非文件缓冲区
	vim.api.nvim_set_option_value("swapfile", false, { buf = codebase_panel_buf }) -- 不创建 swapfile
	vim.api.nvim_set_option_value("filetype", "codebase_panel", { buf = codebase_panel_buf }) -- 设置文件类型为 codebase_panel
	vim.api.nvim_buf_set_name(codebase_panel_buf, "Codebase-Panel")

	codebase_config_async_command:wait()
	assert(codebase_config, "Codebase config not found.")
	-- 3. 在新缓冲区中写入初始内容
	local lines = {
		codebase_config["pgvector"]["dbname"], -- Database Name 所在行
		"",
		"", -- 数据库名称输入
		"", -- User Query Text 所在行
		"", -- 用户输入
	}
	local default_sql = codebase_config["pgvector"]["default_sql"]
	local sql_lines = vim.split(default_sql, "\n", { trimempty = true, plain = true })
	vim.list_extend(lines, sql_lines)
	vim.list_extend(lines, { "", "" }) -- Result所在行
	vim.api.nvim_buf_set_lines(codebase_panel_buf, 0, -1, false, lines)

	-- 4. 垂直分屏打开这个缓冲区
	vim.cmd("vsplit")
	vim.api.nvim_win_set_buf(0, codebase_panel_buf) -- 0表示当前窗口，将当前窗口的缓冲区设置为新创建的缓冲区
	vim.api.nvim_buf_set_option(codebase_panel_buf, "colorcolumn", "")

	-- 设置 extmark 的高亮组
	vim.api.nvim_set_hl(codebase_ns, "Title", { fg = "#f39c12" }) -- 自定义一个标题高亮组

	-- See: https://www.nerdfonts.com/
	local head_extmarks = {
		{
			{
				"Keymaps:  <C-S> -> submit",
				"Question",
			},
		},
		{
			{
				"          <leader>tb -> open schema in preview window",
				"Question",
			},
		},
		{
			{
				"          <leader>cf -> open codebase config in preview window",
				"Question",
			},
		},
		{ { "Snippets: all_file | basic", "Keyword" } },
		{ { "", "NonText" } },
	}
	set_extmarks(head_extmarks, 0)
	set_extmarks({ { { " Database Name", "Title" } } }, 0)
	set_extmarks({ { { "󰧮 User Query Text", "Title" } } }, 2)
	set_extmarks({ { { " SQL", "Title" } } }, 4)
	set_extmarks({ { { " Results", "Title" } } }, 13)

	--让第一个extmark可见，topfill等于第一个extmarks的行数
	vim.fn.winrestview({ topfill = #head_extmarks + 1 })

	vim.keymap.set(
		{ "n", "i" },
		"<C-S>",
		commit_function,
		{ buffer = codebase_panel_buf, noremap = true, silent = true, desc = "Submit Codebase Query" }
	)
	vim.keymap.set("n", "<leader>tb", function()
		local current_script_path = debug.getinfo(1, "S").source:sub(2)
		local create_sql_file = vim.fs.dirname(vim.fs.dirname(current_script_path)) .. "/create_tables.sql"
		vim.cmd("pedit " .. create_sql_file)
	end, { buffer = codebase_panel_buf, noremap = true, silent = true, desc = "Open Schema in Preview Window" })
	vim.keymap.set(
		"n",
		"<leader>cf",
		function()
			local codebase_config_async_command = run_codebase_config_async()
			-- create a temporary buffer to show the config
			local config_buffer = vim.api.nvim_create_buf(false, true)
			vim.api.nvim_set_option_value("buftype", "nofile", { buf = config_buffer }) -- 非文件缓冲区
			vim.api.nvim_set_option_value("swapfile", false, { buf = config_buffer })
			vim.api.nvim_set_option_value("filetype", "json", { buf = config_buffer })
			local result = codebase_config_async_command:wait()
			-- split the result into lines
			local result_stdout_array = vim.split(result.stdout, "\n", { trimemtpy = true, plain = true })
			-- write result to the buffer
			vim.api.nvim_buf_set_lines(config_buffer, 0, -1, false, result_stdout_array)
			vim.cmd("pbuffer" .. config_buffer)
		end,
		{ buffer = codebase_panel_buf, noremap = true, silent = true, desc = "Open Codebase Config in Preview Window" }
	)
end

return M
