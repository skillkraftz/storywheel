-- A menu of Writer actions (F12 / Alt+M): a small floating list. Arrow keys or a number choose, Enter runs, Esc closes;
-- a mouse click on an entry runs it too.
local util = require("sw.util")
local M = {}

local function actions()
  local sw = require("sw")
  local prose = require("sw.prose")
  local notepad = require("sw.notepad")
  return {
    { "Scenes sidebar", function() require("sw.sidebar").toggle() end },
    { "New scene", function() sw.new_scene() end },
    { "Undo (" .. util.key_label("<C-z>") .. ")", function() notepad.undo() end },
    { "Redo (" .. util.key_label("<C-y>") .. ")", function() notepad.redo() end },
    { "Find…", function() notepad.find() end },
    { "Find and replace…", function() require("sw.replace").open() end },
    { "Look up the word under the cursor", function() require("sw.lookup").word() end },
    { "Look up a word…", function() require("sw.lookup").ask() end },
    { "Join lines into one paragraph", function() notepad.join_lines() end },
    { "Peek at the name under the cursor", function() require("sw.world").peek() end },
    { "Show invisibles", function() prose.toggle("invisibles") end },
    { "Typewriter mode", function() prose.toggle("typewriter") end },
    { "Spellcheck", function() prose.toggle("spell") end },
    { "Add the word under the cursor to this universe's dictionary", function()
        local w = require("sw.lookup").word_at_cursor()
        if w then require("sw.spell").add_word(w) end
      end },
    { "Word counts", function() sw.show_stats() end },
    { "Export manuscript (.docx)", function() sw.export("docx") end },
    { "Export anonymous manuscript (.docx)", function() sw.export("docx", true) end },
    { "Copy manuscript as plain text", function() sw.copy_manuscript() end },
    { "This story's settings.toml", function() sw.edit_settings() end },
    { "Words (F5): look up, vocabulary, word bank, overused", function() sw.words() end },
    { "Settings (F4)", function() sw.leave("settings") end },
    { "Back to the Builder (F2)", function() sw.leave("builder") end },
    { "To the Wheel (F1)", function() sw.leave("wheel") end },
    { "Help", function() sw.help() end },
    { notepad.enabled and "Switch to Vim keys (this session)" or "Switch to notepad mode", function()
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
  }
end

M.items = actions

function M.open()
  local items = actions()
  local labels = {}
  for i, it in ipairs(items) do
    labels[i] = string.format(" %s%s ", i <= 9 and (i .. "  ") or "   ", it[1])
  end
  local width = 0
  for _, l in ipairs(labels) do width = math.max(width, vim.fn.strdisplaywidth(l)) end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, labels)
  vim.bo[buf].modifiable = false
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 2, col = math.floor((vim.o.columns - width) / 2), width = width + 2,
    height = math.min(#labels, vim.o.lines - 6), style = "minimal", border = "rounded", title = " Writer ", title_pos = "center",
  })
  vim.wo[win].cursorline = true
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
  local function row() return vim.api.nvim_win_get_cursor(win)[1] end
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<CR>", function() run(row()) end)
  map("<Esc>", function() close() np.insert(true) end)
  map("q", function() close() np.insert(true) end)
  map("<LeftMouse>", function()
    local pos = vim.fn.getmousepos()
    if pos.winid == win and pos.line >= 1 then run(pos.line) else close() np.insert(true) end
  end)
  for i = 1, math.min(9, #items) do map(tostring(i), function() run(i) end) end
  map("<Down>", "j")
  map("<Up>", "k")
  M.last = { win = win, buf = buf, items = items }
  return win
end

return M
