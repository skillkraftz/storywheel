-- Find and replace (Ctrl+H, a setting): a small floating form over the writing window. Two lines to type in (Find, Replace);
-- Enter finds the next match, Alt+R replaces the one you are on, Alt+A replaces all (one undo step), Alt+C match case, Alt+W whole
-- word. The title says how many matches there are and what was replaced. Matching is literal text (no patterns).
local M = {}

M.opts = { case = false, word = false }
M.find_text = ""
M.replace_text = ""

local function keyword_char(c)
  return c ~= nil and c ~= "" and (c:match("[%w_]") ~= nil or c:byte() >= 128)
end

-- The Vim pattern that finds `text` literally. Whole word only where the text starts/ends with a word character.
function M.pattern(text, opts)
  opts = opts or M.opts
  if text == nil or text == "" then return nil end
  local body = (text:gsub("\\", "\\\\"))
  if opts.word and keyword_char(text:sub(1, 1)) then body = "\\<" .. body end
  if opts.word and keyword_char(text:sub(-1)) then body = body .. "\\>" end
  return "\\V" .. (opts.case and "\\C" or "\\c") .. body
end

function M.regex(text, opts)
  local pat = M.pattern(text, opts)
  return pat and vim.regex(pat) or nil
end

-- All matches in a buffer: { {row, col, end_col}, ... } (0-based rows, byte columns; end_col is exclusive).
function M.matches(buf, text, opts)
  local re = M.regex(text, opts)
  local out = {}
  if not re then return out end
  local count = vim.api.nvim_buf_line_count(buf)
  for row = 0, count - 1 do
    local line = vim.api.nvim_buf_get_lines(buf, row, row + 1, false)[1]
    local from = 0
    while from <= #line do
      local s, e = re:match_line(buf, row, from)
      if not s then break end
      out[#out + 1] = { row, from + s, from + e }
      from = from + (e > s and e or s + 1)
    end
  end
  return out
end

-- The first match at or after (row, col), wrapping round. Returns the match or nil.
function M.next_match(buf, text, row, col, opts, backwards)
  local all = M.matches(buf, text, opts)
  if #all == 0 then return nil end
  if backwards then
    for i = #all, 1, -1 do
      local m = all[i]
      if m[1] < row or (m[1] == row and m[2] < col) then return m end
    end
    return all[#all]
  end
  for _, m in ipairs(all) do
    if m[1] > row or (m[1] == row and m[2] >= col) then return m end
  end
  return all[1]
end

-- Replace every match in the buffer by `repl` in a single undo step. Returns how many were replaced.
function M.replace_all(buf, text, repl, opts)
  local all = M.matches(buf, text, opts)
  if #all == 0 then return 0 end
  local byrow = {}
  for _, m in ipairs(all) do
    byrow[m[1]] = byrow[m[1]] or {}
    table.insert(byrow[m[1]], m)
  end
  local first, last = all[1][1], all[#all][1]
  local lines = vim.api.nvim_buf_get_lines(buf, first, last + 1, false)
  for row = first, last do
    local ms = byrow[row]
    if ms then
      local line = lines[row - first + 1]
      for i = #ms, 1, -1 do
        line = line:sub(1, ms[i][2]) .. repl .. line:sub(ms[i][3] + 1)
      end
      lines[row - first + 1] = line
    end
  end
  vim.api.nvim_buf_set_lines(buf, first, last + 1, false, lines)
  return #all
end

-- Replace the match under/after (row, col) and return the next one's position (so repeated presses walk through the text).
function M.replace_one(buf, text, repl, row, col, opts)
  local m = M.next_match(buf, text, row, col, opts)
  if not m then return 0 end
  vim.api.nvim_buf_set_text(buf, m[1], m[2], m[1], m[3], { repl })
  return 1, m[1], m[2] + #repl
end

-- --- the form ------------------------------------------------------------------------------------------------------------

local function main_win()
  return require("sw.layout").main
end

function M.status(count, note)
  local bits = {}
  bits[#bits + 1] = count == nil and "" or (count == 1 and "1 match" or count .. " matches")
  bits[#bits + 1] = M.opts.case and "case: match" or "case: ignore"
  bits[#bits + 1] = M.opts.word and "whole word" or "any part of a word"
  if note then bits[#bits + 1] = note end
  return " Find and replace · " .. table.concat(vim.tbl_filter(function(b) return b ~= "" end, bits), " · ") .. " "
end

function M.open(prefill)
  local notepad = require("sw.notepad")
  local win = main_win()
  local mbuf = vim.api.nvim_win_get_buf(win)
  if M.win and vim.api.nvim_win_is_valid(M.win) then vim.api.nvim_set_current_win(M.win) return M.win end
  if prefill == nil and notepad.has_selection() then
    local text = notepad.selected_text()
    if text and not text:find("\n") then prefill = text end
    vim.cmd("normal! \27")
  end
  local find = prefill or M.find_text or ""
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, { find, M.replace_text or "" })
  vim.bo[buf].bufhidden = "wipe"
  local width = 60
  local fwin = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 2, col = math.floor((vim.o.columns - width) / 2), width = width, height = 2,
    style = "minimal", border = "rounded", title = M.status(nil), title_pos = "center",
    footer = " Enter next · Alt+R replace · Alt+A all · Alt+C case · Alt+W word · Esc close ", footer_pos = "center",
  })
  M.win, M.buf, M.main_buf, M.main = fwin, buf, mbuf, win
  local ns = vim.api.nvim_create_namespace("sw_replace_labels")
  for row, label in ipairs({ "Find     ", "Replace  " }) do
    vim.api.nvim_buf_set_extmark(buf, ns, row - 1, 0, { virt_text = { { label, "Comment" } }, virt_text_pos = "inline", right_gravity = false })
  end
  local function texts()
    local l = vim.api.nvim_buf_get_lines(buf, 0, 2, false)
    return l[1] or "", l[2] or ""
  end
  local hl_id
  local function refresh(note)
    local f, r = texts()
    M.find_text, M.replace_text = f, r
    local n = #M.matches(mbuf, f)
    if vim.api.nvim_win_is_valid(fwin) then
      vim.api.nvim_win_set_config(fwin, { title = M.status(f ~= "" and n or nil, note), title_pos = "center" })
    end
    if hl_id then pcall(vim.fn.matchdelete, hl_id, win) hl_id = nil end
    if f ~= "" then
      pcall(function() hl_id = vim.fn.matchadd("Search", M.pattern(f), 10, -1, { window = win }) end)
    end
    return n
  end
  local function goto_match(m)
    if not m then return end
    vim.api.nvim_win_set_cursor(win, { m[1] + 1, m[2] })
    vim.api.nvim_win_call(win, function() vim.cmd("normal! zz") end)
  end
  local function cursor0()
    local c = vim.api.nvim_win_get_cursor(win)
    return c[1] - 1, c[2]
  end
  local function find_next(back)
    local f = texts()
    if f == "" then return end
    local row, col = cursor0()
    local m = M.next_match(mbuf, f, row, back and col or col + (M.just_found and 1 or 0), M.opts, back)
    if m then M.just_found = true goto_match(m) refresh() else refresh("not found") end
  end
  local function replace_one()
    local f, r = texts()
    if f == "" then return end
    local row, col = cursor0()
    local n, nrow, ncol = M.replace_one(mbuf, f, r, row, M.just_found and col or col, M.opts)
    if n == 0 then refresh("not found") return end
    vim.api.nvim_win_set_cursor(win, { nrow + 1, ncol })
    refresh("replaced 1")
  end
  local function replace_all()
    local f, r = texts()
    if f == "" then return end
    local n = M.replace_all(mbuf, f, r, M.opts)
    M.last_replaced = n
    refresh(n == 0 and "nothing to replace" or ("replaced " .. n))
  end
  local function toggle(which)
    M.opts[which] = not M.opts[which]
    refresh()
  end
  local function close()
    if hl_id then pcall(vim.fn.matchdelete, hl_id, win) end
    if vim.api.nvim_win_is_valid(fwin) then vim.api.nvim_win_close(fwin, true) end
    M.win = nil
    if vim.api.nvim_win_is_valid(win) then vim.api.nvim_set_current_win(win) end
    notepad.insert(true)
  end
  local function line_focus(n)
    vim.api.nvim_win_set_cursor(fwin, { n, #(vim.api.nvim_buf_get_lines(buf, n - 1, n, false)[1] or "") })
  end
  local function in_line()
    return vim.api.nvim_win_get_cursor(fwin)[1]
  end
  local function map(lhs, fn)
    vim.keymap.set({ "i", "n" }, lhs, fn, { buffer = buf, silent = true, nowait = true })
  end
  map("<CR>", function() if in_line() == 1 then find_next(false) else replace_one() end end)
  map("<Tab>", function() line_focus(in_line() == 1 and 2 or 1) end)
  map("<S-Tab>", function() line_focus(in_line() == 1 and 2 or 1) end)
  map("<Down>", function() line_focus(2) end)
  map("<Up>", function() line_focus(1) end)
  map("<A-r>", replace_one)
  map("<A-a>", replace_all)
  map("<A-c>", function() toggle("case") end)
  map("<A-w>", function() toggle("word") end)
  map("<A-n>", function() find_next(false) end)
  map("<A-p>", function() find_next(true) end)
  map("<Esc>", close)
  map("<C-q>", close)
  -- the form is exactly two lines
  vim.api.nvim_create_autocmd({ "TextChangedI", "TextChanged" }, { buffer = buf, callback = function()
    if vim.api.nvim_buf_line_count(buf) ~= 2 then
      local l = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
      vim.api.nvim_buf_set_lines(buf, 0, -1, false, { l[1] or "", l[2] or "" })
    end
    M.just_found = false
    refresh()
  end })
  vim.api.nvim_create_autocmd("WinClosed", { pattern = tostring(fwin), once = true, callback = function()
    if hl_id then pcall(vim.fn.matchdelete, hl_id, win) end
    M.win = nil
  end })
  M.actions = { find_next = find_next, replace_one = replace_one, replace_all = replace_all, toggle = toggle, close = close, refresh = refresh }
  refresh()
  line_focus(1)
  vim.cmd("startinsert!")
  return fwin
end

return M
