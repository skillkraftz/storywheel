-- Dictionary and thesaurus card (F7 on the word under the cursor or a selection, F6 for a typed word; also in the menus).
-- A floating card with meanings by part of speech, similar words and opposite words. Move to a word and press Enter: it replaces
-- the word you looked up, keeping its capitalization. The data comes from `storywheel lookup WORD --json` (offline).
local util = require("sw.util")
local M = {}

M.WIDTH = 76

-- The word at the cursor (or in a one-line selection): returns word, { row0, start_col, end_col } or nil.
function M.word_at_cursor()
  local notepad = require("sw.notepad")
  if notepad.has_selection() then
    local text = notepad.selected_text()
    local r1, c1, r2, c2 = require("sw.prose").selection_bounds()
    if text and r1 == r2 and text:match("%S") then
      local trimmed = vim.trim(text)
      vim.cmd("normal! \27")
      return trimmed, { r1, c1 + (#text - #text:gsub("^%s+", "")), c1 + (#text - #text:gsub("^%s+", "")) + #trimmed }
    end
    return nil
  end
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  local line = vim.api.nvim_get_current_line()
  local function wordy(i)
    local c = line:sub(i, i)
    return c ~= "" and (c:match("[%w]") ~= nil or c:byte() >= 128)
  end
  local function joiner(i)       -- an apostrophe or hyphen between two word characters belongs to the word
    local c = line:sub(i, i)
    return (c == "'" or c == "-") and wordy(i - 1) and wordy(i + 1)
  end
  local function part(i) return wordy(i) or joiner(i) end
  local i = col + 1
  if not part(i) and part(i - 1) then i = i - 1 end             -- the cursor is just after the word
  if not part(i) then return nil end
  local s, e = i, i
  while s > 1 and part(s - 1) do s = s - 1 end
  while e < #line and part(e + 1) do e = e + 1 end
  return line:sub(s, e), { row - 1, s - 1, e }
end

function M.apply_case(original, new)
  if original:match("^%u%u+$") then return new:upper() end
  if original:match("^%u") then return new:sub(1, 1):upper() .. new:sub(2) end
  return new
end

-- Ask the CLI. Returns the decoded result, or nil and a message.
function M.fetch(word)
  local out = vim.fn.system(util.cli({ "lookup", word, "--json" }))
  local ok, data = pcall(vim.json.decode, out)
  if not ok or type(data) ~= "table" then return nil, "The dictionary lookup failed (is storywheel installed for python3?)." end
  if data.error then return nil, data.error end
  return data
end

local function wrap(text, width, indent)
  local lines, cur = {}, indent
  for w in text:gmatch("%S+") do
    if #cur + #w + 1 > width and cur:match("%S") then
      lines[#lines + 1] = cur
      cur = indent .. w
    else
      cur = (cur:match("%S") and (cur .. " ") or cur) .. w
    end
  end
  if cur:match("%S") then lines[#lines + 1] = cur end
  return lines
end

-- The card as lines, plus which lines are words you can pick: { lines = {...}, picks = { [line number] = "word" } }.
function M.build(result, original)
  local lines, picks = {}, {}
  local function add(text, pick)
    lines[#lines + 1] = text
    if pick then picks[#lines] = pick end
  end
  if not result.found then
    add(" No entry for '" .. (result.word ~= "" and result.word or result.query) .. "'.")
    if #result.suggestions > 0 then
      add("")
      add(" Did you mean (Enter looks it up):")
      for _, s in ipairs(result.suggestions) do add("   " .. s, { lookup = s }) end
    end
    return { lines = lines, picks = picks }
  end
  for n, e in ipairs(result.entries) do
    if n > 2 then break end
    local form_of = e.form_of ~= vim.NIL and e.form_of or nil           -- (JSON null is vim.NIL, which is truthy)
    add(" " .. e.word .. (form_of and ("   (form of “" .. form_of .. "”)") or ""))
    for _, part in ipairs(e.parts) do
      add(" " .. part.pos)
      for i, s in ipairs(part.senses) do
        if i > 4 then break end
        for _, l in ipairs(wrap(i .. ". " .. s.definition, M.WIDTH - 2, "   ")) do add(l) end
        if s.examples[1] then add("      “" .. s.examples[1] .. "”") end
      end
    end
    add("")
    if #e.synonyms > 0 then
      add(" Similar words" .. (original and (" — Enter replaces “" .. original .. "”") or " — Enter inserts the word"))
      for _, w in ipairs(e.synonyms) do add("   " .. w, { replace = w }) end
      if e.more_synonyms > 0 then add("   … " .. e.more_synonyms .. " more (storywheel thesaurus " .. e.word .. ")") end
      add("")
    end
    if #e.antonyms > 0 then
      add(" Opposite words")
      for _, w in ipairs(e.antonyms) do add("   " .. w, { replace = w }) end
      add("")
    end
  end
  add(" Open English WordNet (CC BY 4.0); Moby Thesaurus (public domain)")
  return { lines = lines, picks = picks }
end

function M.close()
  if M.win and vim.api.nvim_win_is_valid(M.win) then vim.api.nvim_win_close(M.win, true) end
  M.win = nil
  local layout = require("sw.layout")
  if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
end

-- Put `new` in place of the looked-up word (or at the cursor for a typed word), then go back to typing.
function M.replace(new)
  local target, original = M.target, M.original
  local layout = require("sw.layout")
  M.close()
  local buf = vim.api.nvim_win_get_buf(layout.main)
  if target then
    local row, s, e = target[1], target[2], target[3]
    local now = vim.api.nvim_buf_get_text(buf, row, s, row, e, {})[1]
    if now ~= original then
      vim.api.nvim_echo({ { "The text changed since you looked it up; nothing replaced.", "WarningMsg" } }, true, {})
    else
      local text = M.apply_case(original, new)
      vim.api.nvim_buf_set_text(buf, row, s, row, e, { text })
      vim.api.nvim_win_set_cursor(layout.main, { row + 1, s + #text })
    end
  else
    local c = M.cursor or vim.api.nvim_win_get_cursor(layout.main)
    vim.api.nvim_buf_set_text(buf, c[1] - 1, c[2], c[1] - 1, c[2], { new })
    vim.api.nvim_win_set_cursor(layout.main, { c[1], c[2] + #new })
  end
  require("sw.notepad").insert(true)
end

function M.show(word, target)
  local result, err = M.fetch(word)
  if not result then
    vim.api.nvim_echo({ { err, "WarningMsg" } }, true, {})
    return false
  end
  M.close()
  local card = M.build(result, target and word or nil)
  M.target, M.original = target, target and word or nil
  M.result = result
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, card.lines)
  vim.bo[buf].modifiable = false
  vim.bo[buf].bufhidden = "wipe"
  local height = math.min(#card.lines, vim.o.lines - 6)
  local title = " " .. (result.found and result.entries[1].word or "Look up") .. " "
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 2, col = math.max(0, math.floor((vim.o.columns - M.WIDTH) / 2)), width = M.WIDTH, height = math.max(3, height),
    style = "minimal", border = "rounded", title = title, title_pos = "center",
    footer = " Enter pick · Tab next section · w another word · Esc close ", footer_pos = "center",
  })
  vim.wo[win].cursorline = true
  vim.wo[win].wrap = false
  M.win, M.buf, M.card = win, buf, card
  vim.cmd("stopinsert")
  local first
  for i = 1, #card.lines do if card.picks[i] then first = i break end end
  if first then vim.api.nvim_win_set_cursor(win, { first, 0 }) end
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  local function pick()
    local p = card.picks[vim.api.nvim_win_get_cursor(win)[1]]
    if not p then return end
    if p.replace then M.replace(p.replace) elseif p.lookup then M.show(p.lookup, target) end
  end
  map("<CR>", pick)
  map("<LeftMouse>", function()
    local pos = vim.fn.getmousepos()
    if pos.winid ~= win then M.close() require("sw.notepad").insert(true) return end
    vim.api.nvim_win_set_cursor(win, { pos.line, 0 })
  end)
  map("<2-LeftMouse>", pick)
  map("<Esc>", function() M.close() require("sw.notepad").insert(true) end)
  map("q", function() M.close() require("sw.notepad").insert(true) end)
  map("j", "j")
  map("k", "k")
  map("<Down>", "j")
  map("<Up>", "k")
  map("<Tab>", function()                       -- the next section's first word
    local cur = vim.api.nvim_win_get_cursor(win)[1]
    local in_section = true
    for i = cur + 1, #card.lines do
      if not card.picks[i] then in_section = false elseif not in_section then vim.api.nvim_win_set_cursor(win, { i, 0 }) return end
    end
  end)
  map("w", function() M.ask(target) end)
  return true
end

-- F7: the word under the cursor (or the selection).
function M.word()
  local word, target = M.word_at_cursor()
  if not word then
    vim.api.nvim_echo({ { "Put the cursor on a word first (or select one), or press the other lookup key to type a word.", "Normal" } }, true, {})
    return false
  end
  return M.show(word, target)
end

-- F6: a typed word. Picking a word inserts it where the cursor was.
function M.ask(target)
  local layout = require("sw.layout")
  M.cursor = vim.api.nvim_win_get_cursor(layout.main)
  M.close()
  vim.ui.input({ prompt = "Look up: " }, function(text)
    if text and vim.trim(text) ~= "" then M.show(vim.trim(text), target) else require("sw.notepad").insert(true) end
  end)
end

return M
