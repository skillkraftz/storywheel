-- Restore from a backup (F12 menu): every backup of this story (rolling copies, and the copies made before a conversion or a restore) with its
-- date, kind and word count. Enter restores one: the version you have now is copied aside first, so a restore can be undone.
local util = require("sw.util")
local story = require("sw.story")
local M = {}

local function close_all()
  for _, w in ipairs({ M.win, M.pwin }) do
    if w and vim.api.nvim_win_is_valid(w) then vim.api.nvim_win_close(w, true) end
  end
  M.win, M.pwin = nil, nil
  local layout = require("sw.layout")
  if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
end

local function leave()
  close_all()
  require("sw.notepad").insert(true)
end

local function target()
  return story.universe .. "/" .. story.slug
end

function M.fetch()
  local data, err = util.cli_json({ "backups", "list", target(), "--json" })
  return data, err
end

function M.show_preview(entry)
  local out = vim.fn.system(util.cli({ "backups", "show", target(), entry.id, "--lines", "12" }))
  local lines = vim.split(out, "\n", { plain = true })
  if lines[#lines] == "" then table.remove(lines) end
  if #lines == 0 then lines = { "(empty)" } end
  local buf = M.pbuf
  vim.bo[buf].modifiable = true
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
end

function M.restore(entry)
  local ok = util.ask_yes(string.format("Restore %s from %s (%s)?\n\nThe version you have now is kept aside first (in .backups/restore-…), so you can undo this.",
    entry.file, entry.when, entry.what))
  if not ok then return false end
  require("sw.backup").save_all()
  local out = vim.fn.system(util.cli({ "backups", "restore", target(), entry.id, "--json" }))
  local good, data = pcall(vim.json.decode, out)
  if vim.v.shell_error ~= 0 or not good then
    vim.api.nvim_echo({ { "Couldn't restore: " .. out, "ErrorMsg" } }, true, {})
    return false
  end
  close_all()
  vim.cmd("silent! checktime")                      -- the buffers read the restored file
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    local name = vim.api.nvim_buf_get_name(b)
    if vim.api.nvim_buf_is_loaded(b) and story.manuscript and name:find(story.manuscript, 1, true) and not vim.bo[b].modified then
      pcall(vim.api.nvim_buf_call, b, function() vim.cmd("silent! edit!") end)
    end
  end
  vim.api.nvim_echo({ { string.format("Restored %s (%d words).%s", data.restored, data.words, data.kept and " The version it replaced is kept in .backups." or ""), "Normal" } }, true, {})
  require("sw.stats").refresh()
  require("sw.notepad").insert(true)
  return true
end

function M.open()
  require("sw.backup").save_all()
  local rows, err = M.fetch()
  if not rows then
    vim.api.nvim_echo({ { "Couldn't list the backups: " .. tostring(err), "ErrorMsg" } }, true, {})
    return false
  end
  if #rows == 0 then
    vim.api.nvim_echo({ { "There are no backups of this story yet (they are made while you write).", "Normal" } }, true, {})
    return false
  end
  local lines = {}
  for _, r in ipairs(rows) do
    lines[#lines + 1] = string.format(" %s   %-32s %-16s %7s words ", r.when, r.what, r.file, tostring(r.words))
  end
  local width = 0
  for _, l in ipairs(lines) do width = math.max(width, vim.fn.strdisplaywidth(l)) end
  local height = math.min(#lines, math.max(4, vim.o.lines - 24))
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  vim.bo[buf].bufhidden = "wipe"
  local col = math.max(0, math.floor((vim.o.columns - width) / 2))
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 2, col = col, width = width + 1, height = height, style = "minimal", border = "rounded",
    title = " Backups of " .. (story.info.title or "this story") .. " ", title_pos = "center",
    footer = " Enter restore · j/k move · Esc close ", footer_pos = "center",
  })
  vim.wo[win].cursorline = true
  M.win = win
  -- the preview, under the list
  local pbuf = vim.api.nvim_create_buf(false, true)
  vim.bo[pbuf].bufhidden = "wipe"
  M.pbuf = pbuf
  local pwin = vim.api.nvim_open_win(pbuf, false, {
    relative = "editor", row = 2 + height + 2, col = col, width = width + 1, height = 13, style = "minimal", border = "rounded",
    title = " What the highlighted backup holds ", title_pos = "center", focusable = false,
  })
  M.pwin = pwin
  vim.cmd("stopinsert")
  local function current() return rows[vim.api.nvim_win_get_cursor(win)[1]] end
  M.show_preview(rows[1])
  vim.api.nvim_create_autocmd("CursorMoved", { buffer = buf, callback = function() local r = current() if r then M.show_preview(r) end end })
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<CR>", function() M.restore(current()) end)
  map("<2-LeftMouse>", function() M.restore(current()) end)
  map("<Esc>", leave)
  map("q", leave)
  map("j", "j")
  map("k", "k")
  map("<Down>", "j")
  map("<Up>", "k")
  M.rows = rows
  return win
end

return M
