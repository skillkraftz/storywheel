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
  local script = require("sw.script")
  if script.is_script(buf) then
    for _, sc in ipairs(script.scenes(lines)) do
      if row >= sc.start and row <= sc.finish then return sc.words end
    end
    return 0
  end
  for _, sc in ipairs(util.parse_scenes(lines)) do
    if row >= sc.start and row <= sc.finish then return sc.words end
  end
  return buffer_words(buf)
end

-- Pasted text is not writing: with the setting stats_skip_paste (on by default) its words move the starting total, so they never reach today's count.
function M.skip_pasted(lines)
  local v = story.setting("stats_skip_paste", true)
  if v == false or v == "false" or not story.dir then return end
  M.check_day()
  M.start_total = M.start_total + util.count_words(table.concat(lines, "\n"))
end

function M.mine()
  M.check_day()
  return M.day_base + math.max(0, M.manuscript() - M.start_total)
end

function M.today()
  return (M.others or 0) + M.mine()
end

function M.stats_path()
  return story.dir .. "/stats.json"
end

M.host = (vim.uv.os_gethostname and vim.uv.os_gethostname()) or "this-machine"
M.day = nil              -- the date the counts below belong to

-- Per-machine words of a day: old files have a single `words`, which is kept as the "(earlier)" machine.
local function machines_of(day)
  local m = {}
  for k, v in pairs(day.machines or {}) do m[k] = tonumber(v) or 0 end
  if next(m) == nil and tonumber(day.words) then m["(earlier)"] = tonumber(day.words) end
  return m
end

local function sum_others(m)
  local n = 0
  for k, v in pairs(m) do if k ~= M.host then n = n + v end end
  return n
end

function M.begin()
  if not story.dir then return end
  M.day = util.today()
  M.start_total = M.manuscript()
  local data = util.json_read(M.stats_path(), { days = {}, sessions = {} })
  local m = machines_of((data.days or {})[M.day] or {})
  M.day_base = m[M.host] or 0           -- what this machine already wrote today
  M.others = sum_others(m)              -- what other machines wrote today (counted in the display, never rewritten)
end

-- A new day started while the Writer stayed open: save the old day's count under its own date, then start the new day from scratch.
function M.check_day()
  if M.day and M.day ~= util.today() then
    M.save()
    M.begin()
  end
end

-- Write stats.json: today's total, and this session's record (the same record is updated, not duplicated).
function M.save()
  if not story.dir then return end
  local data = util.json_read(M.stats_path(), { days = {}, sessions = {} })
  data.days = data.days or {}
  data.sessions = data.sessions or {}
  local date = M.day or util.today()
  local day = data.days[date] or {}
  local m = machines_of(day)
  m[M.host] = M.day_base + math.max(0, M.manuscript() - M.start_total)
  day.machines = m
  local total = 0
  for _, v in pairs(m) do total = total + v end
  day.words = total                     -- (the sum, for readers that only know `words`)
  data.days[date] = day
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
  local buf = vim.api.nvim_get_current_buf()
  local script = require("sw.script")
  M.pages_cached = script.is_script(buf) and script.status(buf) or nil
  vim.cmd("redrawstatus")
end

-- The status line: words in the scene, in the story, and written today against the goal as "312 / 1,000 words · 31%" (each number says what it is).
function M.line()
  local goal = tonumber(story.setting("daily_goal", 0)) or 0
  M.check_day()
  local today = (M.others or 0) + math.max(0, M.total_cached - M.start_total) + M.day_base
  local today_text
  if goal > 0 then
    today_text = string.format("today %s / %s words · %d%%", commas(today), commas(goal), math.floor(100 * today / goal + 0.5))
  else
    today_text = string.format("today %s words", commas(today))
  end
  local g = require("sw.grammar").status_text()
  local target = M.pages_cached == nil and tonumber((story.info or {}).target_words) or 0       -- (prose: the story's target length, from the story form)
  local total = commas(M.total_cached)
  if target and target > 0 then
    total = string.format("%s / %s words · %d%%", total, commas(target), math.floor(100 * M.total_cached / target + 0.5))
  end
  return string.format("  %swords: in this scene %s · in the story %s · %s%s", M.pages_cached and (M.pages_cached .. "  ·  ") or "",
                       commas(M.scene_cached), total, today_text, g ~= "" and ("  ·  " .. g) or "")
end

-- (a statusline expression is read as a statusline: its % signs must be doubled)
function M.statusline()
  return (M.line():gsub("%%", "%%%%"))
end

function M.setup()
  M.begin()
  M.refresh()
  vim.o.statusline = "%{%v:lua.require'sw.stats'.statusline()%}"
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
