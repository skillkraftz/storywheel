-- Where the writer was in each story (open scenes, cursor, toggles), kept under Neovim's own state folder
-- (~/.storywheel/nvim/state/...), plus small preferences (like whether Ctrl+I works in this terminal).
local util = require("sw.util")
local story = require("sw.story")
local M = {}

local function dir()
  return vim.fn.stdpath("state") .. "/sw"
end

function M.path()
  return string.format("%s/%s__%s.json", dir(), story.universe or "none", story.slug or "none")
end

local function prefs_path()
  return dir() .. "/prefs.json"
end

function M.pref(key)
  return (util.json_read(prefs_path(), {}))[key]
end

function M.set_pref(key, value)
  local p = util.json_read(prefs_path(), {})
  p[key] = value
  util.json_write(prefs_path(), p)
end

function M.load()
  return util.json_read(M.path(), { cursors = {}, open = {} })
end

-- Remember: the current scene, the cursor in every scene visited, the open scenes, and the toggles.
function M.save(extra)
  if not story.dir then return end
  local data = M.load()
  data.cursors = data.cursors or {}
  local buf = vim.api.nvim_get_current_buf()
  local name = vim.api.nvim_buf_get_name(buf)
  if name:find(story.manuscript or "\0", 1, true) then
    local cur = vim.api.nvim_win_get_cursor(0)
    data.cursors[name] = { cur[1], cur[2] }
    data.current = name
  end
  data.open = {}
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    local n = vim.api.nvim_buf_get_name(b)
    if vim.api.nvim_buf_is_loaded(b) and n:find(story.manuscript or "\0", 1, true) then data.open[#data.open + 1] = n end
  end
  for k, v in pairs(extra or {}) do data[k] = v end
  util.json_write(M.path(), data)
  return data
end

return M
