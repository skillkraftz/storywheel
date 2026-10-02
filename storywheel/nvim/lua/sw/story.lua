-- The story being written: its folder, details from the CLI (settings, universe), and its scene files.
local util = require("sw.util")
local M = {}

M.dir = nil
M.slug = nil
M.universe = nil
M.info = { settings = {}, title = "", author = {} }

function M.setup()
  M.dir = os.getenv("STORYWHEEL_STORY_DIR")
  M.slug = os.getenv("STORYWHEEL_STORY")
  M.universe = os.getenv("STORYWHEEL_UNIVERSE")
  M.manuscript = M.dir and (M.dir .. "/manuscript") or nil
  M.reload()
end

-- (Re)read the story's details and settings through the CLI: `storywheel story show UNIVERSE/STORY --json`.
function M.reload()
  if not M.dir or not M.universe then return end
  local data = util.cli_json({ "story", "show", M.universe .. "/" .. M.slug, "--json" })
  if data then M.info = data end
end

function M.settings()
  return M.info.settings or {}
end

function M.setting(key, default)
  local v = M.settings()[key]
  if v == nil then return default end
  return v
end

-- Scene files in order: { { path=, name= }, ... }
function M.scenes()
  local out = {}
  if not M.manuscript then return out end
  for _, name in ipairs(vim.fn.readdir(M.manuscript)) do
    if name:match("%.md$") then out[#out + 1] = { path = M.manuscript .. "/" .. name, name = name } end
  end
  table.sort(out, function(a, b) return a.name < b.name end)
  return out
end

function M.ensure_first_scene()
  if not M.manuscript then return end
  util.mkdir(M.manuscript)
  if #M.scenes() == 0 then util.write(M.manuscript .. "/01-opening.md", "") end
end

-- "03-the-letter.md" -> "The letter"
function M.scene_title(name)
  local t = name:gsub("%.md$", ""):gsub("^%d+%-", ""):gsub("%-", " ")
  return (t:gsub("^%l", string.upper))
end

local function slugify(text)
  local s = text:lower():gsub("'", ""):gsub("[^%w]+", "-"):gsub("^%-+", ""):gsub("%-+$", "")
  if s == "" then s = "scene" end
  return s:sub(1, 50)
end
M.slugify = slugify

-- A new scene file after the last one. Returns its path.
function M.add_scene(title)
  util.mkdir(M.manuscript)
  local last = 0
  for _, s in ipairs(M.scenes()) do
    local n = tonumber(s.name:match("^(%d+)%-")) or 0
    if n > last then last = n end
  end
  local path = string.format("%s/%02d-%s.md", M.manuscript, last + 1, slugify(title or "scene"))
  util.write(path, "")
  return path
end

function M.first_line(path)
  local f = io.open(path, "r")
  if not f then return "" end
  for line in f:lines() do
    if line:match("%S") then f:close() return line end
  end
  f:close()
  return ""
end

return M
