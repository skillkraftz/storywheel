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
    elseif gap > 0 and line == "" and i > 1 and lines[i - 1]:match("%S") and i < #lines then
      local extra = {}
      for _ = 1, gap do extra[#extra + 1] = { { "", "Normal" } } end
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, { virt_lines = extra })
    elseif indent_on and line:match("%S") and (i == 1 or not lines[i - 1]:match("%S") or require("sw.util").marker_label(lines[i - 1]) ~= nil) then
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, {
        virt_text = { { string.rep(" ", M.INDENT), "Normal" } }, virt_text_pos = "inline",
      })
    end
  end
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

-- Enter starts a new paragraph: a blank line between, nothing extra on an empty line.
-- The mapping is an expression that hands over to enter() through <Cmd>, so enter() runs after the text typed
-- before it has gone into the buffer (an expression is evaluated early when keys are queued up).
function M.enter_expr()
  if vim.fn.pumvisible() == 1 and vim.fn.complete_info({ "selected" }).selected >= 0 then
    return vim.api.nvim_replace_termcodes("<C-y>", true, false, true)
  end
  return vim.api.nvim_replace_termcodes("<Cmd>lua require('sw.prose').enter()<CR>", true, false, true)
end

function M.enter()
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  local line = vim.api.nvim_get_current_line()
  if line == "" then return end
  vim.api.nvim_buf_set_lines(0, row - 1, row, false, { line:sub(1, col), "", line:sub(col + 1) })
  vim.api.nvim_win_set_cursor(0, { row + 2, 0 })
end

-- Insert `* * *` between paragraphs (with a blank line each side) and leave the cursor on the empty line after it.
function M.scene_break()
  local buf = 0
  local row = vim.api.nvim_win_get_cursor(0)[1]
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local line = lines[row] or ""
  local nxt = lines[row + 1]
  local next_blank = nxt ~= nil and not nxt:match("%S")
  local new, target
  if line:match("%S") then
    new = { "", "* * *" }
    if not next_blank then new[#new + 1] = "" end
    target = row + 3                       -- the blank line after the break
  else
    new = { "* * *" }
    if not next_blank then new[#new + 1] = "" end
    target = row + 2
  end
  vim.api.nvim_buf_set_lines(buf, row, row, false, new)
  local count = vim.api.nvim_buf_line_count(buf)
  vim.api.nvim_win_set_cursor(0, { math.min(target, count), 0 })
  M.decorate(buf)
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
  vim.wo[M.window].spell = on
  vim.bo.spelllang = "en_us"
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
  -- paragraphs
  map("i", "<CR>", function() return M.enter_expr() end, { expr = true, replace_keycodes = false })
  map("n", "o", "A<CR>", { remap = true })
  -- formatting (Alt works in every terminal; Ctrl+I only where the terminal can tell it from Tab)
  for _, spec in ipairs({ { "<A-i>", "*" }, { "<A-b>", "**" }, { "<C-b>", "**" } }) do
    map("i", spec[1], function() M.toggle_insert(spec[2]) end)
    map({ "x", "s" }, spec[1], function() M.wrap_visual(spec[2]) end)
  end
  if M.ctrl_i_wanted() then
    map("i", "<C-i>", function() M.toggle_insert("*") end)
    map({ "x", "s" }, "<C-i>", function() M.wrap_visual("*") end)
  end
  -- scene break
  map({ "i", "n" }, "<A-s>", function() M.scene_break() end)
  -- name completion with Tab
  map("i", "<Tab>", function()
    if vim.fn.pumvisible() == 1 then return vim.api.nvim_replace_termcodes("<C-n>", true, false, true) end
    return vim.api.nvim_replace_termcodes("<Tab>", true, false, true)
  end, { expr = true, replace_keycodes = false })
end

return M
