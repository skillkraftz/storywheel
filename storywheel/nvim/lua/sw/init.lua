-- The Writer: puts the modules together. Entry point: require("sw").setup() (from the config's init.lua).
local util = require("sw.util")
local story = require("sw.story")
local layout = require("sw.layout")
local prose = require("sw.prose")
local sidebar = require("sw.sidebar")
local world = require("sw.world")
local stats = require("sw.stats")
local backup = require("sw.backup")
local notepad = require("sw.notepad")
local gui = require("sw.gui")
local session = require("sw.session")

local M = {}

-- The help comes from the same files as every other help surface (storywheel/data/help/writer.md, through `storywheel help writer`).
-- This short text is only for when the command line cannot be run.
M.HELP_FALLBACK = {
  "storywheel Writer",
  "",
  "The help could not be loaded. Run  storywheel help writer  in a terminal to read it.",
  "F1 Wheel   F2 Builder   F3 this help   F4 Settings   F5 Words   F12 or Alt+M the Writer menu",
}

function M.help_lines(width)
  local out = vim.fn.system(util.cli({ "help", "writer", "--width", tostring(width or 88) }))
  if vim.v.shell_error ~= 0 or out == "" then return M.HELP_FALLBACK end
  return vim.split(out, "\n", { plain = true })
end

-- --- scenes ---------------------------------------------------------------------------------------------

function M.main_buf()
  return vim.api.nvim_win_get_buf(layout.main)
end

function M.current_scene()
  local name = vim.api.nvim_buf_get_name(M.main_buf())
  if name:find(story.manuscript, 1, true) then return name end
end

-- Open a scene file in the writing window, optionally at {line, col}.
function M.open_scene(path, cursor)
  if not (layout.main and vim.api.nvim_win_is_valid(layout.main)) then return end
  vim.api.nvim_set_current_win(layout.main)
  backup.save_all()
  if vim.api.nvim_buf_get_name(0) ~= path then vim.cmd("silent! edit " .. vim.fn.fnameescape(path)) end
  local buf = vim.api.nvim_get_current_buf()
  prose.prepare_buffer(buf)
  prose.prepare_window(layout.main)
  prose.set_invisibles(prose.invisibles)
  vim.wo[layout.main].spell = prose.spell
  if cursor then
    local last = vim.api.nvim_buf_line_count(buf)
    pcall(vim.api.nvim_win_set_cursor, layout.main, { math.min(cursor[1], last), cursor[2] or 0 })
  end
  if prose.typewriter then vim.cmd("normal! zz") end
  stats.refresh()
  if layout.sidebar_open then sidebar.render() end
end

-- ]] and [[: the next / previous scene (by its marker), across files.
function M.step_scene(direction)
  local list = story.scene_list()
  local path = vim.api.nvim_buf_get_name(M.main_buf())
  local row = vim.api.nvim_win_get_cursor(layout.main)[1]
  for i, sc in ipairs(list) do
    if sc.path == path and row >= sc.start and row <= sc.finish and list[i + direction] then
      session.save()
      local target = list[i + direction]
      return M.open_scene(target.path, { target.body, 0 })
    end
  end
  vim.api.nvim_echo({ { direction > 0 and "This is the last scene." or "This is the first scene.", "Normal" } }, false, {})
end

-- --- leaving ----------------------------------------------------------------------------------------------

-- Save everything, remember where we were, say where to go next, and quit.
function M.leave(where, extra)
  local ok = pcall(backup.save_all)
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(b) and vim.bo[b].modified and vim.bo[b].buftype == "" and vim.api.nvim_buf_get_name(b) ~= "" then
      vim.api.nvim_echo({ { "Couldn't save " .. vim.api.nvim_buf_get_name(b) .. ": staying here.", "ErrorMsg" } }, true, {})
      return false
    end
  end
  backup.snapshot(false)
  stats.save()
  session.save({ sidebar = layout.sidebar_open, invisibles = prose.invisibles, typewriter = prose.typewriter, spell = prose.spell,
                 grammar = require("sw.grammar").enabled })
  local rf = os.getenv("STORYWHEEL_RETURN_FILE")
  if rf and rf ~= "" then
    util.write(rf, where or "")
    if extra then util.write(rf .. ".data", vim.json.encode(extra)) end          -- what the next mode is handed (a word, and where it was)
  end
  vim.cmd("qa!")
  return true
end

-- F5: Words, with the word under the cursor (or the selection) and where it is, so "Use in Writer" can replace it.
-- Quit the whole program (asks first; everything is saved).
function M.quit()
  if util.ask_yes("Quit storywheel?  Everything is saved.") then return M.leave("quit") end
  return false
end

function M.words()
  local data = { universe = story.universe, story = story.slug }
  local word, target = require("sw.lookup").word_at_cursor()
  if word then
    data.word = word
    data.replace = { file = vim.api.nvim_buf_get_name(0), row = target[1], start = target[2], ["end"] = target[3], text = word }
  end
  return M.leave("words", data)
end

-- A word chosen in Words ("Use in Writer") replaces the one it was chosen for, before the first screen. Returns the file and
-- cursor to open at, or nil.
function M.apply_pending_replace()
  local raw = os.getenv("STORYWHEEL_REPLACE")
  if not raw or raw == "" then return nil end
  local ok, r = pcall(vim.json.decode, raw)
  if not ok or type(r) ~= "table" or not r.file or not util.exists(r.file) then return nil end
  local buf = util.load_buffer(r.file)
  local row, s, e = r.row, r.start, r["end"]
  local now = vim.api.nvim_buf_get_text(buf, row, s, row, e, {})[1]
  if now ~= r.text then
    vim.api.nvim_echo({ { "The text changed since you picked the word; nothing replaced.", "WarningMsg" } }, true, {})
    return { r.file, { row + 1, s } }
  end
  vim.api.nvim_buf_set_text(buf, row, s, row, e, { r.new })
  vim.api.nvim_buf_call(buf, function() vim.cmd("silent! write") end)
  vim.api.nvim_echo({ { "Replaced “" .. r.text .. "” with “" .. r.new .. "”.", "Normal" } }, true, {})
  return { r.file, { row + 1, s + #r.new } }
end

-- --- the toggles and commands ---------------------------------------------------------------------------

-- The manuscript as plain text: no markup, scene markers become "#" (a marker at the very start only names the first scene).
function M.plain_text()
  local parts = {}
  for _, f in ipairs(story.files()) do
    local out, started = {}, false
    for _, line in ipairs(story.lines_of(f.path)) do
      if util.marker_label(line) ~= nil then
        if started then out[#out + 1] = "#" end
      else
        if line:match("%S") then started = true end
        if started then out[#out + 1] = line end
      end
    end
    local text = table.concat(out, "\n"):gsub("^%s+", ""):gsub("%s+$", "")
    if text ~= "" then parts[#parts + 1] = text end
  end
  local text = table.concat(parts, "\n\n")
  text = text:gsub("%*%*", ""):gsub("%*", "")
  return text
end

function M.copy_manuscript()
  local text = M.plain_text()
  local ok = pcall(vim.fn.setreg, "+", text)
  local got = ok and vim.fn.getreg("+") or ""
  if ok and got == text then
    vim.api.nvim_echo({ { string.format("Copied the manuscript (%d words) as plain text.", util.count_words(text)), "Normal" } }, false, {})
    return true
  end
  vim.api.nvim_echo({ { "A clipboard tool isn't installed. Copying to the system clipboard needs one. To fix it, run:  sudo apt install xclip   Or export a .txt file instead.", "ErrorMsg" } }, true, {})
  return false
end

function M.export(format, anonymous)
  backup.save_all()
  if story.is_screenplay() and (format == nil or format == "docx") then format = "pdf" end     -- (a script exports as a PDF)
  local args = { "manuscript", "export", story.universe .. "/" .. story.slug, "--format", format or "docx", "--json" }
  if anonymous then args[#args + 1] = "--anonymous" end
  vim.api.nvim_echo({ { "Exporting…", "Normal" } }, false, {})
  local data, err = util.cli_json(args)
  if data and data.path then
    vim.api.nvim_echo({ { "Exported " .. (data.shown or data.path) .. ((data.warnings and #data.warnings > 0) and ("  (" .. table.concat(data.warnings, "; ") .. ")") or ""), "Normal" } }, true, {})
    return data
  end
  vim.api.nvim_echo({ { "Export failed: " .. tostring(err), "ErrorMsg" } }, true, {})
end

function M.show_stats()
  local w = stats.scene()
  vim.api.nvim_echo({ { string.format("scene %d words · manuscript %d · today %d / goal %s", w, stats.manuscript(), stats.today(),
                                      tostring(story.setting("daily_goal", 0))), "Normal" } }, false, {})
end

-- The help's tabs, from `storywheel help writer --tabs`: the guide to this story's format (Screenplay, or Writing prose), Writing basics,
-- Keys, Export. Each tab is {title, lines}.
function M.help_format()
  if story.is_screenplay() then return "screenplay" end
  return (story.info or {}).format_key or "short-story"
end

function M.help_tabs(width)
  local data = util.cli_json({ "help", "writer", "--tabs", "--json", "--width", tostring(width or 88), "--format", M.help_format() })
  if type(data) ~= "table" or #data == 0 then return { { title = "Help", lines = M.HELP_FALLBACK } } end
  local out = {}
  for _, tab in ipairs(data) do
    out[#out + 1] = { title = tab.title, lines = vim.split((tab.text or ""):gsub("\n$", ""), "\n", { plain = true }) }
  end
  return out
end

-- A click on a tab in the help's bar (the winbar's %@ click regions pass the tab number as the first argument).
function _G.SwHelpTab(n)
  require("sw").help_show(tonumber(n))
end

-- The tab bar (the window's winbar). If the titles do not fit the window they are shortened, down to the numbers alone; the open tab's own
-- name is the last to go. The key hints are in the window's footer, not here.
local function help_bar(tabs, current, width)
  local function build(limit)
    local parts, total = {}, 0
    for i, tab in ipairs(tabs) do
      local title = tab.title
      if limit and (i ~= current or limit < 4) and vim.fn.strdisplaywidth(title) > limit then
        title = limit > 0 and (vim.fn.strcharpart(title, 0, math.max(1, limit - 1)) .. "…") or ""
      end
      local text = title ~= "" and string.format(" %d %s ", i, title) or string.format(" %d ", i)
      total = total + vim.fn.strdisplaywidth(text) + 1
      local hl = i == current and "%#TabLineSel#" or "%#TabLine#"
      parts[#parts + 1] = string.format("%s%%%d@v:lua.SwHelpTab@%s%%X", hl, i, (text:gsub("%%", "%%%%")))
    end
    return parts, total
  end
  local limit = nil
  local parts, total = build(limit)
  limit = 0
  for _, t in ipairs(tabs) do limit = math.max(limit, vim.fn.strdisplaywidth(t.title)) end
  while total > (width or 1000) and limit > 0 do
    limit = limit - 1
    parts, total = build(limit)
  end
  return table.concat(parts, "%#TabLineFill# ") .. "%#TabLineFill#"
end

local HELP_HINT = " Tab / Shift+Tab / 1-%d  ·  / search  ·  F3, Esc, q close "

-- A heading in the help text is a line followed by a line of dashes as long as it: show it in the Title colour and leave the dashes out.
local function help_headings(lines)
  local out, marks = {}, {}
  for _, l in ipairs(lines) do
    if l:match("^%-+$") and #out > 0 and out[#out] ~= "" and #l == #out[#out] then
      marks[#marks + 1] = #out
    else
      out[#out + 1] = l
    end
  end
  return out, marks
end

M.help_ns = vim.api.nvim_create_namespace("sw_help")

-- Show tab n of the open help (wrapping round).
function M.help_show(n)
  local h = M.help_state
  if not (h and M.help_win and vim.api.nvim_win_is_valid(M.help_win)) then return end
  n = ((n - 1) % #h.tabs) + 1
  h.current = n
  local lines, marks = help_headings(h.tabs[n].lines)
  vim.bo[h.buf].modifiable = true
  vim.api.nvim_buf_set_lines(h.buf, 0, -1, false, lines)
  vim.bo[h.buf].modifiable = false
  vim.api.nvim_buf_clear_namespace(h.buf, M.help_ns, 0, -1)
  for _, row in ipairs(marks) do vim.api.nvim_buf_add_highlight(h.buf, M.help_ns, "Title", row - 1, 0, -1) end
  vim.wo[M.help_win].winbar = help_bar(h.tabs, n, vim.api.nvim_win_get_width(M.help_win))
  pcall(vim.api.nvim_win_set_cursor, M.help_win, { 1, 0 })
end

-- F3 (and the menu's Help): the help float, in tabs, opening on the guide to this story's format. F3 again closes it.
function M.help(tab)
  if M.help_win and vim.api.nvim_win_is_valid(M.help_win) then          -- F3 again (or the menu's Help again) closes it
    M.help_close()
    return
  end
  local width = math.max(40, math.min(100, vim.o.columns - 6))
  local tabs = M.help_tabs(width - 2)
  local tallest = 5
  for _, t in ipairs(tabs) do tallest = math.max(tallest, #(help_headings(t.lines)) + 1) end
  local buf = vim.api.nvim_create_buf(false, true)
  local height = math.max(5, math.min(tallest, vim.o.lines - 6))
  local win = vim.api.nvim_open_win(buf, true, { relative = "editor", row = 2, col = math.floor((vim.o.columns - width) / 2),
    width = width, height = height, style = "minimal", border = "rounded", title = " Help ", title_pos = "center",
    footer = string.format(HELP_HINT, #tabs), footer_pos = "center" })
  vim.wo[win].wrap = true
  vim.wo[win].linebreak = true
  vim.wo[win].cursorline = true
  vim.cmd("stopinsert")
  M.help_win = win
  M.help_state = { buf = buf, tabs = tabs, current = 1 }
  M.help_show(tab or 1)
  M.help_close = function()
    if vim.api.nvim_win_is_valid(win) then vim.api.nvim_win_close(win, true) end
    M.help_win = nil
    M.help_state = nil
    vim.cmd("nohlsearch")
    local layout = require("sw.layout")
    if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
    require("sw.notepad").insert(true)
  end
  local function map(k, fn) vim.keymap.set("n", k, fn, { buffer = buf, nowait = true }) end
  for _, k in ipairs({ "q", "<Esc>", "<F3>" }) do map(k, M.help_close) end
  map("<Tab>", function() M.help_show(M.help_state.current + 1) end)
  map("<S-Tab>", function() M.help_show(M.help_state.current - 1) end)
  for i = 1, math.min(9, #tabs) do map(tostring(i), function() M.help_show(i) end) end
  vim.keymap.set("n", "<Space>", "<PageDown>", { buffer = buf, nowait = true })
  vim.keymap.set("n", "<BS>", "<PageUp>", { buffer = buf, nowait = true })
  return win
end

-- What does this terminal send for Ctrl+I? (Most send a Tab, which Neovim can't tell apart.)
function M.keycheck()
  vim.api.nvim_echo({ { "Press Ctrl+I now (anything else cancels)…", "Normal" } }, false, {})
  vim.cmd("redraw")
  local key = vim.fn.getcharstr()
  local distinct = key ~= "\t" and vim.fn.keytrans(key) ~= "<Tab>" and vim.fn.keytrans(key):lower():find("c%-i") ~= nil
  local msg
  if key == "\t" then
    msg = "Ctrl+I sent a Tab, so it can't be told apart from the Tab key here. Use Alt+I for italic."
    session.set_pref("ctrl_i", "no")
  elseif distinct then
    msg = "Ctrl+I arrives as " .. vim.fn.keytrans(key) .. ": it works. Restart the Writer to use it for italic."
    session.set_pref("ctrl_i", "yes")
  else
    msg = "Got " .. vim.fn.keytrans(key) .. " (not Ctrl+I)."
  end
  vim.api.nvim_echo({ { msg, "Normal" } }, true, {})
  return key, msg
end

function M.edit_settings()
  M.open_file(story.dir .. "/settings.toml")
end

function M.open_file(path)
  backup.save_all()
  if not util.exists(path) then util.write(path, "") end
  vim.api.nvim_set_current_win(layout.main)
  vim.cmd("edit " .. vim.fn.fnameescape(path))
  vim.bo.filetype = "toml"
  vim.bo.swapfile = false
  -- a saved settings file is applied straight away
  vim.api.nvim_create_autocmd("BufWritePost", { buffer = 0, callback = function() M.apply_settings() end })
end

-- Read the story's settings again (settings.toml) and apply what can change on the fly.
function M.apply_settings()
  story.reload()
  layout.apply()
  prose.decorate(M.main_buf())
  if story.setting("typewriter", false) ~= prose.typewriter then prose.set_typewriter(story.setting("typewriter", false)) end
  if story.setting("invisibles", false) ~= prose.invisibles then prose.set_invisibles(story.setting("invisibles", false)) end
  if story.setting("spellcheck", true) ~= prose.spell then prose.set_spell(story.setting("spellcheck", true)) end
  stats.refresh()
end

function M.new_scene()
  vim.ui.input({ prompt = "New scene title: " }, function(t)
    if t == nil then return end
    local path, line = sidebar.add(t)
    M.open_scene(path, { line + 1, 0 })
  end)
end

-- --- setup ---------------------------------------------------------------------------------------------------

local function global_options()
  local o = vim.o
  o.termguicolors = true
  o.laststatus = 3
  o.statusline = " "                        -- (blank until the word counts are ready: never a file path)
  o.showmode = false
  o.ruler = false
  o.showcmd = false
  o.mouse = "a"
  o.hidden = true
  o.swapfile = false
  o.title = true
  o.titlestring = "storywheel: writing"        -- (the terminal window title; short, so it never shows a long path. start() adds the story's title)
  o.shortmess = "filmnrxoOtTWAIFcs"        -- short messages: a long file path must never wrap and scroll the status line
  o.scrolloff = 4
  o.timeoutlen = 600
  o.virtualedit = ""
  o.splitright = false
end

function M.map_global()
  local function map(modes, lhs, fn, desc)
    vim.keymap.set(modes, lhs, fn, { silent = true, desc = desc })
  end
  map({ "n", "i", "x", "s" }, "<F1>", function() M.leave("wheel") end, "to the Wheel")
  map({ "n", "i", "x", "s" }, "<F2>", function() M.leave("builder") end, "to the Builder")
  map({ "n", "i", "x", "s" }, "<F3>", function() M.help() end, "help (you are in the Writer)")
  map({ "n", "i", "x", "s" }, "<F4>", function() M.leave("settings") end, "to Settings")
  map({ "n", "i", "x", "s" }, "<F5>", function() M.words() end, "to Words")
  map({ "n", "i" }, story.setting("key_sidebar", "<F9>"), function() sidebar.toggle() end, "scene sidebar")
  map({ "n", "i" }, story.setting("key_peek", "<F8>"), function() world.peek() end, "peek")
  map({ "n", "i" }, story.setting("key_overview", "<C-o>"), function() require("sw.overview").toggle() end, "story outline")
  -- The same actions as the Space keys below, with keys that work while typing (notepad mode); Settings > Keys changes them.
  local notepad_keys = {
    key_new_scene = function() M.new_scene() end, key_invisibles = function() prose.toggle("invisibles") end,
    key_typewriter = function() prose.toggle("typewriter") end, key_spell = function() prose.toggle("spell") end,
    key_stats = function() M.show_stats() end, key_copy_manuscript = function() M.copy_manuscript() end,
    key_export = function() M.export() end, key_writer_settings = function() M.edit_settings() end, key_keycheck = function() M.keycheck() end,
  }
  for name, fn in pairs(notepad_keys) do
    map({ "n", "i", "x", "s" }, story.setting(name, require("sw.keys_default")[name]), fn, "Writer: " .. name)
  end
  local leader = {
    n = function() sidebar.toggle() end, p = function() world.peek() end, a = function() M.new_scene() end,
    i = function() prose.toggle("invisibles") end, t = function() prose.toggle("typewriter") end,
    s = function() prose.toggle("spell") end, w = function() M.show_stats() end,
    c = function() M.copy_manuscript() end, e = function() M.export("docx") end,
    S = function() M.edit_settings() end, k = function() M.keycheck() end, ["?"] = function() M.help() end,
  }
  for key, fn in pairs(leader) do map("n", "<Space>" .. key, fn, "Writer: " .. key) end
  map("n", "]]", function() M.step_scene(1) end, "next scene")
  map("n", "[[", function() M.step_scene(-1) end, "previous scene")
end

function M.commands()
  local c = function(name, fn, opts) vim.api.nvim_create_user_command(name, fn, opts or {}) end
  c("SWBuilder", function() M.leave("builder") end)
  c("SWWheel", function() M.leave("wheel") end)
  c("SWSidebar", function() sidebar.toggle() end)
  c("SWPeek", function() world.peek() end)
  c("SWOutline", function() require("sw.overview").toggle() end)
  c("SWExport", function(a) M.export(a.args ~= "" and a.args or "docx") end, { nargs = "?" })
  c("SWCopy", function() M.copy_manuscript() end)
  c("SWStats", function() M.show_stats() end)
  c("SWHelp", function() M.help() end)
  c("SWSettings", function() M.edit_settings() end)
  c("SWKeyCheck", function() M.keycheck() end)
  c("SWSceneBreak", function() prose.scene_break() end)
  c("SWJoin", function() notepad.join_lines() end)
  c("SWLookup", function(a) if a.args ~= "" then require("sw.lookup").show(a.args) else require("sw.lookup").word() end end, { nargs = "?" })
  c("SWReplace", function(a) require("sw.replace").open(a.args ~= "" and a.args or nil) end, { nargs = "?" })
  c("SWInvisibles", function() prose.toggle("invisibles") end)
  c("SWTypewriter", function() prose.toggle("typewriter") end)
  c("SWSpell", function() prose.toggle("spell") end)
  c("SWNewScene", function() M.new_scene() end)
end

-- setup() registers commands and keys; the window layout waits for VimEnter, when the real screen size is known.
-- (Tests call start() themselves.)
function M.setup()
  global_options()
  story.setup()
  M.commands()
  M.map_global()
  if not story.dir then
    vim.api.nvim_echo({ { "No story given: start the Writer from storywheel (Builder, F3).", "WarningMsg" } }, true, {})
    return
  end
  vim.api.nvim_create_autocmd("VimEnter", { once = true, callback = function() M.start() end })
end

function M.start()
  if M.started or not story.dir then return end
  M.started = true
  local title = vim.trim((story.info or {}).title or "")
  if title ~= "" then vim.o.titlestring = "storywheel: " .. story.title_with_format(title) end           -- (the window title says which story this is)
  story.ensure_first_scene()
  local saved = session.load()
  gui.setup()                                       -- (is this the Writer's own kitty window?)
  require("sw.appearance").setup()                  -- (transparent background, text and accent colors)
  local main = vim.api.nvim_get_current_win()
  layout.setup(main)
  prose.window = main
  local start = saved.current
  if not (start and util.exists(start)) then start = story.files()[1].path end
  local cursor = saved.cursors and saved.cursors[start] or { 1, 0 }
  local asked = os.getenv("STORYWHEEL_SCENE")                  -- "<file>:<line>": open at that scene (from the Builder)
  if asked and asked ~= "" then
    local file, line = asked:match("^(.*):(%d+)$")
    if file and util.exists(file) then
      start, cursor = file, { tonumber(line), 0 }
      local sc = story.scene_at(file, tonumber(line))
      if sc then cursor = { sc.body, 0 } end                   -- not on the marker itself, on the first line of text
    end
  end
  local replaced = M.apply_pending_replace()
  if replaced then start, cursor = replaced[1], replaced[2] end
  M.open_scene(start, cursor)
  for _, p in ipairs(saved.open or {}) do          -- scenes that were open come back as (hidden) buffers
    if p ~= start and util.exists(p) then pcall(util.load_buffer, p) end
  end
  local function pick(remembered, default)
    if remembered == nil then return default end
    return remembered
  end
  require("sw.spell").setup()
  prose.set_typewriter(pick(saved.typewriter, story.setting("typewriter", false)))
  prose.set_invisibles(pick(saved.invisibles, story.setting("invisibles", false)))
  prose.set_spell(pick(saved.spell, story.setting("spellcheck", true)))
  stats.setup()
  backup.setup()
  world.setup()
  require("sw.typing").setup()
  require("sw.grammar").setup(pick(saved.grammar, story.setting("grammar", false)))
  vim.api.nvim_create_autocmd({ "BufEnter", "BufReadPost" }, { group = vim.api.nvim_create_augroup("sw_spell", { clear = true }),
    callback = function(ev)
      local name = vim.api.nvim_buf_get_name(ev.buf)
      if story.manuscript and name:find(story.manuscript, 1, true) then require("sw.spell").apply(ev.buf) end
    end })
  require("sw.spell").apply_all()
  require("sw.context").setup()                     -- our own right-click menu, not Neovim's pop-up
  notepad.setup()                                   -- (notepad mode is on unless the settings say otherwise)
  if notepad.enabled then
    notepad.map_buffer(vim.api.nvim_get_current_buf())
    notepad.disable_alt_keys(vim.api.nvim_get_current_buf())          -- (after every real Alt key is mapped)
  end
  vim.api.nvim_set_current_win(layout.main)
  if saved.sidebar then
    sidebar.open()
    vim.api.nvim_set_current_win(layout.main)
  end
  notepad.start_typing()
  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI" }, {
    group = vim.api.nvim_create_augroup("sw_decorate", { clear = true }),
    callback = function(ev)
      if vim.bo[ev.buf].filetype == "storywheel" then prose.decorate(ev.buf) end        -- (floats are drawn from column 0, no paragraph indent)
      if layout.sidebar_open then sidebar.render() end
    end,
  })
  vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI", "InsertEnter" }, {
    group = vim.api.nvim_create_augroup("sw_marker_guard", { clear = true }), callback = function() prose.guard_marker() end,
  })
  prose.guard_marker()                                          -- (the session may have reopened the cursor on a marker)
  vim.api.nvim_create_autocmd("VimLeavePre", { group = vim.api.nvim_create_augroup("sw_leave", { clear = true }),
    callback = function()
      session.save({ sidebar = layout.sidebar_open, invisibles = prose.invisibles, typewriter = prose.typewriter, spell = prose.spell,
                 grammar = require("sw.grammar").enabled })
      stats.save()
    end })
end

return M
