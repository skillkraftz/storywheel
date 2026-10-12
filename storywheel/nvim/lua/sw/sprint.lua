-- Writing sprints: a set number of minutes (and, if you like, a word target). The status line shows the time left and the words written
-- since it began; at the end one quiet line says how it went, and the sprint is added to the story's stats.json. No sounds, no pop-ups.
local util = require("sw.util")
local story = require("sw.story")
local stats = require("sw.stats")
local M = {}

M.active = nil          -- { t0 = clock seconds, minutes =, target = (words or nil), base = manuscript words at the start, started = "ISO time" }
M.timer = nil
M.last = nil            -- the record of the sprint that ended last

-- Seconds on a steady clock. (Tests replace it to move time along.)
function M.clock() return vim.uv.hrtime() / 1e9 end

local function say(text)
  vim.api.nvim_echo({ { text, "Normal" } }, true, {})                  -- (kept in :messages too)
end

local function stop_timer()
  if M.timer then
    M.timer:stop()
    if not M.timer:is_closing() then M.timer:close() end
    M.timer = nil
  end
end

-- Words written since the sprint began (pasted text moves the base, as it does for the day's count; deleting never goes below 0).
function M.words(exact)
  if not M.active then return 0 end
  local now = exact and stats.manuscript() or stats.total_cached
  return math.max(0, now - M.active.base)
end

function M.adjust(n)
  if M.active then M.active.base = M.active.base + n end
end

function M.seconds_left()
  if not M.active then return 0 end
  return math.max(0, math.ceil(M.active.minutes * 60 - (M.clock() - M.active.t0)))
end

-- "sprint 12:03 left · 240 / 500 words ✓", or "" when no sprint is running. Part of the status line.
function M.status_text()
  local a = M.active
  if not a then return "" end
  local left = M.seconds_left()
  local words = M.words()
  local w = a.target and string.format("%d / %d words%s", words, a.target, words >= a.target and " ✓" or "") or string.format("%d words", words)
  return string.format("sprint %d:%02d left · %s", math.floor(left / 60), left % 60, w)
end

local function tick()
  if not M.active then return stop_timer() end
  if M.seconds_left() <= 0 then
    M.finish("done")
  else
    vim.cmd("redrawstatus")
  end
end

-- Start a sprint of `minutes` (and an optional word target). Returns false and says why when it can't.
function M.start(minutes, target)
  if M.active then
    say("A sprint is already running (" .. M.status_text() .. ").")
    return false
  end
  minutes = tonumber(minutes)
  if not minutes or minutes < 1 or minutes > 600 then
    say("A sprint is 1 to 600 minutes.")
    return false
  end
  target = tonumber(target)
  if target and target < 1 then target = nil end
  stats.refresh()
  M.active = { t0 = M.clock(), minutes = minutes, target = target and math.floor(target) or nil, base = stats.manuscript(),
               started = os.date("%Y-%m-%dT%H:%M:%S") }
  stop_timer()
  M.timer = vim.uv.new_timer()
  M.timer:start(1000, 1000, vim.schedule_wrap(tick))
  vim.cmd("redrawstatus")
  say(string.format("Sprint started: %d minutes%s. Press the sprint key again to stop it early.", minutes,
                    M.active.target and (", aiming for " .. M.active.target .. " words") or ""))
  return true
end

-- End the sprint ("done": the time ran out; "stopped": you stopped it; "left": the Writer was closed). Records it and says one line.
function M.finish(reason)
  local a = M.active
  if not a then return nil end
  local planned = a.minutes * 60
  local elapsed = reason == "done" and planned or math.min(planned, math.max(0, M.clock() - a.t0))
  local words = M.words(true)
  M.active = nil
  stop_timer()
  vim.cmd("redrawstatus")
  if reason ~= "done" and elapsed < 10 and words == 0 then
    if reason == "stopped" then say("Sprint cancelled.") end
    return nil
  end
  local minutes = elapsed / 60
  local rec = { start = a.started, ["end"] = os.date("%Y-%m-%dT%H:%M:%S"), minutes = a.minutes, actual_minutes = math.floor(minutes * 10 + 0.5) / 10,
                words = words, wpm = minutes > 0 and math.floor(words / minutes * 10 + 0.5) / 10 or 0, early = reason ~= "done" or nil,
                reason = reason }
  if a.target then
    rec.target, rec.hit = a.target, words >= a.target
  end
  M.last = rec
  M.record(rec)
  local line = string.format("Sprint %s: %d words in %s (%s a minute)", reason == "done" and "done" or "stopped", words,
                             reason == "done" and (a.minutes .. " minutes") or string.format("%.1f minutes", minutes), string.format("%.1f", rec.wpm))
  if a.target then line = line .. (rec.hit and string.format(" · reached the %d-word target", a.target) or string.format(" · short of the %d-word target", a.target)) end
  if reason ~= "left" then say(line) end
  return rec
end

-- Add the record to the story's stats.json (next to its days and sessions).
function M.record(rec)
  if not story.dir then return end
  local data = util.json_read(story.dir .. "/stats.json", { days = {}, sessions = {} })
  data.sprints = data.sprints or {}
  data.sprints[#data.sprints + 1] = rec
  util.json_write(story.dir .. "/stats.json", data)
end

-- The key and the menu entry: start one (asking how long, and for an optional target), or stop the one that is running.
function M.ask()
  if M.active then
    M.finish("stopped")
    return
  end
  local default = tonumber(story.setting("sprint_minutes", 25)) or 25
  vim.ui.input({ prompt = string.format("Sprint minutes (Enter for %d): ", default) }, function(text)
    if text == nil then return end
    local minutes = default
    if vim.trim(text) ~= "" then
      minutes = tonumber(vim.trim(text))
      if not minutes or minutes < 1 or minutes > 600 then
        say("A sprint is 1 to 600 minutes.")
        return
      end
    end
    vim.ui.input({ prompt = "Word target (optional, Enter for none): " }, function(t2)
      if t2 == nil then return end
      t2 = vim.trim(t2)
      local target = nil
      if t2 ~= "" then
        target = tonumber(t2)
        if not target or target < 1 then
          say("A word target is a number of words, or leave it empty.")
          return
        end
      end
      M.start(minutes, target)
    end)
  end)
end

function M.menu_label()
  if M.active then return "Stop the writing sprint (" .. M.status_text() .. ")" end
  return "Start a writing sprint…"
end

return M
