-- Word counts for the status line, and stats.json (words per day and per session).
local util = require("sw.util")
local story = require("sw.story")
local M = {}

M.cache = {}            -- path -> { mtime=, words= } for scenes that are not open
M.start_total = 0
M.day_base = 0
M.session_start = os.date("%Y-%m-%dT%H:%M:%S")
M.session_id = M.session_start .. "#" .. tostring(vim.fn.getpid())
M.total_cached = 0
M.scene_cached = 0
M.timer = nil

local function path_words(path)
  local st = vim.uv.fs_stat(path)
  if not st then return 0 end
  local c = M.cache[path]
  if c and c.mtime == st.mtime.sec then return c.words end
  local words = util.count_words(util.read(path) or "")
  M.cache[path] = { mtime = st.mtime.sec, words = words }
  return words
end

local function buffer_words(buf)
  return util.count_words(table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n"))
end

-- Words in the whole manuscript (open buffers count as they are now, others as saved on disk).
function M.manuscript()
  local total = 0
  for _, s in ipairs(story.files()) do
    local b = vim.fn.bufnr(s.path)
    if b ~= -1 and vim.api.nvim_buf_is_loaded(b) then total = total + buffer_words(b) else total = total + path_words(s.path) end
  end
  return total
end

-- Words in the scene the cursor is in (a scene runs from one marker line to the next).
function M.scene(buf)
  buf = buf or vim.api.nvim_get_current_buf()
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local win = vim.fn.bufwinid(buf)
  local row = (win ~= -1) and vim.api.nvim_win_get_cursor(win)[1] or 1
  for _, sc in ipairs(util.parse_scenes(lines)) do
    if row >= sc.start and row <= sc.finish then return sc.words end
  end
  return buffer_words(buf)
end

function M.today()
  return M.day_base + math.max(0, M.manuscript() - M.start_total)
end

function M.stats_path()
  return story.dir .. "/stats.json"
end

function M.begin()
  if not story.dir then return end
  M.start_total = M.manuscript()
  local data = util.json_read(M.stats_path(), { days = {}, sessions = {} })
  M.day_base = ((data.days or {})[util.today()] or {}).words or 0
end

-- Write stats.json: today's total, and this session's record (the same record is updated, not duplicated).
function M.save()
  if not story.dir then return end
  local data = util.json_read(M.stats_path(), { days = {}, sessions = {} })
  data.days = data.days or {}
  data.sessions = data.sessions or {}
  local today = M.today()
  local day = data.days[util.today()] or {}
  day.words = today
  data.days[util.today()] = day
  local words = math.max(0, M.manuscript() - M.start_total)
  local found = false
  for _, s in ipairs(data.sessions) do
    if s.id == M.session_id then
      s["end"], s.words, s.total = os.date("%Y-%m-%dT%H:%M:%S"), words, M.manuscript()
      found = true
    end
  end
  if not found then
    data.sessions[#data.sessions + 1] = { id = M.session_id, start = M.session_start, ["end"] = os.date("%Y-%m-%dT%H:%M:%S"),
                                          words = words, total = M.manuscript() }
  end
  util.json_write(M.stats_path(), data)
end

local function commas(n)
  local s = tostring(n)
  return (s:reverse():gsub("(%d%d%d)", "%1,"):reverse():gsub("^,", ""))
end

function M.refresh()
  M.scene_cached = M.scene()
  M.total_cached = M.manuscript()
  vim.cmd("redrawstatus")
end

-- The status line: words in the scene, in the story, and written today against the goal (each number says what it is).
function M.line()
  local goal = tonumber(story.setting("daily_goal", 0)) or 0
  local today = math.max(0, M.total_cached - M.start_total) + M.day_base
  local goal_text = goal > 0 and (" of " .. commas(goal)) or ""
  local g = require("sw.grammar").status_text()
  return string.format("  words: in this scene %s · in the story %s · written today %s%s%s", commas(M.scene_cached), commas(M.total_cached),
                       commas(today), goal_text, g ~= "" and ("  ·  " .. g) or "")
end

function M.setup()
  M.begin()
  M.refresh()
  vim.o.statusline = "%{%v:lua.require'sw.stats'.line()%}"
  vim.api.nvim_set_hl(0, "StatusLine", { link = "Comment" })
  vim.api.nvim_set_hl(0, "StatusLineNC", { link = "Comment" })
  local group = vim.api.nvim_create_augroup("sw_stats", { clear = true })
  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI", "BufEnter" }, {
    group = group,
    callback = function()
      if M.timer then M.timer:stop() end
      M.timer = vim.defer_fn(function() M.refresh() end, 150)
    end,
  })
end

return M
