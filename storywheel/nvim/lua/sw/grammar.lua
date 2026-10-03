-- Optional grammar checking with a LOCAL LanguageTool server (storywheel/grammar.py starts and stops it). Off unless turned on.
--
-- Each paragraph (one line) is sent on its own, only when it changed since it was last checked, a moment after you stop typing. The
-- markdown markup (* for italics and bold) is taken out before sending, and the answer is mapped back onto the original line, so the
-- underlines land on the right letters. Problems get their own underline colour (SwGrammar), distinct from spelling. Results are
-- remembered per story (.grammar-cache.json) so a paragraph is checked once.
local util = require("sw.util")
local story = require("sw.story")
local M = {}

M.ns = vim.api.nvim_create_namespace("sw_grammar")
M.enabled = false
M.state = "off"             -- off | starting | ready | error
M.message = ""              -- why it is in error
M.cfg = nil
M.cache = { sig = "", clean = {}, found = {} }
M.queue, M.busy, M.timer = {}, false, nil
M.ignored = {}              -- { { rule =, text = }, ... } for this story
M.off_rules = {}            -- rule ids turned off in this session (also saved in Settings)
M.started = false           -- did we start a server (so we stop it)

vim.api.nvim_set_hl(0, "SwGrammar", { undercurl = true, sp = "#e0a030", default = true })

local function hash(line) return vim.fn.sha256(line) end

local function cache_path() return story.dir and (story.dir .. "/.grammar-cache.json") or nil end
local function ignore_path() return story.dir and (story.dir .. "/grammar-ignore.json") or nil end

-- --- taking the markup out, keeping the offsets ------------------------------------------------------------------------------------

-- A scene break (*** , * * * , #) or an empty line holds no prose.
function M.is_prose(line)
  if line:match("^%s*$") then return false end
  if util.marker_label(line) ~= nil then return false end
  return line:find("%a") ~= nil
end

-- plain text without the * markup, and two tables for LanguageTool's offsets (UTF-16 code units, 0-based): start[u] is the byte where the
-- character holding unit u begins, stop[u] the byte after it (both 0-based into the original line).
function M.strip(line)
  local plain, start, stop = {}, {}, {}
  local u = 0
  local positions = vim.str_utf_pos(line)
  for i, b in ipairs(positions) do
    local nxt = positions[i + 1] or (#line + 1)
    local ch = line:sub(b, nxt - 1)
    if ch ~= "*" then
      plain[#plain + 1] = ch
      local units = (vim.fn.char2nr(ch) > 0xFFFF) and 2 or 1
      for k = 0, units - 1 do
        start[u + k], stop[u + k] = b - 1, nxt - 1
      end
      u = u + units
    end
  end
  return table.concat(plain), start, stop, u
end

-- LanguageTool's matches for `plain` -> matches on the original line (byte columns, 0-based, end exclusive).
function M.map_matches(line, raw, start, stop, units)
  local out = {}
  for _, m in ipairs(raw or {}) do
    local o, len = tonumber(m.offset), tonumber(m.length)
    if o and len and len > 0 and o >= 0 and o + len <= units and start[o] and stop[o + len - 1] then
      local reps = {}
      for _, r in ipairs(m.replacements or {}) do
        if r.value and #reps < 5 then reps[#reps + 1] = r.value end
      end
      local rule = m.rule or {}
      out[#out + 1] = {
        scol = start[o], ecol = stop[o + len - 1], message = m.message or (rule.description or "Grammar problem"),
        rule = rule.id or "?", category = (rule.category or {}).id or "", replacements = reps,
        text = line:sub(start[o] + 1, stop[o + len - 1]),
      }
    end
  end
  return out
end

-- --- the cache, ignored items, rules -------------------------------------------------------------------------------------------------

function M.signature()
  local c = M.cfg or {}
  return table.concat({ c.language or "", c.disabledCategories or "", c.disabledRules or "" }, "|")
end

function M.load_cache()
  local p = cache_path()
  local data = p and util.json_read(p, nil)
  if type(data) == "table" and data.sig == M.signature() then
    M.cache = { sig = data.sig, clean = data.clean or {}, found = data.found or {} }
  else
    M.cache = { sig = M.signature(), clean = {}, found = {} }
  end
  local ip = ignore_path()
  local list = ip and util.json_read(ip, {}) or {}
  M.ignored = type(list) == "table" and list or {}
end

function M.save_cache()
  local p = cache_path()
  if p then pcall(util.json_write, p, M.cache) end
end

local function is_ignored(m)
  for _, i in ipairs(M.ignored) do
    if i.rule == m.rule and (i.text == nil or i.text == m.text) then return true end
  end
  return M.off_rules[m.rule] == true
end

-- The live problems on a line (cached, minus ignored items and turned-off rules).
function M.line_problems(line)
  local found = M.cache.found[hash(line)]
  if not found then return {} end
  local out = {}
  for _, m in ipairs(found) do
    if not is_ignored(m) then out[#out + 1] = m end
  end
  return out
end

-- --- drawing -------------------------------------------------------------------------------------------------------------------------

function M.buf()
  local layout = require("sw.layout")
  if layout.main and vim.api.nvim_win_is_valid(layout.main) then return vim.api.nvim_win_get_buf(layout.main) end
  return vim.api.nvim_get_current_buf()
end

function M.is_manuscript(buf)
  local name = vim.api.nvim_buf_get_name(buf)
  return story.manuscript ~= nil and name:find(story.manuscript, 1, true) ~= nil
end

function M.render()
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(b) then vim.api.nvim_buf_clear_namespace(b, M.ns, 0, -1) end
  end
  if not M.enabled then return end
  local buf = M.buf()
  if not M.is_manuscript(buf) then return end
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  for row, line in ipairs(lines) do
    for _, m in ipairs(M.line_problems(line)) do
      pcall(vim.api.nvim_buf_set_extmark, buf, M.ns, row - 1, m.scol, { end_row = row - 1, end_col = m.ecol, hl_group = "SwGrammar", priority = 90 })
    end
  end
end

function M.count()
  local n = 0
  local buf = M.buf()
  if not M.is_manuscript(buf) then return 0 end
  for _, line in ipairs(vim.api.nvim_buf_get_lines(buf, 0, -1, false)) do n = n + #M.line_problems(line) end
  return n
end

-- A few words for the status line.
function M.status_text()
  if not M.enabled then return "" end
  if M.state == "starting" then return "grammar: starting…" end
  if M.state == "error" then return "grammar: unavailable (" .. (M.message ~= "" and M.message or "see :SWGrammarStatus") .. ")" end
  local pending = #M.queue + (M.busy and 1 or 0)
  if pending > 0 then return string.format("grammar: checking %d…", pending) end
  local n = M.count()
  return n == 0 and "grammar: no problems" or string.format("grammar: %d problem%s", n, n == 1 and "" or "s")
end

-- --- asking the server -------------------------------------------------------------------------------------------------------------------

function M.request(plain, cb)
  local c = M.cfg
  local cmd = { "curl", "-s", "-S", "--max-time", tostring(M.timeout or 20), "-X", "POST", c.url .. "/v2/check",
    "--data-urlencode", "language=" .. c.language, "--data-urlencode", "text=" .. plain }
  if c.disabledCategories ~= "" then vim.list_extend(cmd, { "--data-urlencode", "disabledCategories=" .. c.disabledCategories }) end
  if c.disabledRules ~= "" then vim.list_extend(cmd, { "--data-urlencode", "disabledRules=" .. c.disabledRules }) end
  local ok, err = pcall(vim.system, cmd, { text = true }, function(res)
    vim.schedule(function()
      if res.code ~= 0 then
        cb(nil, res.code == 28 and "LanguageTool is too slow to answer" or ("the server did not answer" .. ((res.stderr or "") ~= "" and (": " .. res.stderr:gsub("%s+$", "")) or "")))
        return
      end
      local good, data = pcall(vim.json.decode, res.stdout or "")
      if not good or type(data) ~= "table" then cb(nil, "the server's answer was not understood") return end
      cb(data.matches or {})
    end)
  end)
  if not ok then cb(nil, "curl is not installed (sudo apt install curl)") end
end

function M.pump()
  if M.busy or M.state ~= "ready" or not M.enabled then return end
  local item = table.remove(M.queue, 1)
  if not item then M.save_cache() M.render() return end
  M.busy = true
  M.request(item.plain, function(raw, err)
    M.busy = false
    if not M.enabled then return end
    if not raw then
      M.state, M.message = "error", err
      M.queue = {}
      M.retry_at = vim.uv.now() + 15000
      M.render()
      return
    end
    local matches = M.map_matches(item.line, raw, item.start, item.stop, item.units)
    if #matches == 0 then M.cache.clean[item.hash] = true else M.cache.found[item.hash] = matches end
    M.render()
    M.pump()
  end)
end

-- Queue every paragraph of the manuscript buffer that has not been checked (unchanged ones are skipped: they are in the cache).
function M.scan()
  if not M.enabled then return end
  if M.state == "error" and M.retry_at and vim.uv.now() >= M.retry_at then M.state = "ready" end
  if M.state ~= "ready" then return end
  local buf = M.buf()
  if not M.is_manuscript(buf) then return end
  local queued = {}
  for _, it in ipairs(M.queue) do queued[it.hash] = true end
  for _, line in ipairs(vim.api.nvim_buf_get_lines(buf, 0, -1, false)) do
    if M.is_prose(line) then
      local h = hash(line)
      if not M.cache.clean[h] and not M.cache.found[h] and not queued[h] then
        local plain, start, stop, units = M.strip(line)
        if plain:find("%a%a") then
          queued[h] = true
          M.queue[#M.queue + 1] = { hash = h, line = line, plain = plain, start = start, stop = stop, units = units }
        else
          M.cache.clean[h] = true
        end
      end
    end
  end
  M.render()
  M.pump()
end

-- Something was typed: check what changed a moment after typing stops.
function M.touch()
  if not M.enabled then return end
  if M.timer then M.timer:stop() else M.timer = vim.uv.new_timer() end
  M.timer:start((M.cfg and M.cfg.pause_ms) or 1500, 0, vim.schedule_wrap(function() M.scan() end))
end

-- --- turning it on and off --------------------------------------------------------------------------------------------------------------------

local function cli_async(args, cb)
  vim.system(util.cli(args), { text = true }, function(res) vim.schedule(function() cb(res) end) end)
end

function M.set(on, quiet)
  if on == M.enabled then return end
  if not on then
    M.enabled, M.state = false, "off"
    M.queue = {}
    if M.timer then M.timer:stop() end
    M.render()
    M.stop_server()
    if not quiet then vim.api.nvim_echo({ { "Grammar checking off (the server was stopped).", "Normal" } }, false, {}) end
    return
  end
  local cfg, err = util.cli_json({ "grammar", "config" })
  if not cfg then
    vim.api.nvim_echo({ { "Grammar checking could not start: " .. tostring(err), "ErrorMsg" } }, true, {})
    return
  end
  M.cfg = cfg
  M.enabled, M.state, M.message = true, "starting", ""
  M.off_rules = {}
  M.load_cache()
  if not quiet then vim.api.nvim_echo({ { "Starting LanguageTool (this can take a while the first time)…", "Normal" } }, false, {}) end
  cli_async({ "grammar", "start", "--json" }, function(res)
    if not M.enabled then M.stop_server() return end
    local ok, data = pcall(vim.json.decode, res.stdout or "")
    if res.code == 0 and ok and data and data.ok then
      M.started, M.state = true, "ready"
      M.scan()
      if not quiet then vim.api.nvim_echo({ { "Grammar checking is on.", "Normal" } }, false, {}) end
    else
      local msg = vim.trim(res.stdout or "") ~= "" and vim.trim(res.stdout) or vim.trim(res.stderr or "could not start")
      M.state, M.message = "error", msg:gsub("%s+", " "):sub(1, 90)
      vim.api.nvim_echo({ { "Grammar checking: " .. msg, "ErrorMsg" } }, true, {})
    end
  end)
end

function M.stop_server()
  M.started = false
  pcall(function() vim.system(util.cli({ "grammar", "stop", "--json" }), { text = true }):wait(8000) end)
end

function M.toggle() M.set(not M.enabled) end

-- --- finding and handling problems ---------------------------------------------------------------------------------------------------------

function M.problem_at(row, col)        -- row 1-based, col 0-based byte
  local buf = M.buf()
  local line = vim.api.nvim_buf_get_lines(buf, row - 1, row, false)[1]
  if not line then return nil end
  for _, m in ipairs(M.line_problems(line)) do
    if col >= m.scol and col < m.ecol then return vim.tbl_extend("force", m, { row = row }) end
  end
  return nil
end

function M.all()
  local out = {}
  local buf = M.buf()
  if not M.is_manuscript(buf) then return out end
  for row, line in ipairs(vim.api.nvim_buf_get_lines(buf, 0, -1, false)) do
    for _, m in ipairs(M.line_problems(line)) do out[#out + 1] = vim.tbl_extend("force", m, { row = row }) end
  end
  return out
end

function M.next()
  if not M.enabled then
    vim.api.nvim_echo({ { "Grammar checking is off (Writer menu, or Settings > Grammar).", "Normal" } }, false, {})
    return
  end
  local all = M.all()
  if #all == 0 then vim.api.nvim_echo({ { M.status_text(), "Normal" } }, false, {}) return end
  local cur = vim.api.nvim_win_get_cursor(0)
  local pick = all[1]
  for _, m in ipairs(all) do
    if m.row > cur[1] or (m.row == cur[1] and m.scol > cur[2]) then pick = m break end
  end
  vim.api.nvim_win_set_cursor(0, { pick.row, pick.scol })
  vim.api.nvim_echo({ { pick.message .. "  [" .. pick.rule .. "]", "Normal" } }, false, {})
end

function M.apply(m, replacement)
  local buf = M.buf()
  local ok = pcall(vim.api.nvim_buf_set_text, buf, m.row - 1, m.scol, m.row - 1, m.ecol, { replacement })
  if ok then M.touch() end
  return ok
end

function M.ignore(m)
  M.ignored[#M.ignored + 1] = { rule = m.rule, text = m.text }
  local p = ignore_path()
  if p then pcall(util.json_write, p, M.ignored) end
  M.render()
end

function M.turn_off_rule(m)
  M.off_rules[m.rule] = true
  util.cli_json({ "grammar", "rule-off", m.rule, "--json" })
  M.render()
end

-- A small floating menu: the message, then choices. Number keys, arrows and Enter, Esc to close, a click on a choice.
function M.menu(m)
  local items = {}
  for _, r in ipairs(m.replacements or {}) do
    items[#items + 1] = { label = "Replace with “" .. r .. "”", run = function() M.apply(m, r) end }
  end
  items[#items + 1] = { label = "Ignore this one", run = function() M.ignore(m) end }
  items[#items + 1] = { label = "Turn off this rule (" .. m.rule .. ")", run = function() M.turn_off_rule(m) end }
  items[#items + 1] = { label = "Close", run = function() end }
  local lines, first = {}, 0
  local width = 30
  local wrapped = {}
  for _, part in ipairs(vim.split(m.message, "\n", { plain = true })) do
    while #part > 58 do
      local cut = part:sub(1, 58):match("^.*()%s") or 58
      wrapped[#wrapped + 1] = " " .. part:sub(1, cut - 1)
      part = part:sub(cut + 1)
    end
    wrapped[#wrapped + 1] = " " .. part
  end
  for _, l in ipairs(wrapped) do lines[#lines + 1] = l end
  lines[#lines + 1] = ""
  first = #lines + 1
  for i, it in ipairs(items) do lines[#lines + 1] = string.format(" %s  %s", i <= 9 and tostring(i) or " ", it.label) end
  for _, l in ipairs(lines) do width = math.max(width, vim.fn.strdisplaywidth(l) + 1) end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  for r = 1, first - 1 do vim.api.nvim_buf_add_highlight(buf, -1, "Comment", r - 1, 0, -1) end
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "cursor", row = 1, col = 0, width = width, height = #lines, style = "minimal", border = "rounded", title = " Grammar ", title_pos = "center",
  })
  vim.wo[win].cursorline = true
  vim.api.nvim_win_set_cursor(win, { first, 0 })
  vim.cmd("stopinsert")
  local function close()
    if vim.api.nvim_win_is_valid(win) then vim.api.nvim_win_close(win, true) end
    local layout = require("sw.layout")
    if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
  end
  local function run(i)
    close()
    if items[i] then items[i].run() end
    local np = require("sw.notepad")
    if np.enabled then np.insert(true) end
  end
  local function current() return vim.api.nvim_win_get_cursor(win)[1] - first + 1 end
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<CR>", function() run(current()) end)
  map("<Esc>", function() close() local np = require("sw.notepad") if np.enabled then np.insert(true) end end)
  map("q", function() close() local np = require("sw.notepad") if np.enabled then np.insert(true) end end)
  map("<LeftMouse>", function()
    local pos = vim.fn.getmousepos()
    if pos.winid ~= win then close() return end
    local i = pos.line - first + 1
    if items[i] then run(i) end
  end)
  for i = 1, math.min(9, #items) do map(tostring(i), function() run(i) end) end
  map("j", function() local c = current() if c < #items then vim.api.nvim_win_set_cursor(win, { first + c, 0 }) end end)
  map("<Down>", function() local c = current() if c < #items then vim.api.nvim_win_set_cursor(win, { first + c, 0 }) end end)
  map("k", function() local c = current() if c > 1 then vim.api.nvim_win_set_cursor(win, { first + c - 2, 0 }) end end)
  map("<Up>", function() local c = current() if c > 1 then vim.api.nvim_win_set_cursor(win, { first + c - 2, 0 }) end end)
  M.last_menu = { win = win, buf = buf, items = items, lines = lines, first = first }
  return win
end

-- All problems in the story as a list; Enter jumps to one.
function M.list()
  if not M.enabled then
    vim.api.nvim_echo({ { "Grammar checking is off (Writer menu, or Settings > Grammar).", "Normal" } }, false, {})
    return
  end
  local all = M.all()
  local lines = {}
  for _, m in ipairs(all) do lines[#lines + 1] = string.format(" line %-4d %-24s %s", m.row, (("“" .. m.text .. "”"):sub(1, 30)), m.message) end
  local note = M.status_text()
  if #all == 0 then lines = { " " .. note } end
  local width = 40
  for _, l in ipairs(lines) do width = math.max(width, math.min(vim.o.columns - 6, vim.fn.strdisplaywidth(l) + 1)) end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 2, col = math.floor((vim.o.columns - width) / 2), width = width,
    height = math.min(#lines, vim.o.lines - 6), style = "minimal", border = "rounded", title = " Grammar problems: " .. note .. " ", title_pos = "center",
  })
  vim.wo[win].cursorline = true
  vim.cmd("stopinsert")
  local function close()
    if vim.api.nvim_win_is_valid(win) then vim.api.nvim_win_close(win, true) end
    local layout = require("sw.layout")
    if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
  end
  local function go()
    local m = all[vim.api.nvim_win_get_cursor(win)[1]]
    close()
    if m then vim.api.nvim_win_set_cursor(0, { m.row, m.scol }) end
    local np = require("sw.notepad")
    if np.enabled then np.insert(true) end
  end
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<CR>", go)
  map("<Esc>", close)
  map("q", close)
  map("<LeftMouse>", function()
    local pos = vim.fn.getmousepos()
    if pos.winid ~= win then close() return end
    vim.api.nvim_win_set_cursor(win, { math.max(1, pos.line), 0 })
    go()
  end)
  M.last_list = { win = win, buf = buf, lines = lines, all = all, go = go }
  return win
end

-- --- wiring --------------------------------------------------------------------------------------------------------------------------------

function M.map_buffer(buf)
  vim.keymap.set({ "n", "i", "x", "s" }, "<RightMouse>", function()
    local pos = vim.fn.getmousepos()
    local layout = require("sw.layout")
    if M.enabled and layout.main and pos.winid == layout.main then
      local m = M.problem_at(pos.line, math.max(0, pos.column - 1))
      if m then
        vim.api.nvim_win_set_cursor(layout.main, { m.row, m.scol })
        M.menu(m)
        return
      end
    end
    vim.api.nvim_feedkeys(vim.keycode("<RightMouse>"), "n", false)          -- the ordinary right-click menu
  end, { buffer = buf, silent = true })
end

function M.setup(on)
  local group = vim.api.nvim_create_augroup("sw_grammar", { clear = true })
  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI" }, { group = group, callback = function(ev)
    if M.enabled and M.is_manuscript(ev.buf) then M.touch() end
  end })
  vim.api.nvim_create_autocmd({ "BufEnter", "BufReadPost" }, { group = group, callback = function(ev)
    if M.is_manuscript(ev.buf) then
      M.map_buffer(ev.buf)
      if M.enabled then M.render() M.touch() end
    end
  end })
  vim.api.nvim_create_autocmd("VimLeavePre", { group = group, callback = function() if M.started or M.enabled then M.stop_server() end end })
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(b) and M.is_manuscript(b) then M.map_buffer(b) end
  end
  vim.api.nvim_create_user_command("SWGrammar", function() M.toggle() end, {})
  vim.api.nvim_create_user_command("SWGrammarNext", function() M.next() end, {})
  vim.api.nvim_create_user_command("SWGrammarList", function() M.list() end, {})
  local nextkey, listkey = story.setting("key_grammar_next", "<F10>"), story.setting("key_grammar_list", "<S-F10>")
  vim.keymap.set({ "n", "i", "x", "s" }, nextkey, function() M.next() end, { silent = true, desc = "next grammar problem" })
  vim.keymap.set({ "n", "i", "x", "s" }, listkey, function() M.list() end, { silent = true, desc = "grammar problems" })
  if on then M.set(true, true) end
end

return M
