-- The scene sidebar: every scene of the manuscript, found by its marker line (`* * *` or `* * * Title`), in order, with
-- its first line. Enter jumps there; a adds a scene; r renames it (edits its marker); J / K move it down / up; q closes.
local util = require("sw.util")
local story = require("sw.story")
local layout = require("sw.layout")
local M = {}

M.entries = {}     -- buffer line (1-based) -> a scene from story.scene_list()

local function main_path()
  return vim.api.nvim_buf_get_name(vim.api.nvim_win_get_buf(layout.main))
end

local function truncate(text, width)
  text = text:gsub("%*+", "")
  if vim.fn.strdisplaywidth(text) <= width then return text end
  return vim.fn.strcharpart(text, 0, width - 1) .. "…"
end

function M.width()
  return layout.sidebar_width
end

-- The lines and the jump table.
function M.build()
  local lines, entries = {}, {}
  local path = main_path()
  local row = vim.api.nvim_win_is_valid(layout.main) and vim.api.nvim_win_get_cursor(layout.main)[1] or 0
  for _, sc in ipairs(story.scene_list()) do
    local here = sc.path == path and row >= sc.start and row <= sc.finish
    local line = string.format("%s%02d %s — %s", here and "▶ " or "  ", sc.n, sc.title, sc.first_line)
    lines[#lines + 1] = truncate(line, M.width() - 1)
    entries[#lines] = sc
  end
  if #lines == 0 then lines = { "  (no scenes yet: press a)" } end
  return lines, entries
end

function M.render()
  if not layout.sidebar_open then return end
  local buf = vim.api.nvim_win_get_buf(layout.left)
  local lines, entries = M.build()
  M.entries = entries
  vim.bo[buf].modifiable = true
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  for i, e in pairs(entries) do
    if lines[i]:sub(1, 3) == "▶ " then pcall(vim.api.nvim_win_set_cursor, layout.left, { i, 0 }) break end
  end
end

function M.current_entry()
  return M.entries[vim.api.nvim_win_get_cursor(layout.left)[1]]
end

function M.jump(entry)
  entry = entry or M.current_entry()
  if not entry then return end
  vim.api.nvim_set_current_win(layout.main)
  require("sw").open_scene(entry.path, { entry.body, 0 })
end

-- Work on a file through its buffer, so unsaved edits are never lost and the writing window shows the change at once.
local function buffer_of(path)
  return util.load_buffer(path)
end

local function save(b)
  vim.api.nvim_buf_call(b, function() vim.cmd("silent! write") end)
end

-- Give a scene a new title: its marker line says `* * * Title` (a first scene without a marker gets one).
function M.rename(entry, title)
  entry = entry or M.current_entry()
  if not entry or not title or title == "" then return end
  local b = buffer_of(entry.path)
  local marker = "* * * " .. title
  if entry.marked then
    vim.api.nvim_buf_set_lines(b, entry.start - 1, entry.start, false, { marker })
  else
    vim.api.nvim_buf_set_lines(b, 0, 0, false, { marker, "" })
  end
  save(b)
  M.render()
end

-- Swap a scene with its neighbour in the same file (direction -1 up, +1 down). Returns true if it moved.
function M.move(entry, direction)
  entry = entry or M.current_entry()
  if not entry then return false end
  local all = story.scene_list()
  local idx
  for i, sc in ipairs(all) do if sc.path == entry.path and sc.start == entry.start then idx = i end end
  local other = idx and all[idx + direction]
  if not other then return false end
  if other.path ~= entry.path then
    vim.api.nvim_echo({ { "That would move the scene into another chapter file: move it by hand.", "WarningMsg" } }, false, {})
    return false
  end
  local a, b_ = entry, other
  if direction < 0 then a, b_ = other, entry end             -- a comes first in the file
  local b = buffer_of(entry.path)
  local lines = vim.api.nvim_buf_get_lines(b, 0, -1, false)
  local block_a = vim.list_slice(lines, a.start, a.finish)
  local block_b = vim.list_slice(lines, b_.start, b_.finish)
  -- every scene but the first begins with a marker: an unmarked first scene that moves down gets one
  if not a.marked then table.insert(block_a, 1, "* * *") end
  if not b_.marked then table.insert(block_b, 1, "* * *") end
  local merged = {}
  vim.list_extend(merged, block_b)                            -- b now leads the pair, a follows
  vim.list_extend(merged, block_a)
  local rewritten = {}
  vim.list_extend(rewritten, vim.list_slice(lines, 1, a.start - 1))
  vim.list_extend(rewritten, merged)
  vim.list_extend(rewritten, vim.list_slice(lines, b_.finish + 1, #lines))
  local was_here = main_path() == entry.path
  local cursor = was_here and vim.api.nvim_win_get_cursor(layout.main) or nil
  vim.api.nvim_buf_set_lines(b, 0, -1, false, rewritten)
  save(b)
  if cursor then                                              -- the cursor stays on the same text: it moved with its scene
    local row = cursor[1]
    if row >= a.start and row <= a.finish then
      row = a.start + #block_b + (row - a.start) + (a.marked and 0 or 1)
    elseif row >= b_.start and row <= b_.finish then
      row = a.start + (row - b_.start)
    end
    pcall(vim.api.nvim_win_set_cursor, layout.main, { math.min(row, vim.api.nvim_buf_line_count(b)), cursor[2] })
  end
  M.render()
  return true
end

function M.add(title)
  local path, line = story.add_scene(title ~= "" and title or nil)
  M.render()
  return path, line
end

local function prompt(label, default, cb)
  vim.ui.input({ prompt = label, default = default }, function(text) if text and text ~= "" then cb(text) end end)
end

function M.map(buf)
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, silent = true, nowait = true }) end
  map("<CR>", function() M.jump() end)
  map("<2-LeftMouse>", function() M.jump() end)
  map("a", function()
    prompt("New scene title: ", "", function(t)
      local path, line = M.add(t)
      vim.api.nvim_set_current_win(layout.main)
      require("sw").open_scene(path, { line + 1, 0 })
    end)
  end)
  map("r", function() local e = M.current_entry() if e then prompt("Rename scene: ", e.label ~= "" and e.label or e.title, function(t) M.rename(e, t) end) end end)
  map("J", function() M.move(nil, 1) end)
  map("K", function() M.move(nil, -1) end)
  map("q", function() M.close() end)
  map("<Esc>", function() M.close() end)
  map("j", "j")
  map("k", "k")
end

function M.open()
  layout.sidebar_open = true
  layout.apply()
  local buf = vim.api.nvim_create_buf(false, true)
  vim.bo[buf].buftype, vim.bo[buf].bufhidden, vim.bo[buf].swapfile = "nofile", "wipe", false
  vim.api.nvim_win_set_buf(layout.left, buf)
  local o = vim.wo[layout.left]
  o.wrap, o.number, o.cursorline, o.winfixwidth = false, false, true, true
  o.winhighlight = "Normal:SwPad,CursorLine:Visual"
  M.map(buf)
  M.render()
  vim.api.nvim_set_current_win(layout.left)
end

function M.close()
  if not layout.sidebar_open then return end
  layout.sidebar_open = false
  local buf = vim.api.nvim_create_buf(false, true)
  vim.bo[buf].buftype, vim.bo[buf].bufhidden, vim.bo[buf].swapfile = "nofile", "hide", false
  vim.bo[buf].modifiable = false
  vim.api.nvim_win_set_buf(layout.left, buf)
  vim.wo[layout.left].cursorline = false
  vim.wo[layout.left].winhighlight = "Normal:SwPad,EndOfBuffer:SwPad,NormalNC:SwPad"
  layout.apply()
  if vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
end

function M.toggle()
  if layout.sidebar_open then M.close() else M.open() end
end

return M
