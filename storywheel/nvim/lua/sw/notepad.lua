-- Notepad mode (the default): the Writer behaves like an ordinary text editor.
--
--   * you are always typing: Escape does not leave Insert mode
--   * the mouse selects like in any app, Shift+arrows select, typing replaces the selection (Neovim's Select mode)
--   * Ctrl+C / X / V use the system clipboard, Ctrl+Z / Y undo and redo, Ctrl+S saves, Ctrl+A selects all,
--     Ctrl+F finds (Ctrl+G next, Alt+G previous), Ctrl+Q goes back to the Builder
--   * right-click opens a menu; F12 (or Alt+M) opens a menu of Writer actions
--
-- A setting (notepad_mode = false in settings.toml, or the Writer menu) turns Vim behavior back on.
local util = require("sw.util")
local story = require("sw.story")
local M = {}

M.enabled = false
M.find_text = nil

function M.wanted()
  return story.setting("notepad_mode", true) ~= false
end

-- --- the clipboard ----------------------------------------------------------------------------------------

-- Neovim finds xclip / wl-copy / pbcopy itself. If there is none, copy and paste still work inside the Writer
-- through a clipboard of its own, and we say so once.
function M.ensure_clipboard()
  local forced = os.getenv("STORYWHEEL_INTERNAL_CLIPBOARD") == "1"       -- (tests, and anyone who wants it)
  if not forced and (vim.g.clipboard ~= nil or vim.fn.has("clipboard") == 1 and vim.fn.exists("*provider#clipboard#Executable") == 1
      and vim.fn["provider#clipboard#Executable"]() ~= "") then
    M.clipboard_kind = "system"
    return
  end
  local store = { ["+"] = { { "" }, "v" }, ["*"] = { { "" }, "v" } }
  vim.g.clipboard = {
    name = "storywheel",
    copy = { ["+"] = function(lines, regtype) store["+"] = { lines, regtype } end,
             ["*"] = function(lines, regtype) store["*"] = { lines, regtype } end },
    paste = { ["+"] = function() return store["+"] end, ["*"] = function() return store["*"] end },
  }
  M.clipboard_kind = "internal"
  M.clipboard_note = (not forced) and "No clipboard tool found (xclip, wl-copy, xsel...): copy and paste work inside the Writer only." or nil
end

local function put_register(text, linewise)
  local lines = vim.split(text, "\n", { plain = true })
  pcall(vim.fn.setreg, "+", lines, linewise and "V" or "v")
  pcall(vim.fn.setreg, '"', lines, linewise and "V" or "v")
end

local function get_register()
  local ok, lines = pcall(vim.fn.getreg, "+", 1, true)
  if not ok or #lines == 0 or (#lines == 1 and lines[1] == "") then
    lines = vim.fn.getreg('"', 1, true)
  end
  return lines, (vim.fn.getregtype("+"):sub(1, 1) == "V")
end

-- --- selections -----------------------------------------------------------------------------------------------

function M.has_selection()
  local m = vim.fn.mode()
  return m == "s" or m == "S" or m == "v" or m == "V" or m == "\22" or m == "\19"
end

local function selection()
  return require("sw.prose").selection_bounds()
end

local function leave_selection()
  vim.cmd("normal! \27")
end

-- Back to typing. `now` does it at once (from a key you pressed); otherwise it waits a moment (from a mode change).
function M.insert(now)
  if now then
    if M.enabled and vim.fn.mode() ~= "i" then vim.cmd("startinsert") end
    return
  end
  vim.schedule(function()
    if M.enabled and vim.fn.mode() == "n" then vim.cmd("startinsert") end
  end)
end

function M.selected_text()
  if not M.has_selection() then return nil end
  local r1, c1, r2, c2, linewise = selection()
  local text = table.concat(vim.api.nvim_buf_get_text(0, r1, c1, r2, c2, {}), "\n")
  return text, linewise
end

-- Ctrl+C
function M.copy()
  local text, linewise = M.selected_text()
  if not text then
    vim.api.nvim_echo({ { "Nothing selected.", "Normal" } }, false, {})
    return false
  end
  put_register(text, linewise)
  return true
end

-- Ctrl+X
function M.cut()
  local text, linewise = M.selected_text()
  if not text then return false end
  local r1, c1, r2, c2 = selection()
  put_register(text, linewise)
  leave_selection()
  vim.api.nvim_buf_set_text(0, r1, c1, r2, c2, { "" })
  vim.api.nvim_win_set_cursor(0, { r1 + 1, c1 })
  M.insert(true)
  return true
end

-- Delete the selection (typing and paste do it for you; Backspace and Delete already do in Select mode).
function M.delete_selection()
  if not M.has_selection() then return end
  local r1, c1, r2, c2 = selection()
  leave_selection()
  vim.api.nvim_buf_set_text(0, r1, c1, r2, c2, { "" })
  vim.api.nvim_win_set_cursor(0, { r1 + 1, c1 })
end

-- Ctrl+V: paste, replacing the selection if there is one.
function M.paste()
  local lines, linewise = get_register()
  if #lines == 0 then return false end
  if M.has_selection() then M.delete_selection() end
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  if linewise then
    -- a whole line pasted: it becomes a paragraph of its own
    table.insert(lines, #lines + 1, "")
    vim.api.nvim_buf_set_text(0, row - 1, col, row - 1, col, vim.list_extend({ "" }, lines))
  else
    vim.api.nvim_buf_set_text(0, row - 1, col, row - 1, col, lines)
    local last = lines[#lines]
    if #lines == 1 then vim.api.nvim_win_set_cursor(0, { row, col + #last })
    else vim.api.nvim_win_set_cursor(0, { row + #lines - 1, #last }) end
  end
  M.insert(true)
  return true
end

-- Ctrl+A
-- Select mode with an EXCLUSIVE selection cannot take in the very last character of the buffer (Vim leaves it out when
-- the selection is replaced), so selecting everything uses an inclusive selection until the selection ends.
function M.select_all()
  vim.cmd("stopinsert")
  vim.api.nvim_win_set_cursor(0, { 1, 0 })
  vim.o.selection = "inclusive"
  vim.cmd("normal! vG$")
  vim.cmd("normal! \7")
  vim.api.nvim_create_autocmd("ModeChanged", {
    once = true, pattern = "s:*", callback = function() vim.o.selection = "exclusive" end,
  })
end

-- Ctrl+S
function M.save()
  vim.cmd("silent! update")
  vim.api.nvim_echo({ { "Saved.", "Normal" } }, false, {})
  require("sw.stats").save()
end

function M.undo()
  vim.cmd("silent! undo")
end

function M.redo()
  vim.cmd("silent! redo")
end

-- Ctrl+F, Ctrl+G, Alt+G
function M.find(text)
  local function go(t)
    if not t or t == "" then return end
    M.find_text = t
    vim.fn.setreg("/", "\\V" .. vim.fn.escape(t, "\\"))
    vim.o.hlsearch = true
    M.find_next(1)
  end
  if text then return go(text) end
  vim.ui.input({ prompt = "Find: ", default = M.find_text or "" }, go)
end

function M.find_next(direction)
  if not M.find_text then return M.find() end
  local flags = direction > 0 and "w" or "bw"
  local found = vim.fn.search(vim.fn.getreg("/"), flags)
  if found == 0 then
    vim.api.nvim_echo({ { "Not found: " .. M.find_text, "WarningMsg" } }, false, {})
  end
  return found ~= 0
end

-- Undo in small steps: a new undo block at every space and every Enter, since we never leave Insert mode.
function M.undo_break_on(char)
  return "<C-g>u" .. char
end

-- --- Escape ----------------------------------------------------------------------------------------------------

function M.escape()
  if vim.fn.pumvisible() == 1 then
    return vim.api.nvim_replace_termcodes("<C-e>", true, false, true)
  end
  if vim.v.hlsearch == 1 then
    vim.cmd("nohlsearch")
  end
  return ""
end

-- --- keys, menus ----------------------------------------------------------------------------------------------------

function M.map_buffer(buf)
  if not M.enabled then return end
  local function map(mode, lhs, rhs, opts)
    vim.keymap.set(mode, lhs, rhs, vim.tbl_extend("force", { buffer = buf, silent = true }, opts or {}))
  end
  map("i", "<Esc>", function() return M.escape() end, { expr = true, replace_keycodes = false })
  -- clipboard, undo, save, select all, find
  map({ "i", "s", "x", "n" }, "<C-c>", function() M.copy() end)
  map({ "i", "s", "x", "n" }, "<C-x>", function() M.cut() end)
  map({ "i", "s", "x", "n" }, "<C-v>", function() M.paste() end)
  map({ "i", "s", "x", "n" }, "<C-z>", function() M.undo() end)
  map({ "i", "s", "x", "n" }, "<C-y>", function() M.redo() end)
  map({ "i", "s", "x", "n" }, "<C-s>", function() M.save() end)
  map({ "i", "s", "x", "n" }, "<C-a>", function() M.select_all() end)
  map({ "i", "s", "x", "n" }, "<C-f>", function() M.find() end)
  map({ "i", "s", "x", "n" }, "<C-g>", function() M.find_next(1) end)
  map({ "i", "s", "x", "n" }, "<A-g>", function() M.find_next(-1) end)
  map({ "i", "s", "x", "n" }, "<C-q>", function() require("sw").leave("builder") end)
  map({ "i", "s", "x", "n" }, "<F12>", function() require("sw.menu").open() end)
  map({ "i", "s", "x", "n" }, "<A-m>", function() require("sw.menu").open() end)
  -- smaller undo steps: a break at every space
  map("i", "<Space>", "<C-g>u<Space>")
  -- the shortcuts that normal mode's leader keys give a Vim user
  map({ "i", "s", "x", "n" }, "<F9>", function() require("sw.sidebar").toggle() end)
  map({ "i", "s", "x", "n" }, "<F8>", function() require("sw.world").peek() end)
end

-- The right-click menu.
function M.popup_menu()
  pcall(vim.cmd, "aunmenu PopUp")           -- (removing Neovim's own items leaves "E31: No such mapping" in v:errmsg; harmless)
  vim.v.errmsg = ""
  -- Neovim 0.11 installs a MenuPopup handler that enables/disables its own items ("Go to definition"...) and raises
  -- E329 once they are gone. Drop every MenuPopup autocmd that is not ours (the group name varies by version).
  for _, a in ipairs(vim.api.nvim_get_autocmds({ event = "MenuPopup" })) do
    if a.group then pcall(vim.api.nvim_del_autocmd, a.id) end
  end
  pcall(vim.api.nvim_del_augroup_by_name, "nvim.popupmenu")
  local items = {
    { "Cut", "cut" }, { "Copy", "copy" }, { "Paste", "paste" }, { "Select All", "select_all" }, { "-" },
    { "Italic", "italic" }, { "Bold", "bold" }, { "Scene Break", "scene_break" }, { "-" },
    { "Find", "find" }, { "Writer Menu", "menu" },
  }
  for i, it in ipairs(items) do
    if it[1] == "-" then
      vim.cmd(string.format("amenu 10.%d PopUp.-sep%d- :", 100 + i, i))
    else
      vim.cmd(string.format("anoremenu 10.%d PopUp.%s <Cmd>lua require('sw.notepad').run_menu_item('%s')<CR>",
        100 + i, it[1]:gsub(" ", "\\ "), it[2]))
    end
  end
  M.popup_items = items
end

function M.run_menu_item(name)
  local prose = require("sw.prose")
  local actions = {
    cut = M.cut, copy = M.copy, paste = M.paste, select_all = M.select_all, find = function() M.find() end,
    italic = function()
      if M.has_selection() then prose.wrap_visual("*") else prose.toggle_insert("*") end
    end,
    bold = function()
      if M.has_selection() then prose.wrap_visual("**") else prose.toggle_insert("**") end
    end,
    scene_break = function() prose.scene_break() end,
    menu = function() require("sw.menu").open() end,
  }
  if actions[name] then actions[name]() end
  M.insert(true)
end

function M.setup()
  M.enabled = M.wanted()
  if not M.enabled then return end
  M.ensure_clipboard()
  local o = vim.o
  o.selectmode = "mouse,key"
  o.keymodel = "startsel,stopsel"
  o.selection = "exclusive"
  o.mousemodel = "popup_setpos"
  o.virtualedit = "onemore"
  o.undolevels = 10000
  M.popup_menu()
  local group = vim.api.nvim_create_augroup("sw_notepad", { clear = true })
  -- never rest in Normal mode inside the writing window
  vim.api.nvim_create_autocmd("ModeChanged", {
    group = group, pattern = "*:n",
    callback = function()
      local layout = require("sw.layout")
      if M.enabled and layout.main and vim.api.nvim_get_current_win() == layout.main
          and vim.bo.filetype == "storywheel" and not M.paused then
        M.insert()
      end
    end,
  })
  if M.clipboard_note then util.notify(M.clipboard_note) end
end

-- Used by tests and by the menu to step out of notepad behavior for a moment.
function M.pause(on)
  M.paused = on
end

function M.start_typing()
  if M.enabled then vim.cmd("startinsert") end
end

return M
