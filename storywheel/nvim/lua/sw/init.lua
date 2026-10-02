-- The Writer: puts the modules together. Entry point: require("sw").setup() (from the config's init.lua).
local util = require("sw.util")
local story = require("sw.story")
local layout = require("sw.layout")
local prose = require("sw.prose")
local sidebar = require("sw.sidebar")
local world = require("sw.world")
local stats = require("sw.stats")
local backup = require("sw.backup")
local session = require("sw.session")

local M = {}

M.HELP = {
  "storywheel Writer                         F1 Wheel   F2 Builder   F3 Writer   F4 Settings",
  "",
  "Writing",
  "  Alt+I / Alt+B      italic / bold (insert and visual; Ctrl+B too; Ctrl+I only if your terminal can send it)",
  "  Enter              starts a new paragraph (a blank line between, shown with an indent)",
  "  Alt+S              scene break  (* * *  in the file, centered on screen)",
  "  Tab                next name in the completion list (names from this universe)",
  "",
  "Normal mode, with Space first",
  "  n  scene sidebar      p  peek at the name under the cursor (also F10)    a  new scene",
  "  i  show invisibles    t  typewriter mode    s  spellcheck",
  "  w  word counts        c  copy the manuscript as plain text",
  "  e  export (docx)      S  this story's settings.toml      k  check which keys your terminal sends",
  "  ]] / [[  next / previous scene                          ?  this help",
  "",
  "Sidebar (Space n, or F9):  Enter jump   a add   r rename   J / K move down / up   q close",
  "",
  "Leaving:  F2 saves everything and goes back to the Builder.  F1 the Wheel.  F4 Settings.  :q works too.",
  "Everything is saved as you go; backups are in the story's .backups folder.",
}

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

function M.step_scene(direction)
  local scenes = story.scenes()
  local cur = M.current_scene()
  for i, s in ipairs(scenes) do
    if s.path == cur and scenes[i + direction] then
      session.save()
      return M.open_scene(scenes[i + direction].path, { 1, 0 })
    end
  end
  vim.api.nvim_echo({ { direction > 0 and "This is the last scene." or "This is the first scene.", "Normal" } }, false, {})
end

-- --- leaving ----------------------------------------------------------------------------------------------

-- Save everything, remember where we were, say where to go next, and quit.
function M.leave(where)
  local ok = pcall(backup.save_all)
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(b) and vim.bo[b].modified and vim.bo[b].buftype == "" and vim.api.nvim_buf_get_name(b) ~= "" then
      vim.api.nvim_echo({ { "Couldn't save " .. vim.api.nvim_buf_get_name(b) .. ": staying here.", "ErrorMsg" } }, true, {})
      return false
    end
  end
  backup.snapshot(false)
  stats.save()
  session.save({ sidebar = layout.sidebar_open, invisibles = prose.invisibles, typewriter = prose.typewriter, spell = prose.spell })
  local rf = os.getenv("STORYWHEEL_RETURN_FILE")
  if rf and rf ~= "" then util.write(rf, where or "") end
  vim.cmd("qa!")
  return true
end

-- --- the toggles and commands ---------------------------------------------------------------------------

function M.plain_text()
  local parts = {}
  for _, s in ipairs(story.scenes()) do
    local b = vim.fn.bufnr(s.path)
    local text
    if b ~= -1 and vim.api.nvim_buf_is_loaded(b) then text = table.concat(vim.api.nvim_buf_get_lines(b, 0, -1, false), "\n")
    else text = util.read(s.path) or "" end
    parts[#parts + 1] = text:gsub("^%s+", ""):gsub("%s+$", "")
  end
  local text = table.concat(parts, "\n\n")
  text = text:gsub("\n%* %* %*\n", "\n#\n"):gsub("^%* %* %*\n", "#\n")
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
  vim.api.nvim_echo({ { "Couldn't reach the clipboard (install xclip or wl-clipboard). Use the Builder's export for a .txt file.", "ErrorMsg" } }, true, {})
  return false
end

function M.export(format)
  backup.save_all()
  local args = { "manuscript", "export", story.universe .. "/" .. story.slug, "--format", format or "docx", "--json" }
  vim.api.nvim_echo({ { "Exporting…", "Normal" } }, false, {})
  local data, err = util.cli_json(args)
  if data and data.path then
    vim.api.nvim_echo({ { "Exported: " .. data.path .. ((data.warnings and #data.warnings > 0) and ("  (" .. table.concat(data.warnings, "; ") .. ")") or ""), "Normal" } }, true, {})
    return data
  end
  vim.api.nvim_echo({ { "Export failed: " .. tostring(err), "ErrorMsg" } }, true, {})
end

function M.show_stats()
  local w = stats.scene()
  vim.api.nvim_echo({ { string.format("scene %d words · manuscript %d · today %d / goal %s", w, stats.manuscript(), stats.today(),
                                      tostring(story.setting("daily_goal", 0))), "Normal" } }, false, {})
end

function M.help()
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, M.HELP)
  vim.bo[buf].modifiable = false
  local width = 0
  for _, l in ipairs(M.HELP) do width = math.max(width, vim.fn.strdisplaywidth(l)) end
  width = math.min(width + 2, vim.o.columns - 4)
  local win = vim.api.nvim_open_win(buf, true, { relative = "editor", row = 2, col = math.floor((vim.o.columns - width) / 2),
    width = width, height = math.min(#M.HELP, vim.o.lines - 6), style = "minimal", border = "rounded" })
  for _, k in ipairs({ "q", "<Esc>", "<CR>", "?" }) do vim.keymap.set("n", k, function() vim.api.nvim_win_close(win, true) end, { buffer = buf }) end
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
  if story.setting("spellcheck", false) ~= prose.spell then prose.set_spell(story.setting("spellcheck", false)) end
  stats.refresh()
end

function M.new_scene()
  vim.ui.input({ prompt = "New scene title: " }, function(t)
    if t == nil then return end
    local path = sidebar.add(t ~= "" and t or "scene")
    M.open_scene(path, { 1, 0 })
  end)
end

-- --- setup ---------------------------------------------------------------------------------------------------

local function global_options()
  local o = vim.o
  o.termguicolors = true
  o.laststatus = 3
  o.showmode = false
  o.ruler = false
  o.showcmd = false
  o.mouse = "a"
  o.hidden = true
  o.swapfile = false
  o.shortmess = o.shortmess .. "I"
  o.scrolloff = 4
  o.timeoutlen = 600
  o.virtualedit = ""
  o.splitright = false
end

function M.map_global()
  local function map(modes, lhs, fn, desc)
    vim.keymap.set(modes, lhs, fn, { silent = true, desc = desc })
  end
  map({ "n", "i", "x" }, "<F1>", function() M.leave("wheel") end, "to the Wheel")
  map({ "n", "i", "x" }, "<F2>", function() M.leave("builder") end, "to the Builder")
  map({ "n", "i", "x" }, "<F3>", function() vim.api.nvim_echo({ { "You are in the Writer.", "Normal" } }, false, {}) end, "Writer")
  map({ "n", "i", "x" }, "<F4>", function() M.leave("settings") end, "to Settings")
  map({ "n", "i" }, "<F9>", function() sidebar.toggle() end, "scene sidebar")
  map({ "n", "i" }, "<F10>", function() world.peek() end, "peek")
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
  c("SWExport", function(a) M.export(a.args ~= "" and a.args or "docx") end, { nargs = "?" })
  c("SWCopy", function() M.copy_manuscript() end)
  c("SWStats", function() M.show_stats() end)
  c("SWHelp", function() M.help() end)
  c("SWSettings", function() M.edit_settings() end)
  c("SWKeyCheck", function() M.keycheck() end)
  c("SWSceneBreak", function() prose.scene_break() end)
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
  story.ensure_first_scene()
  local saved = session.load()
  local main = vim.api.nvim_get_current_win()
  layout.setup(main)
  prose.window = main
  local start = saved.current
  if not (start and util.exists(start)) then start = story.scenes()[1].path end
  M.open_scene(start, saved.cursors and saved.cursors[start] or { 1, 0 })
  for _, p in ipairs(saved.open or {}) do          -- scenes that were open come back as (hidden) buffers
    if p ~= start and util.exists(p) then pcall(vim.fn.bufload, vim.fn.bufadd(p)) end
  end
  local function pick(remembered, default)
    if remembered == nil then return default end
    return remembered
  end
  prose.set_typewriter(pick(saved.typewriter, story.setting("typewriter", false)))
  prose.set_invisibles(pick(saved.invisibles, story.setting("invisibles", false)))
  prose.set_spell(pick(saved.spell, story.setting("spellcheck", false)))
  stats.setup()
  backup.setup()
  world.setup()
  vim.api.nvim_set_current_win(layout.main)
  if saved.sidebar then
    sidebar.open()
    vim.api.nvim_set_current_win(layout.main)
  end
  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI" }, {
    group = vim.api.nvim_create_augroup("sw_decorate", { clear = true }),
    callback = function(ev) prose.decorate(ev.buf) if layout.sidebar_open then sidebar.render() end end,
  })
  vim.api.nvim_create_autocmd("VimLeavePre", { group = vim.api.nvim_create_augroup("sw_leave", { clear = true }),
    callback = function()
      session.save({ sidebar = layout.sidebar_open, invisibles = prose.invisibles, typewriter = prose.typewriter, spell = prose.spell })
      stats.save()
    end })
end

return M
