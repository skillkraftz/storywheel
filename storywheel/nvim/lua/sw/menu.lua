-- A menu of Writer actions (F12 / Alt+M): a small floating list. Arrow keys choose and Enter runs; every entry also has a key of its own
-- (1-9, then letters), shown beside it; Esc closes; a mouse click on an entry runs it too.
local util = require("sw.util")
local M = {}

-- The menu in groups: { title, { {label, function}, ... } }. M.items() is the same list without the titles (what the number keys and
-- Down/Enter walk through).
local function groups()
  local sw = require("sw")
  local prose = require("sw.prose")
  local notepad = require("sw.notepad")
  local story_mod = require("sw.story")
  local exports
  if story_mod.is_screenplay() then
    exports = {
      { "Export script (.pdf)", function() sw.export("pdf") end },
      { "Export anonymous script (.pdf)", function() sw.export("pdf", true) end },
      { "Export for Final Draft (.fdx)", function() sw.export("fdx") end },
      { "Export Fountain (.fountain)", function() sw.export("fountain") end },
      { "Flip test (" .. util.key_label(story_mod.setting("key_flip_test", "<A-f>")) .. ")", function() require("sw.script").flip_test() end },
    }
  else
    exports = {
      { "Export manuscript (.docx)", function() sw.export("docx") end },
      { "Export anonymous manuscript (.docx)", function() sw.export("docx", true) end },
    }
  end
  local story_items = {
    { "Scenes sidebar", function() require("sw.sidebar").toggle() end },
    { "Story outline (" .. util.key_label(story_mod.setting("key_overview", "<C-o>")) .. ")", function() require("sw.overview").toggle() end },
    { "New scene", function() sw.new_scene() end },
    { "Word counts", function() sw.show_stats() end },
  }
  vim.list_extend(story_items, exports)
  vim.list_extend(story_items, {
    { "Copy manuscript as plain text", function() sw.copy_manuscript() end },
    { "Restore from a backup…", function() require("sw.restore").open() end },
  })
  return {
    { "Edit", {
      { "Undo (" .. util.key_label("<C-z>") .. ")", function() notepad.undo() end },
      { "Redo (" .. util.key_label("<C-y>") .. ")", function() notepad.redo() end },
      { "Find…", function() notepad.find() end },
      { "Find and replace…", function() require("sw.replace").open() end },
      { "Join lines into one paragraph", function() notepad.join_lines() end },
      { "Spellcheck", function() prose.toggle("spell") end },
      { "Add the word under the cursor to this universe's dictionary", function()
          local w = require("sw.lookup").word_at_cursor()
          if w then require("sw.spell").add_word(w) end
        end },
      { require("sw.grammar").enabled and "Grammar check: turn off" or "Grammar check: turn on (needs LanguageTool)", function() require("sw.grammar").toggle() end },
      { "Next grammar problem (" .. util.key_label(require("sw.story").setting("key_grammar_next", "<F10>")) .. ")", function() require("sw.grammar").next() end },
      { "List of grammar problems (" .. util.key_label(require("sw.story").setting("key_grammar_list", "<S-F10>")) .. ")", function() require("sw.grammar").list() end },
      { "Show invisibles", function() prose.toggle("invisibles") end },
      { "Typewriter mode", function() prose.toggle("typewriter") end },
    } },
    { "Look up", {
      { "Look up the word under the cursor", function() require("sw.lookup").word() end },
      { "Look up a word…", function() require("sw.lookup").ask() end },
      { "Peek at the name under the cursor", function() require("sw.world").peek() end },
      { "Words (F5): dictionary, words to learn, overused words", function() sw.words() end },
    } },
    { "Story", story_items },
    { "Leave", {
      { "Settings (F4)", function() sw.leave("settings") end },
      { "Back to the Builder (F2)", function() sw.leave("builder") end },
      { "To the Wheel (F1)", function() sw.leave("wheel") end },
      { "Quit storywheel (" .. util.key_label(require("sw.story").setting("key_quit", "<A-q>")) .. ")", function() sw.quit() end },
    } },
    { "More", {
      { "Help", function() sw.help() end },
      { notepad.enabled and "Use Vim keys for now" or "Use notepad mode again", function()
          if notepad.enabled then
            notepad.enabled = false
            vim.cmd("stopinsert")
            vim.api.nvim_echo({ { "Vim keys on: Escape leaves Insert mode now. Notepad mode comes back next time (it is a setting).", "Normal" } }, false, {})
          else
            notepad.setup()
            notepad.map_buffer(vim.api.nvim_get_current_buf())
            notepad.start_typing()
          end
        end },
    } },
  }
end

local function actions()
  local out = {}
  for _, g in ipairs(groups()) do
    for _, it in ipairs(g[2]) do out[#out + 1] = it end
  end
  return out
end

M.items = actions
M.groups = groups

-- One key for each entry: 1-9, then the letters (not j, k and q, which move and close), then capitals. The menu has about 35 entries.
function M.hotkeys(count)
  local out = {}
  for i = 1, 9 do out[#out + 1] = tostring(i) end
  for _, set in ipairs({ "abcdefghilmnoprstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ" }) do
    for c in set:gmatch(".") do out[#out + 1] = c end
  end
  return vim.list_slice(out, 1, count)
end

function M.open()
  local items = actions()
  local lines, row_item, item_row = {}, {}, {}
  local n = 0
  local keys = M.hotkeys(#items)
  for gi, g in ipairs(groups()) do
    if gi > 1 then lines[#lines + 1] = "" end
    lines[#lines + 1] = " ─ " .. g[1] .. " ─"
    for _, it in ipairs(g[2]) do
      n = n + 1
      lines[#lines + 1] = string.format(" %s  %s ", keys[n] or " ", it[1])
      row_item[#lines] = n
      item_row[n] = #lines
    end
  end
  local width = 0
  for _, l in ipairs(lines) do width = math.max(width, vim.fn.strdisplaywidth(l)) end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  for r, l in ipairs(lines) do
    if not row_item[r] and l ~= "" then vim.api.nvim_buf_add_highlight(buf, -1, "Comment", r - 1, 0, -1) end
  end
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 1, col = math.floor((vim.o.columns - width) / 2), width = width + 2,
    height = math.max(3, math.min(#lines, vim.o.lines - 5)), style = "minimal", border = "rounded", title = " Writer ", title_pos = "center",
  })
  vim.wo[win].cursorline = true
  vim.api.nvim_win_set_cursor(win, { item_row[1], 0 })
  vim.cmd("stopinsert")
  local np = require("sw.notepad")
  local function close()
    if vim.api.nvim_win_is_valid(win) then vim.api.nvim_win_close(win, true) end
    local layout = require("sw.layout")
    if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
  end
  local function run(i)
    local item = items[i]
    close()
    if item then
      item[2]()
      -- back to typing only when we are in the writing window: a help or sidebar window that the item opened keeps Normal mode
      local layout = require("sw.layout")
      if layout.main and vim.api.nvim_get_current_win() == layout.main then np.insert(true) end
    end
  end
  local function current() return row_item[vim.api.nvim_win_get_cursor(win)[1]] end
  local function move(dir)                           -- the next entry, skipping the group titles
    local i = (current() or 1) + dir
    if item_row[i] then vim.api.nvim_win_set_cursor(win, { item_row[i], 0 }) end
  end
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<CR>", function() local i = current() if i then run(i) end end)
  map("<Esc>", function() close() np.insert(true) end)
  map("q", function() close() np.insert(true) end)
  map("<LeftMouse>", function()
    local pos = vim.fn.getmousepos()
    if pos.winid ~= win then close() np.insert(true) return end
    local i = row_item[pos.line]
    if i then run(i) end
  end)
  for i, key in ipairs(keys) do map(key, function() run(i) end) end
  map("<Down>", function() move(1) end)
  map("j", function() move(1) end)
  map("<Up>", function() move(-1) end)
  map("k", function() move(-1) end)
  M.last = { win = win, buf = buf, items = items, keys = keys }
  return win
end

return M
