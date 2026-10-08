-- The right-click menu: a small floating list of our own (Neovim's built-in pop-up treats the right button like the left and
-- runs an item when the button is let go over it). Here only a left click or Enter runs an item; a second right-click, Esc or q
-- closes it and runs nothing. It opens at the pointer, is kept inside the window, and scrolls when the window is short.
local util = require("sw.util")
local story = require("sw.story")
local M = {}

M.last = nil

-- The items: { label, action, hint } in order, "-" for a separator. The action names are those of notepad.run_menu_item.
function M.items(spell_word)
  local items = {
    { "Undo", "undo", "Ctrl+Z" }, { "Redo", "redo", "Ctrl+Y" }, { "-" },
    { "Cut", "cut", "Ctrl+X" }, { "Copy", "copy", "Ctrl+C" }, { "Paste", "paste", "Ctrl+V" }, { "-" },
  }
  if spell_word then items[#items + 1] = { "Fix Spelling…", "spell_fix" } end
  items[#items + 1] = { "Look Up", "lookup", { "key_lookup", "<F7>" } }
  items[#items + 1] = { "Add to Dictionary", "spell_add" }
  items[#items + 1] = { "-" }
  items[#items + 1] = { "More…", "menu", { "key_menu", "<F12>" } }
  for _, it in ipairs(items) do
    if type(it[3]) == "table" then it[3] = util.key_label(story.setting(it[3][1], it[3][2])) end
  end
  return items
end

function M.close()
  local m = M.last
  M.last = nil
  if m and vim.api.nvim_win_is_valid(m.win) then vim.api.nvim_win_close(m.win, true) end
  return m
end

-- Put a selection that was there before the menu took the focus back, so Cut, Copy and the rest see it.
local function reselect(sel)
  if not sel then return end
  local row, col, row2, col2 = sel[1], sel[2], sel[3], sel[4]
  pcall(function()
    vim.api.nvim_win_set_cursor(0, { row + 1, col })
    vim.cmd("normal! v")
    vim.api.nvim_win_set_cursor(0, { row2 + 1, math.max(0, col2) })
    vim.cmd("normal! \7")
  end)
end

-- Open the menu at the pointer (or at `at` = { screen row, screen col }, 1-based). The cursor goes where it was clicked unless the click
-- is inside a selection.
function M.open(at)
  M.close()
  local layout = require("sw.layout")
  local np = require("sw.notepad")
  local pos = vim.fn.getmousepos()
  local sel
  if np.has_selection and np.has_selection() then
    local r1, c1, r2, c2 = require("sw.prose").selection_bounds()
    sel = { r1, c1, r2, c2 }
    if pos.winid == layout.main and pos.line > 0 then            -- a click outside the selection ends it
      local row, col = pos.line - 1, math.max(0, pos.column - 1)
      local inside = (row > r1 or (row == r1 and col >= c1)) and (row < r2 or (row == r2 and col <= c2))
      if not inside then sel = nil end
    end
  end
  if not sel and pos.winid == layout.main and pos.line > 0 then
    if vim.fn.mode():match("[sSvV\22\19]") then vim.cmd("normal! \27") end
    pcall(vim.api.nvim_win_set_cursor, layout.main, { pos.line, math.max(0, pos.column - 1) })
  end
  local word = require("sw.spell").bad_word()
  local items = M.items(word)
  local lines, row_item = {}, {}
  local width = 0
  for _, it in ipairs(items) do
    if it[1] ~= "-" then width = math.max(width, vim.fn.strdisplaywidth(it[1]) + (it[3] and (vim.fn.strdisplaywidth(it[3]) + 3) or 0)) end
  end
  for i, it in ipairs(items) do
    if it[1] == "-" then
      lines[#lines + 1] = string.rep("─", width + 2)
    else
      local pad = width - vim.fn.strdisplaywidth(it[1]) - (it[3] and vim.fn.strdisplaywidth(it[3]) or 0)
      lines[#lines + 1] = " " .. it[1] .. string.rep(" ", pad) .. (it[3] or "") .. " "
      row_item[#lines] = i
    end
  end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  for r, l in ipairs(lines) do
    if not row_item[r] then vim.api.nvim_buf_add_highlight(buf, -1, "Comment", r - 1, 0, -1) end
  end
  local height = math.max(1, math.min(#lines, vim.o.lines - 4))              -- (a short window scrolls)
  local w = width + 2
  local srow = at and at[1] or (pos.screenrow > 0 and pos.screenrow or 2)
  local scol = at and at[2] or (pos.screencol > 0 and pos.screencol or 2)
  -- (row and col are those of the text; the border sits one cell up and left of them, so the pointer lands on the border, not on an item)
  local row = math.max(1, math.min(srow, vim.o.lines - 2 - height))
  local col = math.max(1, math.min(scol, vim.o.columns - 1 - w))
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = row, col = col, width = w, height = height, style = "minimal", border = "rounded", zindex = 200,
  })
  vim.wo[win].cursorline = true
  vim.wo[win].wrap = false
  vim.wo[win].scrolloff = 0
  vim.wo[win].winhighlight = "CursorLine:PmenuSel"
  vim.cmd("stopinsert")
  local first
  for r = 1, #lines do if row_item[r] then first = r break end end
  vim.api.nvim_win_set_cursor(win, { first or 1, 0 })

  local function close_and_return()
    M.close()
    if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
  end
  local function run(i)
    local it = items[i]
    close_and_return()
    if not it or it[1] == "-" then return end
    reselect(sel)
    np.run_menu_item(it[2])
    -- (back to typing is done by run_menu_item, but only in the writing window: an item that opened a float keeps Normal mode)
  end
  local function current() return row_item[vim.api.nvim_win_get_cursor(win)[1]] end
  local function move(dir)
    local r = vim.api.nvim_win_get_cursor(win)[1] + dir
    while r >= 1 and r <= #lines and not row_item[r] do r = r + dir end
    if r >= 1 and r <= #lines then vim.api.nvim_win_set_cursor(win, { r, 0 }) end
  end
  local function leave() close_and_return() np.insert(true) end              -- closes and runs nothing
  local function map(lhs, fn, modes) vim.keymap.set(modes or "n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<CR>", function() local i = current() if i then run(i) end end)
  map("<Esc>", leave)
  map("q", leave)
  map("<RightMouse>", leave)                                                  -- a second right-click closes it and nothing else
  map("<RightRelease>", "<Nop>")
  map("<RightDrag>", "<Nop>")
  map("<LeftDrag>", "<Nop>")
  map("<LeftRelease>", "<Nop>")
  map("<2-LeftMouse>", "<Nop>")
  map("<MiddleMouse>", "<Nop>")
  map("<LeftMouse>", function()
    local p = vim.fn.getmousepos()
    if p.winid ~= win then leave() return end
    local line = p.line > 0 and p.line or (p.winrow + vim.fn.getwininfo(win)[1].topline - 1)      -- (no wrapping: a row is a line)
    local i = row_item[line]
    if i then run(i) end
  end)
  map("<Down>", function() move(1) end)
  map("j", function() move(1) end)
  map("<Up>", function() move(-1) end)
  map("k", function() move(-1) end)
  vim.api.nvim_create_autocmd({ "WinLeave", "BufLeave" }, { buffer = buf, once = true, callback = function() M.last = nil end })
  M.last = { win = win, buf = buf, items = items, lines = lines }
  return win
end

-- The right button, anywhere: over the manuscript it opens the menu; anywhere else (a float, the margins) it does nothing, so a
-- right-click in the F12 menu or the help never opens a second menu.
function M.right_click()
  local layout = require("sw.layout")
  local pos = vim.fn.getmousepos()
  if M.last then M.close() return end
  if vim.api.nvim_win_get_config(0).relative ~= "" then return end          -- a float has the focus (F12, help...): no second menu
  if layout.main and pos.winid == layout.main and vim.bo[vim.api.nvim_win_get_buf(layout.main)].filetype == "storywheel" then
    M.open()
  end
end

function M.setup()
  vim.o.mousemodel = "extend"
  pcall(vim.cmd, "aunmenu PopUp")
  vim.v.errmsg = ""
  vim.keymap.set({ "n", "i", "x", "s" }, "<RightMouse>", function() M.right_click() end, { silent = true })
  vim.keymap.set({ "n", "i", "x", "s" }, "<RightRelease>", "<Nop>", { silent = true })
  vim.keymap.set({ "n", "i", "x", "s" }, "<RightDrag>", "<Nop>", { silent = true })
end

return M
