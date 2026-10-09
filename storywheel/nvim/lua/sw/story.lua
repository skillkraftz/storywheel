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

-- What this story is written as, in words ("short story", "feature film"): the status line and the window title say which version you are in.
local FORMAT_NAMES = { ["flash"] = "flash fiction", ["short-story"] = "short story", ["novel"] = "novel", ["feature-film"] = "feature film", ["short-film"] = "short film" }
function M.format_name()
  return FORMAT_NAMES[(M.info or {}).format_key or "short-story"] or "short story"
end

-- "Title (format)": the title with its format, as the status line and the window title show it.
function M.title_with_format(title)
  title = vim.trim(title or "")
  return title ~= "" and (title .. " (" .. M.format_name() .. ")") or ""
end

function M.settings()
  return M.info.settings or {}
end

function M.setting(key, default)
  local v = M.settings()[key]
  if v == nil then return default end
  return v
end

-- Manuscript files in order: { { path=, name= }, ... } (one for a short story, one per chapter for a novel). Only files storywheel makes
-- count: manuscript.md and NN-name.md. Anything else in the folder (a copy another tool made) is not part of the manuscript.
local function known(name)
  return name:match("^manuscript%.md$") ~= nil or name:match("^%d+%-[a-z0-9%-]+%.md$") ~= nil
end

-- A screenplay is one Fountain file, manuscript/script.fountain.
function M.is_screenplay()
  return M.settings().format == "screenplay"
end

function M.scenes()
  local out = {}
  if not M.manuscript then return out end
  if M.is_screenplay() then
    local p = M.manuscript .. "/script.fountain"
    if util.exists(p) then out[1] = { path = p, name = "script.fountain" } end
    return out
  end
  for _, name in ipairs(vim.fn.readdir(M.manuscript)) do
    if known(name) then out[#out + 1] = { path = M.manuscript .. "/" .. name, name = name } end
  end
  table.sort(out, function(a, b) return a.name < b.name end)
  if M.settings().format ~= "novel" then                           -- a short story with manuscript.md is that one file
    for _, f in ipairs(out) do
      if f.name == "manuscript.md" then return { f } end
    end
  end
  return out
end

M.files = M.scenes

function M.ensure_first_scene()
  if not M.manuscript then return end
  util.mkdir(M.manuscript)
  if M.is_screenplay() then
    if #M.files() == 0 then
      local made = util.cli_json({ "script", "ensure", M.universe .. "/" .. M.slug, "--json" })
      if not made then util.write(M.manuscript .. "/script.fountain", "Title: " .. (M.info.title or "") .. "\nCredit: Written by\n\nFADE IN:\n\n") end
    end
    return
  end
  if #M.files() == 0 then util.write(M.manuscript .. "/manuscript.md", "") end
end

-- The lines of a file: from its buffer if it is open (unsaved edits count), else from disk.
function M.lines_of(path)
  local b = vim.fn.bufnr(path)
  if b ~= -1 and vim.api.nvim_buf_is_loaded(b) then return vim.api.nvim_buf_get_lines(b, 0, -1, false) end
  return vim.split(util.read(path) or "", "\n", { plain = true })
end

-- Every scene of the manuscript in order, across all the files:
-- { n=, path=, name=, start=, finish=, label=, title=, marked=, first_line=, words=, body= }
function M.scene_list()
  local out = {}
  if M.is_screenplay() then
    for _, f in ipairs(M.files()) do
      for _, sc in ipairs(require("sw.script").scenes(M.lines_of(f.path))) do
        sc.path, sc.name = f.path, f.name
        out[#out + 1] = sc
      end
    end
    return out
  end
  for _, f in ipairs(M.files()) do
    for _, sc in ipairs(util.parse_scenes(M.lines_of(f.path))) do
      sc.n, sc.path, sc.name = #out + 1, f.path, f.name
      sc.title = (sc.label ~= "" and sc.label) or ((sc.n == 1 and not sc.marked) and "Opening") or ("Scene " .. sc.n)
      out[#out + 1] = sc
    end
  end
  return out
end

-- The scene the cursor is in (a scene from scene_list(), or nil).
function M.scene_at(path, row)
  for _, sc in ipairs(M.scene_list()) do
    if sc.path == path and row >= sc.start and row <= sc.finish then return sc end
  end
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

-- A new scene at the end of the manuscript: a marker line in the last file. Returns path, line of the marker.
function M.add_scene(title)
  M.ensure_first_scene()
  local files = M.files()
  local path = files[#files].path
  local b = util.load_buffer(path)
  local lines = vim.api.nvim_buf_get_lines(b, 0, -1, false)
  while #lines > 0 and lines[#lines] == "" do table.remove(lines) end
  if #lines > 0 then lines[#lines + 1] = "" end
  if M.is_screenplay() then                                       -- a script's scene is a scene heading
    local head = ((title and title ~= "") and title or "INT. NEW SCENE - DAY")
    if not require("sw.script").is_heading(head) then head = "." .. head end
    lines[#lines + 1] = head:upper()
    local at = #lines
    lines[#lines + 1] = ""
    lines[#lines + 1] = ""
    vim.api.nvim_buf_set_lines(b, 0, -1, false, lines)
    vim.api.nvim_buf_call(b, function() vim.cmd("silent! write") end)
    return path, at
  end
  lines[#lines + 1] = ("* * * " .. (title or "")):gsub("%s+$", "")
  local marker_line = #lines
  lines[#lines + 1] = ""
  vim.api.nvim_buf_set_lines(b, 0, -1, false, lines)
  vim.api.nvim_buf_call(b, function() vim.cmd("silent! write") end)
  return path, marker_line
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
