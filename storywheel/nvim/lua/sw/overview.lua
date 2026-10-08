-- Ctrl+O: a floating, read-only overlay with the story's outline at a glance: title, premise, the beats of its structure, twist, protagonist,
-- setting and rumor. Scrollable; Escape (or Ctrl+O again, or q) closes it. Built from `storywheel story show` (story.info) and the entity list.
local story = require("sw.story")
local util = require("sw.util")
local M = {}

local function plain(text)
  return ((text or ""):gsub("%*%*", ""):gsub("__", ""))
end

-- A beat stored as "**Label.** Body": the label stays unless the sentence already starts with it (older Story Spine outlines store
-- "**Once upon a time.** Once upon a time, Ann ..."): the same rule as outline.beat_label in Python.
local function without_doubled_label(para)
  local label, body = para:match("^%*%*(.-)%*%*%s*(.*)$")
  if not label then return para end
  local bare = label:gsub("%.$", ""):lower()
  if bare ~= "" and body:lower():sub(1, #bare) == bare then return body end
  return para
end

local function paragraphs(text)
  local out = {}
  for _, para in ipairs(vim.split(text or "", "\n%s*\n")) do
    para = vim.trim(para:gsub("%s*\n%s*", " "))
    if para ~= "" then out[#out + 1] = plain(without_doubled_label(para)) end
  end
  return out
end

local function section(lines, title, body)
  if body and body ~= "" then
    if #lines > 0 then lines[#lines + 1] = "" end
    lines[#lines + 1] = title
    lines[#lines + 1] = string.rep("─", #title)
    for _, l in ipairs(vim.split(body, "\n", { plain = true })) do lines[#lines + 1] = l end
  end
end

-- The lines of the overlay, as a list of strings.
function M.lines()
  local info = story.info or {}
  local meta, outline = info.meta or {}, info.outline or {}
  local lines = {}
  local title = plain(meta.title ~= nil and meta.title or info.title or "")
  lines[#lines + 1] = title ~= "" and title or "(untitled)"
  local sub = {}
  for _, k in ipairs({ "genre", "mood" }) do if meta[k] and meta[k] ~= "" then sub[#sub + 1] = meta[k] end end
  if meta.structure and meta.structure ~= "" then sub[#sub + 1] = meta.structure end
  if #sub > 0 then lines[#lines + 1] = table.concat(sub, " · ") end
  section(lines, "Premise", plain(outline["Premise"] or ""))
  local beats = meta.structure and outline[meta.structure]
  if beats then
    local rows = {}
    for i, p in ipairs(paragraphs(beats)) do rows[#rows + 1] = string.format("%d. %s", i, p) end
    section(lines, meta.structure, table.concat(rows, "\n"))
  end
  section(lines, "Twist", plain(outline["Twist"] or ""))
  -- the protagonist: the character whose role is protagonist
  local world = require("sw.world")
  for _, e in ipairs(world.entities or {}) do
    local f = e.fields or {}
    if e.type == "character" and tostring(f.role or ""):lower() == "protagonist" then
      local rows = { e.name }
      local labels = e.labels or {}
      for _, k in ipairs({ "age", "job", "trait", "want", "need", "flaw", "secret", "rival" }) do
        local v = f[k]
        if type(v) == "table" then v = table.concat(v, ", ") end
        v = (e.display or {})[k] or v
        if v and v ~= "" then rows[#rows + 1] = string.format("%s: %s", labels[k] or (k:sub(1, 1):upper() .. k:sub(2)), v) end
      end
      section(lines, "Protagonist", table.concat(rows, "\n"))
      break
    end
  end
  -- the setting, and the rumor from it
  local setting, rumor = {}, nil
  for _, l in ipairs(vim.split(outline["Setting"] or "", "\n", { plain = true })) do
    local k, v = l:match("^%s*%-%s*%*%*(.-):%*%*%s*(.*)$")
    if k then
      if k:lower() == "rumor" then rumor = v else setting[#setting + 1] = string.format("%s: %s", k, plain(v)) end
    end
  end
  section(lines, "Setting", table.concat(setting, "\n"))
  section(lines, "Rumor", rumor and plain(rumor) or nil)
  if #lines <= 2 then lines[#lines + 1] = ""; lines[#lines + 1] = "This story has no outline yet: it was started without a Wheel draft." end
  return lines
end

function M.is_open()
  return M.win ~= nil and vim.api.nvim_win_is_valid(M.win)
end

function M.close()
  if M.is_open() then vim.api.nvim_win_close(M.win, true) end
  M.win = nil
  local layout = require("sw.layout")
  if layout.main and vim.api.nvim_win_is_valid(layout.main) then
    vim.api.nvim_set_current_win(layout.main)
    require("sw.notepad").insert(true)
  end
end

function M.toggle()
  if M.is_open() then return M.close() end
  return M.open()
end

function M.open()
  local lines = M.lines()
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  local width = math.min(92, math.max(30, vim.o.columns - 8))
  local height = math.min(math.max(#lines, 3), math.max(5, vim.o.lines - 6))
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 2, col = math.floor((vim.o.columns - width) / 2), width = width, height = height,
    style = "minimal", border = "rounded", title = " Story outline · Esc closes ", title_pos = "center",
  })
  vim.wo[win].wrap = true
  vim.wo[win].linebreak = true
  vim.cmd("stopinsert")
  for _, r in ipairs({ 1, 2 }) do
    pcall(vim.api.nvim_buf_add_highlight, buf, -1, r == 1 and "Title" or "Comment", r - 1, 0, -1)
  end
  for i, l in ipairs(lines) do                                   -- the underlined section titles
    if l:match("^─+$") and i > 1 then pcall(vim.api.nvim_buf_add_highlight, buf, -1, "Title", i - 2, 0, -1) end
  end
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<Esc>", M.close)
  map("q", M.close)
  map(story.setting("key_overview", "<C-o>"), M.close)
  M.win, M.buf = win, buf
  return win
end

return M
