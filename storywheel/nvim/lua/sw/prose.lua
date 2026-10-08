-- Prose editing: soft wrap, display-line movement, italic/bold, paragraphs, scene breaks, concealed markup,
-- the virtual first-line indent, invisibles, typewriter mode, spellcheck.
local story = require("sw.story")
local M = {}

M.ns = vim.api.nvim_create_namespace("sw_prose")
M.INDENT = 4
M.invisibles = false
M.typewriter = false
M.spell = false
M.window = nil

vim.api.nvim_set_hl(0, "SwBreak", { link = "Comment", default = true })
vim.api.nvim_set_hl(0, "SwDouble", { link = "Error", default = true })

-- --- window and buffer setup ------------------------------------------------------------------------

function M.prepare_window(win)
  M.window = win
  local o = vim.wo[win]
  o.wrap = true
  o.linebreak = true
  o.breakindent = false
  o.number = false
  o.relativenumber = false
  o.signcolumn = "no"
  o.foldcolumn = "0"
  o.cursorline = false
  o.list = false
  o.colorcolumn = ""
  o.conceallevel = 2
  o.concealcursor = "nvc"
  o.spell = false
  o.statuscolumn = ""
end

function M.prepare_buffer(buf)
  local b = vim.bo[buf]
  b.filetype = "storywheel"
  b.textwidth = 0
  b.formatoptions = ""
  b.comments = ""
  b.autoindent = false
  b.smartindent = false
  b.cindent = false
  b.swapfile = false
  b.expandtab = true
  vim.cmd("syntax on")
  M.map_buffer(buf)
  M.decorate(buf)
end

-- --- decoration: scene breaks and the first-line indent ---------------------------------------------------

function M.column_width()
  local win = M.window
  if win and vim.api.nvim_win_is_valid(win) then return vim.api.nvim_win_get_width(win) end
  return story.setting("column_width", 72)
end

function M.decorate(buf)
  buf = buf or vim.api.nvim_get_current_buf()
  if not vim.api.nvim_buf_is_valid(buf) then return end
  if vim.bo[buf].filetype ~= "storywheel" then return end                       -- only the manuscript: never the help, menus, outline or other floats
  if require("sw.script").is_script(buf) then return require("sw.script").decorate(buf) end    -- (a screenplay: none of the prose rules)
  vim.api.nvim_buf_clear_namespace(buf, M.ns, 0, -1)
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local indent_on = story.setting("indent_display", true)
  local width = M.column_width()
  local gap = require("sw.gui").paragraph_spacing()          -- extra blank space between paragraphs (terminal only)
  for i, line in ipairs(lines) do
    local label = require("sw.util").marker_label(line)
    if label ~= nil then
      local chunks = { { "*     *     *", "SwBreak" } }
      local total = 11
      if label ~= "" then
        chunks[2] = { "   " .. label, "Comment" }
        total = total + 3 + vim.fn.strdisplaywidth(label)
      end
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, {
        end_row = i - 1, end_col = #line, conceal = " ",
        virt_text = chunks,
        virt_text_win_col = math.max(0, math.floor((width - total) / 2)),
      })
    elseif M.centered_text(line) then
      -- a centered line (>text<, as in Fountain): shown centered, the markers hidden; display only
      local inner = M.centered_text(line)
      local pad = math.max(0, math.floor((width - vim.fn.strdisplaywidth(inner)) / 2))
      local open_at = line:find(">", 1, true)
      local close_at = #line - (line:reverse():find("<", 1, true) or 1) + 1
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, { virt_text = { { string.rep(" ", pad), "Normal" } }, virt_text_pos = "inline" })
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, open_at - 1, { end_row = i - 1, end_col = open_at, conceal = "" })
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, close_at - 1, { end_row = i - 1, end_col = close_at, conceal = "" })
    elseif line:match("%S") then
      -- every line is a paragraph: it gets the indent, and (if asked for) a visual gap before the next paragraph line
      if indent_on then
        vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, {
          virt_text = { { string.rep(" ", M.INDENT), "Normal" } }, virt_text_pos = "inline",
        })
      end
      local nxt = lines[i + 1]
      if gap > 0 and nxt and nxt:match("%S") and require("sw.util").marker_label(nxt) == nil then
        local extra = {}
        for _ = 1, gap do extra[#extra + 1] = { { "", "Normal" } } end
        vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, { virt_lines = extra })
      end
    end
  end
end

-- --- centered lines ---------------------------------------------------------------------------------------

-- ">text<" (Fountain's centered text) -> "text"; anything else -> nil.
function M.centered_text(line)
  local inner = line:match("^%s*>%s*(.-)%s*<%s*$")
  if inner and inner ~= "" then return inner end
end

-- Alt+C / Ctrl+E: toggle the current line, or every selected line, between centered (>text<) and left. Scene markers and blank lines are left alone.
function M.center()
  local notepad = require("sw.notepad")
  local first = vim.api.nvim_win_get_cursor(0)[1]
  local last = first
  if notepad.has_selection() then
    local r1, _, r2 = M.selection_bounds()
    first, last = r1 + 1, r2 + 1
  end
  local lines = vim.api.nvim_buf_get_lines(0, first - 1, last, false)
  local util = require("sw.util")
  local todo, all_centered = {}, true
  for i, l in ipairs(lines) do
    if l:match("%S") and util.marker_label(l) == nil then
      todo[#todo + 1] = i
      if not M.centered_text(l) then all_centered = false end
    end
  end
  for _, i in ipairs(todo) do
    local l = lines[i]
    lines[i] = all_centered and M.centered_text(l) or (M.centered_text(l) and l or (">" .. l:match("^%s*(.-)%s*$") .. "<"))
  end
  vim.api.nvim_buf_set_lines(0, first - 1, last, false, lines)
  M.decorate(vim.api.nvim_get_current_buf())
end

-- --- italic and bold -----------------------------------------------------------------------------------

local function count(s, pat)
  local _, n = s:gsub(pat, "")
  return n
end

-- In insert mode: inside a pair, step over the closing mark; otherwise insert a pair and sit between.
function M.toggle_insert(mark)
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  local line = vim.api.nvim_get_current_line()
  local before, after = line:sub(1, col), line:sub(col + 1)
  local open
  if mark == "**" then
    open = count(before, "%*%*") % 2 == 1
  else
    open = count(before:gsub("%*%*", ""), "%*") % 2 == 1
  end
  local closing = after:sub(1, #mark) == mark and (mark == "**" or after:sub(1, 2) ~= "**")
  if open and closing then
    vim.api.nvim_win_set_cursor(0, { row, col + #mark })
    return "stepped over"
  end
  vim.api.nvim_buf_set_text(0, row - 1, col, row - 1, col, { mark .. mark })
  vim.api.nvim_win_set_cursor(0, { row, col + #mark })
  return "inserted"
end

-- Wrap (or unwrap, if already wrapped) a piece of text in a mark.
function M.toggle_text(text, mark)
  local m = #mark
  if #text >= 2 * m and text:sub(1, m) == mark and text:sub(-m) == mark
      and (mark == "**" or (text:sub(1, 2) ~= "**" or text:sub(-2) ~= "**")) then
    return text:sub(m + 1, #text - m)
  end
  return mark .. text .. mark
end

-- The selection (Visual or Select mode) as buffer coordinates, start first and end EXCLUSIVE, 0-based:
-- row1, col1, row2, col2, linewise. Works whether 'selection' is inclusive (Vim keys) or exclusive (notepad mode).
function M.selection_bounds()
  local m = vim.fn.mode()
  local a, b = vim.fn.getpos("v"), vim.fn.getpos(".")
  local r1, c1, r2, c2 = a[2] - 1, a[3] - 1, b[2] - 1, b[3] - 1
  if r1 > r2 or (r1 == r2 and c1 > c2) then r1, c1, r2, c2 = r2, c2, r1, c1 end
  local linewise = (m == "S" or m == "V")
  local last = vim.api.nvim_buf_get_lines(0, r2, r2 + 1, false)[1] or ""
  if linewise then
    c1, c2 = 0, #last
  elseif vim.o.selection ~= "exclusive" then
    local extra = (c2 < #last) and vim.str_utf_end(last, c2 + 1) or 0      -- the last character may be several bytes
    c2 = c2 + 1 + extra
  end
  if c2 > #last then c2 = #last end
  return r1, c1, r2, c2, linewise
end

-- In visual or select mode: wrap the selection (each line of it on its own, so the marks stay on one line);
-- wrapping something already wrapped takes the marks off.
function M.wrap_visual(mark)
  local r1, c1, r2, c2 = M.selection_bounds()
  vim.cmd("normal! \27")
  for row = r2, r1, -1 do
    local line = vim.api.nvim_buf_get_lines(0, row, row + 1, false)[1]
    local from = (row == r1) and c1 or 0
    local to = (row == r2) and c2 or #line
    local seg = line:sub(from + 1, to)
    if seg:match("%S") then
      local lead, body, tail = seg:match("^(%s*)(.-)(%s*)$")
      vim.api.nvim_buf_set_text(0, row, from, row, to, { lead .. M.toggle_text(body, mark) .. tail })
    end
  end
end

-- --- paragraphs and scene breaks ------------------------------------------------------------------------

-- Enter starts a new paragraph on the next line (one line is one paragraph; no blank line). Nothing extra on an empty line.
-- A line holding only `***` / `* * *` / `#` becomes the scene break chosen in Settings.
-- The mapping is an expression that hands over to enter() through <Cmd>, so enter() runs after the text typed
-- before it has gone into the buffer (an expression is evaluated early when keys are queued up).
function M.enter_expr()
  if vim.fn.pumvisible() == 1 and vim.fn.complete_info({ "selected" }).selected >= 0 then
    return vim.api.nvim_replace_termcodes("<C-y>", true, false, true)
  end
  return vim.api.nvim_replace_termcodes("<Cmd>lua require('sw.prose').enter()<CR>", true, false, true)
end

function M.break_text()
  local m = story.setting("scene_marker", "***")
  if m ~= "***" and m ~= "* * *" and m ~= "#" then m = "***" end
  return m
end

function M.enter()
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  local line = vim.api.nvim_get_current_line()
  if line == "" then return end
  if require("sw.util").is_plain_break(line) and col >= #line then
    vim.api.nvim_buf_set_lines(0, row - 1, row, false, { M.break_text(), "" })     -- typed as a break: it is one, in the chosen form
    vim.api.nvim_win_set_cursor(0, { row + 1, 0 })
    M.decorate(0)
    return
  end
  vim.api.nvim_buf_set_lines(0, row - 1, row, false, { line:sub(1, col), line:sub(col + 1) })
  vim.api.nvim_win_set_cursor(0, { row + 1, 0 })
end

-- Put a scene break (the form chosen in Settings) on a line of its own after the current paragraph, and leave the cursor on a new
-- empty line after it. On an empty line, the break takes that line's place.
function M.scene_break()
  local buf = 0
  local row = vim.api.nvim_win_get_cursor(0)[1]
  local line = vim.api.nvim_buf_get_lines(buf, row - 1, row, false)[1] or ""
  local nxt = vim.api.nvim_buf_get_lines(buf, row, row + 1, false)[1]
  local mark = M.break_text()
  if line:match("%S") then
    local new = { mark }
    if nxt == nil or nxt:match("%S") then new[2] = "" end                  -- (an empty line that is already there is used)
    vim.api.nvim_buf_set_lines(buf, row, row, false, new)
    vim.api.nvim_win_set_cursor(0, { row + 2, 0 })
  else
    vim.api.nvim_buf_set_lines(buf, row - 1, row, false, { mark, "" })
    vim.api.nvim_win_set_cursor(0, { row + 1, 0 })
  end
  M.decorate(buf)
end

-- The cursor never rests on a scene-marker line (`* * *`, `* * * Title`) in notepad mode: typing there would turn the marker into a paragraph,
-- and the raw marker shows beside the centered one. Arriving on one (arrows, a click, reopening there) moves on to the nearest line that is
-- not a marker: the way you were going, else the other way; a marker at the very end gets an empty line after it. Typing a break
-- (`***` then Enter) is not "arriving": the row has not changed. A scene is renamed from the sidebar (r).
function M.guard_marker()
  local np = require("sw.notepad")
  local layout = require("sw.layout")
  if not (np.enabled and layout.main and vim.api.nvim_get_current_win() == layout.main) then return end
  local buf = vim.api.nvim_get_current_buf()
  if vim.bo[buf].filetype ~= "storywheel" or not vim.bo[buf].modifiable or require("sw.script").is_script(buf) then return end
  local mode = vim.fn.mode()
  if not (mode:sub(1, 1) == "i" or mode:sub(1, 1) == "n") then return end    -- (Insert, Normal, and Insert's one-command Normal "niI"; a selection may run over markers)
  local row = vim.api.nvim_win_get_cursor(0)[1]
  local last = M.guard_last
  M.guard_last = { buf = buf, row = row }
  if last and last.buf == buf and last.row == row then return end             -- same line: typing, not arriving
  local util = require("sw.util")
  local line = vim.api.nvim_buf_get_lines(buf, row - 1, row, false)[1] or ""
  if util.marker_label(line) == nil then return end
  local count = vim.api.nvim_buf_line_count(buf)
  local function is_marker(r) return util.marker_label(vim.api.nvim_buf_get_lines(buf, r - 1, r, false)[1] or "") ~= nil end
  local dir = (last and last.buf == buf and last.row > row) and -1 or 1
  local target
  for _, d in ipairs({ dir, -dir }) do
    local r = row + d
    while r >= 1 and r <= count and is_marker(r) do r = r + d end
    if r >= 1 and r <= count then target = r break end
  end
  if not target then
    vim.api.nvim_buf_set_lines(buf, count, count, false, { "" })
    target = count + 1
  end
  vim.api.nvim_win_set_cursor(0, { target, 0 })
  M.guard_last = { buf = buf, row = target }
end

-- --- toggles ----------------------------------------------------------------------------------------------

function M.set_invisibles(on)
  M.invisibles = on
  local win = M.window
  vim.wo[win].list = on
  vim.wo[win].listchars = "space:·,trail:▪,tab:→ ,eol:¶,nbsp:␣"
  if M.double_match then pcall(vim.fn.matchdelete, M.double_match, win) M.double_match = nil end
  if on then M.double_match = vim.fn.matchadd("SwDouble", [[\S\zs  \+\ze\S]], 10, -1, { window = win }) end
end

function M.set_typewriter(on)
  M.typewriter = on
  vim.o.scrolloff = on and 999 or 4
  if on then vim.cmd("normal! zz") end
end

function M.set_spell(on)
  M.spell = on
  vim.wo[M.window].spell = on                       -- (spell belongs to the window; the language and word lists to each buffer)
  require("sw.spell").apply_all()
end

function M.toggle(which)
  local fn = { invisibles = M.set_invisibles, typewriter = M.set_typewriter, spell = M.set_spell }
  local now = not M[which]
  fn[which](now)
  vim.api.nvim_echo({ { which .. (now and " on" or " off"), "Normal" } }, false, {})
end

-- --- keys ---------------------------------------------------------------------------------------------------

function M.ctrl_i_wanted()
  local setting = require("sw.session").pref("ctrl_i")
  if setting == "yes" then return true end
  if setting == "no" then return false end
  -- "auto": only terminals known to report Ctrl+I apart from Tab
  if require("sw.gui").detected() then return true end              -- a GUI window reports Ctrl+I apart from Tab
  local term, prog = os.getenv("TERM") or "", os.getenv("TERM_PROGRAM") or ""
  return term:find("kitty") ~= nil or term:find("foot") ~= nil or term:find("ghostty") ~= nil
      or os.getenv("KITTY_WINDOW_ID") ~= nil or os.getenv("WEZTERM_EXECUTABLE") ~= nil
      or prog == "WezTerm" or prog == "ghostty"
end

function M.map_buffer(buf)
  local function map(mode, lhs, rhs, opts)
    vim.keymap.set(mode, lhs, rhs, vim.tbl_extend("force", { buffer = buf, silent = true }, opts or {}))
  end
  require("sw.notepad").map_buffer(buf)             -- (notepad keys first; the rest below can refine them)
  -- movement by displayed lines
  map({ "n", "x" }, "j", "gj")
  map({ "n", "x" }, "k", "gk")
  map({ "n", "x" }, "0", "g0")
  map({ "n", "x" }, "^", "g^")
  map({ "n", "x" }, "$", "g$")
  map("n", "<Down>", "gj")
  map("n", "<Up>", "gk")
  map("i", "<Down>", "<C-o>gj")
  map("i", "<Up>", "<C-o>gk")
  local script = require("sw.script")
  if script.is_script(buf) then
    -- a screenplay: italic and bold as in prose, then the screenplay keys (Tab, Enter, the flip test); no paragraph rules, no scene breaks
    for _, spec in ipairs({ { story.setting("key_italic", "<A-i>"), "*" }, { story.setting("key_bold", "<A-b>"), "**" }, { "<C-b>", "**" } }) do
      map("i", spec[1], function() M.toggle_insert(spec[2]) end)
      map({ "x", "s" }, spec[1], function() M.wrap_visual(spec[2]) end)
    end
    script.map_buffer(buf)
    require("sw.notepad").disable_alt_keys(buf)
    return
  end
  -- paragraphs
  map("i", "<CR>", function() return M.enter_expr() end, { expr = true, replace_keycodes = false })
  map("n", "o", "A<CR>", { remap = true })
  -- formatting (Alt works in every terminal; Ctrl+I only where the terminal can tell it from Tab)
  for _, spec in ipairs({ { story.setting("key_italic", "<A-i>"), "*" }, { story.setting("key_bold", "<A-b>"), "**" }, { "<C-b>", "**" } }) do
    map("i", spec[1], function() M.toggle_insert(spec[2]) end)
    map({ "x", "s" }, spec[1], function() M.wrap_visual(spec[2]) end)
  end
  if M.ctrl_i_wanted() then
    map("i", "<C-i>", function() M.toggle_insert("*") end)
    map({ "x", "s" }, "<C-i>", function() M.wrap_visual("*") end)
  end
  -- scene break
  map({ "i", "n" }, story.setting("key_scene_break", "<A-s>"), function() M.scene_break() end)
  -- Tab: next name in the completion list; at the start of a paragraph it does nothing (the indent is automatic)
  map("i", "<Tab>", function()
    if vim.fn.pumvisible() == 1 then return vim.api.nvim_replace_termcodes("<C-n>", true, false, true) end
    local before = vim.api.nvim_get_current_line():sub(1, vim.api.nvim_win_get_cursor(0)[2])
    if before:match("^%s*$") then
      if not M.told_indent then
        M.told_indent = true
        vim.schedule(function() vim.api.nvim_echo({ { "Indents are automatic: every paragraph gets one, so Tab does nothing here.", "Normal" } }, true, {}) end)
      end
      return ""
    end
    return vim.api.nvim_replace_termcodes("<Tab>", true, false, true)
  end, { expr = true, replace_keycodes = false })
  -- a screenplay's keys that mean nothing in prose say so, instead of typing a letter
  map({ "i", "s", "n" }, story.setting("key_flip_test", "<A-f>"), function()
    vim.api.nvim_echo({ { "The flip test is for screenplays.", "Normal" } }, true, {})
  end)
  require("sw.notepad").disable_alt_keys(buf)
end

return M
