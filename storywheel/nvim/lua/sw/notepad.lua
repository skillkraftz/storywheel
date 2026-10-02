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
-- Never in a window that is not the writing window, or in a buffer that can't be changed (a menu, the help, the sidebar):
-- Insert mode there would turn the next Enter into an error.
function M.can_type()
  local layout = require("sw.layout")
  return M.enabled and layout.main ~= nil and vim.api.nvim_win_is_valid(layout.main)
      and vim.api.nvim_get_current_win() == layout.main and vim.bo.modifiable
end

function M.insert(now)
  if now then
    if M.can_type() and vim.fn.mode() ~= "i" then vim.cmd("startinsert") end
    return
  end
  vim.schedule(function()
    if M.can_type() and vim.fn.mode() == "n" then vim.cmd("startinsert") end
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

-- Pasted text: one paragraph per line, flush left. Leading tabs and spaces are dropped (the indent is automatic), and so are
-- empty lines (they mean nothing).
function M.clean_pasted(lines)
  local out = {}
  for _, l in ipairs(lines) do
    local t = require("sw.typing").straighten(l:gsub("\r$", ""))        -- (curly quotes become straight)
    t = t:gsub("^[ \t]+", "")
    while t:sub(1, 2) == "\194\160" do t = t:sub(3):gsub("^[ \t]+", "") end         -- (a non-breaking space too)
    if t ~= "" or #lines == 1 then out[#out + 1] = t end
  end
  if #out == 0 then out = { "" } end
  return out
end

-- Join the selected lines into one paragraph (for text that was hard-wrapped, from an email say). Blank lines and scene breaks
-- inside the selection are dropped. Needs a selection: one line is one paragraph, so there is no "the paragraph" to guess.
function M.join_lines()
  local util = require("sw.util")
  if not M.has_selection() then
    vim.api.nvim_echo({ { "Select the lines to join first (Shift+Down, or drag with the mouse), then join.", "Normal" } }, true, {})
    return false
  end
  local a, _, b = selection()
  local r1, r2 = a + 1, b + 1
  leave_selection()
  local lines = vim.api.nvim_buf_get_lines(0, r1 - 1, r2, false)
  local parts = {}
  for _, l in ipairs(lines) do
    local t = vim.trim(l)
    if t ~= "" and util.marker_label(t) == nil then parts[#parts + 1] = t end
  end
  if #parts < 2 then
    vim.api.nvim_echo({ { "Nothing to join: that is one line already.", "Normal" } }, false, {})
    return false
  end
  vim.api.nvim_buf_set_lines(0, r1 - 1, r2, false, { table.concat(parts, " ") })
  vim.api.nvim_win_set_cursor(0, { r1, 0 })
  vim.api.nvim_echo({ { string.format("Joined %d lines into one paragraph.", #parts), "Normal" } }, true, {})
  M.insert(true)
  return true
end

-- Ctrl+V: paste, replacing the selection if there is one.
function M.paste()
  local lines, linewise = get_register()
  if #lines == 0 then return false end
  lines = M.clean_pasted(lines)
  if M.has_selection() then M.delete_selection() end
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  if linewise then
    -- whole lines pasted: each is a paragraph of its own, on its own line
    vim.api.nvim_buf_set_lines(0, row, row, false, lines)
    vim.api.nvim_win_set_cursor(0, { row + #lines, 0 })
  else
    vim.api.nvim_buf_set_text(0, row - 1, col, row - 1, col, lines)
    local last = lines[#lines]
    if #lines == 1 then vim.api.nvim_win_set_cursor(0, { row, col + #last })
    else vim.api.nvim_win_set_cursor(0, { row + #lines - 1, #last }) end
  end
  M.insert(true)
  return true
end

-- Home and End act on the line you SEE (a wrapped paragraph is several screen lines). Home at the start of a screen line goes
-- on to the start of the paragraph; End goes to the end of the screen line (after the last character on the last one).
function M.home()
  if M.has_selection() then leave_selection() end
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  vim.cmd("normal! g0")
  local r2, c2 = unpack(vim.api.nvim_win_get_cursor(0))
  if r2 == row and c2 == col then vim.api.nvim_win_set_cursor(0, { row, 0 }) end      -- already there: the paragraph's start
  M.insert(true)
end

function M.line_end()
  if M.has_selection() then leave_selection() end
  local row = vim.api.nvim_win_get_cursor(0)[1]
  local line = vim.api.nvim_get_current_line()
  vim.cmd("normal! g$")
  local r2, c2 = unpack(vim.api.nvim_win_get_cursor(0))
  if r2 == row and #line > 0 and (c2 >= #line or c2 + 1 + vim.str_utf_end(line, c2 + 1) >= #line) then
    vim.api.nvim_win_set_cursor(0, { row, #line })                                    -- the last screen line: after the last character
  end
  M.insert(true)
end

-- Shift+Home / Shift+End: select to the start / end of the visible line (the other end stays where it was).
function M.shift_line(which)
  vim.o.selection = "exclusive"
  local was_insert = vim.fn.mode() == "i"
  local anchor, cur
  if M.has_selection() then
    local a, c = vim.fn.getpos("v"), vim.fn.getpos(".")
    anchor, cur = { a[2], a[3] - 1 }, { c[2], c[3] - 1 }
    leave_selection()
  else
    cur = vim.api.nvim_win_get_cursor(0)
    anchor = cur
  end
  vim.api.nvim_win_set_cursor(0, cur)
  local line = vim.api.nvim_get_current_line()
  local target, inclusive = nil, false
  if which == "home" then
    vim.cmd("normal! g0")
    target = vim.api.nvim_win_get_cursor(0)
    if target[1] == cur[1] and target[2] == cur[2] then target = { cur[1], 0 } end
  else
    -- the last character of the visible line is part of the selection, so this one is inclusive (until the selection ends)
    vim.cmd("normal! g$")
    target = vim.api.nvim_win_get_cursor(0)
    if #line > 0 then target = { target[1], math.min(target[2], #line - 1 + vim.str_utf_start(line, #line)) } end    -- (the last character, not past it)
    inclusive = true
  end
  vim.cmd("stopinsert")
  if target[1] == anchor[1] and target[2] == anchor[2] and not inclusive then
    vim.api.nvim_win_set_cursor(0, target)
    M.insert(true)
    return
  end
  if inclusive and anchor[1] == target[1] and anchor[2] > target[2] then
    vim.api.nvim_win_set_cursor(0, anchor)
    M.insert(true)                                  -- already at or past the end: nothing to select
    return
  end
  if inclusive then vim.o.selection = "inclusive" end
  vim.api.nvim_win_set_cursor(0, anchor)
  vim.cmd("normal! v")
  -- (leaving Insert mode, which is still pending in here, moves the cursor one to the left: aim one further)
  local pending_leave = was_insert and target[2] > 0
  vim.api.nvim_win_set_cursor(0, { target[1], math.min(target[2] + (pending_leave and 1 or 0), #line) })
  vim.cmd("normal! \7")
  if inclusive then
    vim.api.nvim_create_autocmd("ModeChanged", { once = true, pattern = "s:*", callback = function() vim.o.selection = "exclusive" end })
  end
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

-- In notepad mode the Ctrl keys are an ordinary editor's, not Neovim's: Ctrl+U would delete a line, Ctrl+W a word, Ctrl+T indent,
-- Ctrl+D unindent, Ctrl+O/R/K/E/N/P/L/J ... all insert-mode commands nobody asked for. Every one that is not deliberately mapped
-- below does nothing. (Mappings made after this replace these; Ctrl+M is Enter, Ctrl+I is Tab, Ctrl+[ is Escape: left alone.)
local KEEP = { m = true, i = true }                         -- Enter and Tab are these keys
local FUNCTION_KEYS = {}
for n = 1, 12 do
  for _, prefix in ipairs({ "", "S-", "C-", "A-", "C-S-", "C-A-", "S-A-" }) do
    FUNCTION_KEYS[#FUNCTION_KEYS + 1] = string.format("<%sF%d>", prefix, n)
  end
end

function M.disable_keys(buf)
  local function nop(lhs)
    pcall(vim.keymap.set, { "i", "s" }, lhs, "<Nop>", { buffer = buf, silent = true })
  end
  for c = string.byte("a"), string.byte("z") do
    local ch = string.char(c)
    if not KEEP[ch] then nop("<C-" .. ch .. ">") end
  end
  for _, lhs in ipairs({ "<C-@>", "<C-]>", "<C-^>", "<C-_>", "<C-\\>", "<C-Space>" }) do nop(lhs) end
  -- a function key nobody mapped must not type its own name ("<F5>") into the story. F1-F5 are the modes (mapped globally).
  for _, lhs in ipairs(FUNCTION_KEYS) do
    if not lhs:match("^<F[1-5]>$") then nop(lhs) end
  end
end

function M.map_buffer(buf)
  if not M.enabled then return end
  local function map(mode, lhs, rhs, opts)
    vim.keymap.set(mode, lhs, rhs, vim.tbl_extend("force", { buffer = buf, silent = true }, opts or {}))
  end
  M.disable_keys(buf)
  -- Ctrl+Backspace (many terminals send it as Ctrl+H) deletes the previous word; Ctrl+Delete the next
  map("i", "<C-h>", "<C-w>")
  map("i", "<C-BS>", "<C-w>")
  map("i", "<C-Del>", "<C-o>dw")
  map("s", "<C-h>", function() M.delete_selection() M.insert(true) end)
  map("s", "<C-BS>", function() M.delete_selection() M.insert(true) end)
  -- <C-n>/<C-p> only walk a completion list
  map("i", "<C-n>", function() return vim.fn.pumvisible() == 1 and vim.api.nvim_replace_termcodes("<C-n>", true, false, true) or "" end, { expr = true, replace_keycodes = false })
  map("i", "<C-p>", function() return vim.fn.pumvisible() == 1 and vim.api.nvim_replace_termcodes("<C-p>", true, false, true) or "" end, { expr = true, replace_keycodes = false })  map("i", "<Esc>", function() return M.escape() end, { expr = true, replace_keycodes = false })
  -- clipboard, undo, save, select all, find
  map({ "i", "s", "x", "n" }, "<C-c>", function() M.copy() end)
  map({ "i", "s", "x", "n" }, "<C-x>", function() M.cut() end)
  map({ "i", "s", "x", "n" }, "<C-v>", function() M.paste() end)
  map({ "i", "s", "x", "n" }, "<C-z>", function() M.undo() end)
  map({ "i", "s", "x", "n" }, "<C-y>", function() M.redo() end)
  map({ "i", "s", "x", "n" }, "<C-s>", function() M.save() end)
  map({ "i", "s", "x", "n" }, "<C-a>", function() M.select_all() end)
  map({ "i", "s", "x" }, "<Home>", function() M.home() end)
  map({ "i", "s", "x" }, "<End>", function() M.line_end() end)
  map({ "i", "s", "x" }, "<S-Home>", function() M.shift_line("home") end)
  map({ "i", "s", "x" }, "<S-End>", function() M.shift_line("end") end)
  map({ "i", "s", "x", "n" }, "<C-f>", function() M.find() end)
  map({ "i", "s", "x", "n" }, "<C-g>", function() M.find_next(1) end)
  map({ "i", "s", "x", "n" }, story.setting("key_replace", "<C-r>"), function() require("sw.replace").open() end)
  map({ "i", "s", "x", "n" }, story.setting("key_lookup", "<F7>"), function() require("sw.lookup").word() end)
  map({ "i", "s", "x", "n" }, story.setting("key_lookup_word", "<F6>"), function() require("sw.lookup").ask() end)
  map({ "i", "s", "x", "n" }, "<A-g>", function() M.find_next(-1) end)
  map({ "i", "s", "x", "n" }, story.setting("key_builder", "<C-q>"), function() require("sw").leave("builder") end)
  map({ "i", "s", "x", "n" }, story.setting("key_menu", "<F12>"), function() require("sw.menu").open() end)
  map({ "i", "s", "x", "n" }, "<A-m>", function() require("sw.menu").open() end)
  map({ "i", "s", "x", "n" }, story.setting("key_quit", "<A-q>"), function() require("sw").quit() end)
  map({ "i", "s", "x" }, "<A-j>", function() M.join_lines() end)
  -- smaller undo steps: a break at every space
  map("i", "<Space>", "<C-g>u<Space>")
  -- the shortcuts that normal mode's leader keys give a Vim user
  map({ "i", "s", "x", "n" }, story.setting("key_sidebar", "<F9>"), function() require("sw.sidebar").toggle() end)
  map({ "i", "s", "x", "n" }, story.setting("key_peek", "<F8>"), function() require("sw.world").peek() end)
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
  -- { name, action, the key shown beside it: text, or { setting, default } for a key you can change }
  local items = {
    { "Undo", "undo", "Ctrl+Z" }, { "Redo", "redo", "Ctrl+Y" }, { "-" },
    { "Cut", "cut", "Ctrl+X" }, { "Copy", "copy", "Ctrl+C" }, { "Paste", "paste", "Ctrl+V" }, { "Select All", "select_all", "Ctrl+A" }, { "-" },
    { "Italic", "italic", { "key_italic", "<A-i>" } }, { "Bold", "bold", { "key_bold", "<A-b>" } },
    { "Scene Break", "scene_break", { "key_scene_break", "<A-s>" } }, { "-" },
    { "Find", "find", "Ctrl+F" }, { "Replace", "replace", { "key_replace", "<C-r>" } }, { "Add to Dictionary", "spell_add" },
    { "Look Up", "lookup", { "key_lookup", "<F7>" } }, { "Join Lines", "join", "Alt+J" }, { "Writer Menu", "menu", { "key_menu", "<F12>" } },
  }
  for i, it in ipairs(items) do
    if it[1] == "-" then
      vim.cmd(string.format("amenu 10.%d PopUp.-sep%d- :", 100 + i, i))
    else
      local hint = it[3]
      if type(hint) == "table" then hint = util.key_label(story.setting(hint[1], hint[2])) end
      vim.cmd(string.format("anoremenu 10.%d PopUp.%s<Tab>%s <Cmd>lua require('sw.notepad').run_menu_item('%s')<CR>",
        100 + i, (it[1]:gsub(" ", "\\ ")), (hint or ""):gsub(" ", "\\ "), it[2]))
    end
  end
  M.popup_items = items
end

function M.run_menu_item(name)
  local prose = require("sw.prose")
  local actions = {
    cut = M.cut, copy = M.copy, paste = M.paste, select_all = M.select_all, find = function() M.find() end,
    spell_add = function()
      local w = require("sw.lookup").word_at_cursor()
      if w then require("sw.spell").add_word(w) else vim.api.nvim_echo({ { "Put the cursor on a word first.", "Normal" } }, true, {}) end
    end,
    undo = function() M.undo() end, redo = function() M.redo() end, replace = function() require("sw.replace").open() end,
    italic = function()
      if M.has_selection() then prose.wrap_visual("*") else prose.toggle_insert("*") end
    end,
    bold = function()
      if M.has_selection() then prose.wrap_visual("**") else prose.toggle_insert("**") end
    end,
    scene_break = function() prose.scene_break() end,
    join = function() M.join_lines() end,
    lookup = function() require("sw.lookup").word() end,
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
  M.wrap_paste()
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

-- Text pasted by the terminal (Ctrl+Shift+V, a middle click, the right-click Paste of the terminal) goes through vim.paste.
-- In the writing window it is cleaned like our own paste: one paragraph per line, no leading tabs or spaces, no empty lines.
-- A big paste arrives in chunks; they are gathered and cleaned as one.
function M.wrap_paste()
  if M.paste_wrapped then return end
  M.paste_wrapped = true
  local original = vim.paste
  local acc
  vim.paste = function(lines, phase)
    if not (M.enabled and vim.bo.filetype == "storywheel" and vim.bo.modifiable) then return original(lines, phase) end
    if phase == -1 then return original(M.clean_pasted(lines), -1) end
    if phase == 1 or acc == nil then acc = {} end
    if #acc == 0 then
      acc = vim.deepcopy(lines)
    else
      acc[#acc] = acc[#acc] .. (lines[1] or "")
      for i = 2, #lines do acc[#acc + 1] = lines[i] end
    end
    if phase == 3 then
      local all = acc
      acc = nil
      return original(M.clean_pasted(all), -1)
    end
    return true
  end
end

-- Used by tests and by the menu to step out of notepad behavior for a moment.
function M.pause(on)
  M.paused = on
end

function M.start_typing()
  if M.can_type() then vim.cmd("startinsert") end
end

return M
