-- The scene sidebar: every scene file with its first line (and each `* * *` section inside it), in order.
-- Enter jumps there; a adds a scene; r renames; J / K move a scene down / up; q closes.
local util = require("sw.util")
local story = require("sw.story")
local layout = require("sw.layout")
local M = {}

M.entries = {}     -- buffer line (1-based) -> { path=, line=, scene= }

local function main_path()
  return vim.api.nvim_buf_get_name(vim.api.nvim_win_get_buf(layout.main))
end

local function truncate(text, width)
  text = text:gsub("%*+", "")
  if vim.fn.strdisplaywidth(text) <= width then return text end
  return vim.fn.strcharpart(text, 0, width - 1) .. "…"
end

-- The lines and the jump table, from the scene files (open buffers are taken as they are now).
function M.build()
  local lines, entries = {}, {}
  local current = main_path()
  for _, s in ipairs(story.scenes()) do
    local b = vim.fn.bufnr(s.path)
    local text_lines
    if b ~= -1 and vim.api.nvim_buf_is_loaded(b) then text_lines = vim.api.nvim_buf_get_lines(b, 0, -1, false)
    else text_lines = vim.split(util.read(s.path) or "", "\n", { plain = true }) end
    local first = ""
    for _, l in ipairs(text_lines) do if l:match("%S") and l ~= "* * *" then first = l break end end
    local mark = (s.path == current) and "▶ " or "  "
    local num = s.name:match("^(%d+)") or "--"
    lines[#lines + 1] = truncate(string.format("%s%s %s — %s", mark, num, story.scene_title(s.name), first), M.width() - 1)
    entries[#lines] = { path = s.path, line = 1, scene = s }
    local after_break = false
    for i, l in ipairs(text_lines) do
      if l == "* * *" then after_break = true
      elseif after_break and l:match("%S") then
        lines[#lines + 1] = truncate("      ✦ " .. l, M.width() - 1)
        entries[#lines] = { path = s.path, line = i, scene = s }
        after_break = false
      end
    end
  end
  if #lines == 0 then lines = { "  (no scenes yet: press a)" } end
  return lines, entries
end

function M.width()
  return layout.sidebar_width
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
    if e.path == main_path() and e.line == 1 then pcall(vim.api.nvim_win_set_cursor, layout.left, { i, 0 }) break end
  end
end

function M.current_entry()
  local row = vim.api.nvim_win_get_cursor(layout.left)[1]
  return M.entries[row]
end

function M.jump(entry)
  entry = entry or M.current_entry()
  if not entry then return end
  vim.api.nvim_set_current_win(layout.main)
  require("sw").open_scene(entry.path, { entry.line, 0 })
end

local function reopen(path_before, path_after)
  -- scene buffers hold old names after a rename: write, wipe them, and open the current scene again
  require("sw.backup").save_all()
  local current = main_path()
  local target = current
  if path_before and current == path_before then target = path_after end
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    local n = vim.api.nvim_buf_get_name(b)
    if n:find(story.manuscript, 1, true) and b ~= vim.api.nvim_win_get_buf(layout.main) then pcall(vim.cmd, "silent! bwipeout! " .. b) end
  end
  return target
end

local function rename_file(old, new)
  if old == new then return end
  assert(os.rename(old, new))
end

-- Give a scene a new title (its number stays).
function M.rename(entry, title)
  entry = entry or M.current_entry()
  if not entry or not title or title == "" then return end
  local path = entry.path
  local num = entry.scene.name:match("^(%d+)") or "00"
  local new = string.format("%s/%s-%s.md", story.manuscript, num, story.slugify(title))
  require("sw.backup").save_all()
  local was_current = main_path() == path
  vim.api.nvim_set_current_win(layout.main)
  if was_current then vim.cmd("silent! enew") end
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_get_name(b) == path then pcall(vim.cmd, "silent! bwipeout! " .. b) end
  end
  rename_file(path, new)
  if was_current then require("sw").open_scene(new) end
  M.render()
end

-- Swap a scene with its neighbour (direction -1 up, +1 down): their number prefixes trade places.
function M.move(entry, direction)
  entry = entry or M.current_entry()
  if not entry then return end
  local scenes = story.scenes()
  local idx
  for i, s in ipairs(scenes) do if s.path == entry.path then idx = i end end
  local other = scenes[idx + direction]
  if not idx or not other then return end
  local a, b = scenes[idx], other
  local na, nb = a.name:match("^(%d+)%-(.*)$")
  local nb_num, nb_rest = b.name:match("^(%d+)%-(.*)$")
  local a_num, a_rest = a.name:match("^(%d+)%-(.*)$")
  if not (a_num and nb_num) then return end
  require("sw.backup").save_all()
  local current = main_path()
  vim.api.nvim_set_current_win(layout.main)
  vim.cmd("silent! enew")
  for _, bf in ipairs(vim.api.nvim_list_bufs()) do
    local n = vim.api.nvim_buf_get_name(bf)
    if n == a.path or n == b.path then pcall(vim.cmd, "silent! bwipeout! " .. bf) end
  end
  local tmp = story.manuscript .. "/.swap-tmp.md"
  local a_new = string.format("%s/%s-%s", story.manuscript, nb_num, a_rest)
  local b_new = string.format("%s/%s-%s", story.manuscript, a_num, nb_rest)
  rename_file(a.path, tmp)
  rename_file(b.path, b_new)
  rename_file(tmp, a_new)
  local reopen_path = current
  if current == a.path then reopen_path = a_new elseif current == b.path then reopen_path = b_new end
  require("sw").open_scene(reopen_path)
  M.render()
  -- keep the cursor on the scene that moved
  for i, e in pairs(M.entries) do if e.path == a_new and e.line == 1 then pcall(vim.api.nvim_win_set_cursor, layout.left, { i, 0 }) end end
end

function M.add(title)
  title = title or ""
  if title == "" then title = "scene" end
  local path = story.add_scene(title)
  M.render()
  return path
end

local function prompt(label, default, cb)
  vim.ui.input({ prompt = label, default = default }, function(text) if text and text ~= "" then cb(text) end end)
end

function M.map(buf)
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, silent = true, nowait = true }) end
  map("<CR>", function() M.jump() end)
  map("<2-LeftMouse>", function() M.jump() end)
  map("a", function() prompt("New scene title: ", "", function(t) local p = M.add(t) M.jump({ path = p, line = 1 }) end) end)
  map("r", function() local e = M.current_entry() if e then prompt("Rename scene: ", story.scene_title(e.scene.name), function(t) M.rename(e, t) end) end end)
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
