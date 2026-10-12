-- Versions of this story (F12 menu, or the versions key): the same story written in another format (a short story and a screenplay) in the
-- same universe. A small list shows each version's title, format and status; Enter saves everything here and opens the chosen one in the Writer.
local util = require("sw.util")
local story = require("sw.story")
local M = {}

local FORMATS = { ["flash"] = "flash fiction", ["short-story"] = "short story", ["novel"] = "novel", ["feature-film"] = "feature film", ["short-film"] = "short film" }

local function say(text)
  vim.api.nvim_echo({ { text, "Normal" } }, true, {})
end

local function close()
  if M.win and vim.api.nvim_win_is_valid(M.win) then vim.api.nvim_win_close(M.win, true) end
  M.win = nil
  local layout = require("sw.layout")
  if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
end

local function leave()
  close()
  require("sw.notepad").insert(true)
end

-- The story's versions from the CLI: { { id=, title=, format_key=, status= }, ... }, the story itself included; empty when it has none.
function M.fetch()
  local data = util.cli_json({ "story", "show", story.universe .. "/" .. story.slug, "--json" })
  return data and data.versions or {}
end

function M.label(v)
  local mark = v.id == story.slug and "  (this one)" or ""
  return string.format(" %-34s %-14s %-10s%s ", v.title, FORMATS[v.format_key] or v.format_key or "", v.status or "", mark)
end

-- Open version `v` in the Writer: everything is saved first, then the Writer is left and started again on the other story.
function M.switch(v)
  if v.id == story.slug then
    leave()
    say("You are already in this version.")
    return false
  end
  close()
  return require("sw").leave("writer", { universe = story.universe, story = v.id })
end

function M.open(rows)
  rows = rows or M.fetch()
  if #rows < 2 then
    say("This story has no other versions. Make one in the Builder (V on the story).")
    return false
  end
  local lines, width = {}, 0
  for _, v in ipairs(rows) do
    lines[#lines + 1] = M.label(v)
    width = math.max(width, vim.fn.strdisplaywidth(lines[#lines]))
  end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  vim.bo[buf].bufhidden = "wipe"
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 2, col = math.max(0, math.floor((vim.o.columns - width) / 2)), width = width + 1, height = #lines, style = "minimal",
    border = "rounded", title = " Versions of " .. (story.info.title or "this story") .. " ", title_pos = "center",
    footer = " Enter open · j/k move · Esc close ", footer_pos = "center",
  })
  vim.wo[win].cursorline = true
  M.win, M.rows = win, rows
  for i, v in ipairs(rows) do
    if v.id == story.slug then vim.api.nvim_win_set_cursor(win, { i, 0 }) end
  end
  vim.cmd("stopinsert")
  local function current() return rows[vim.api.nvim_win_get_cursor(win)[1]] end
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<CR>", function() M.switch(current()) end)
  map("<2-LeftMouse>", function() M.switch(current()) end)
  map("<Esc>", leave)
  map("q", leave)
  map("j", "j")
  map("k", "k")
  map("<Down>", "j")
  map("<Up>", "k")
  return win
end

return M
