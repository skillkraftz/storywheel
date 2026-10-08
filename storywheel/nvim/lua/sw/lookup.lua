-- Dictionary and thesaurus card (F7 on the word under the cursor or a selection, F6 for a typed word; also in the menus).
-- One scrollable card: meanings by part of speech, each with its own similar words; then the full broad list of similar words;
-- opposite words, then the indirect ones (opposites of similar words); a filter narrows every list.
-- Keys in the card: Enter looks the word under the cursor up (b goes back, n forward), r replaces the word that was under the
-- cursor when you opened the card (in the same form: running -> sprinting), i inserts at the cursor, c copies, / filters.
-- The data comes from `storywheel lookup WORD --json` (offline); the form from `storywheel inflect`.
local util = require("sw.util")
local M = {}

M.WIDTH = 80
M.ns = vim.api.nvim_create_namespace("sw_lookup")

-- --- the word at the cursor ---------------------------------------------------------------------------------------------------

-- The word at the cursor (or in a one-line selection): returns word, { row0, start_col, end_col } or nil.
function M.word_at_cursor()
  local notepad = require("sw.notepad")
  if notepad.has_selection() then
    local text = notepad.selected_text()
    local r1, c1, r2, c2 = require("sw.prose").selection_bounds()
    if text and r1 == r2 and text:match("%S") then
      local trimmed = vim.trim(text)
      local lead = #text - #text:gsub("^%s+", "")
      vim.cmd("normal! \27")
      return trimmed, { r1, c1 + lead, c1 + lead + #trimmed }
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

-- --- the data ---------------------------------------------------------------------------------------------------------------------

-- Ask the CLI. Returns the decoded result, or nil and a message.
function M.fetch(word)
  local out = vim.fn.system(util.cli({ "lookup", word, "--json" }))
  local ok, data = pcall(vim.json.decode, out)
  if not ok or type(data) ~= "table" then return nil, "The dictionary lookup failed (is storywheel installed for python3?)." end
  if data.installed == false then return nil, "No dictionary yet: run  storywheel dictionary install" end
  if data.error then return nil, data.error end
  return data
end

-- A problem with a lookup, as one line that fits the screen (a longer message wraps mid-word and waits for Enter).
function M.warn(err)
  local room = math.max(20, vim.o.columns - 12)
  if vim.fn.strdisplaywidth(err) > room then err = vim.fn.strcharpart(err, 0, room - 1) .. "…" end
  vim.api.nvim_echo({ { err, "WarningMsg" } }, true, {})
end

local function nz(v)
  if v == vim.NIL then return nil end
  return v
end

-- The chosen word in the same form as the original ("running" was a form of "run": sprint -> sprinting), unless it needs no change.
function M.inflected(word, pos)
  local o = M.origin
  if not o or not o.base or not o.kind or o.kind == "base" then return word end
  local args = { "inflect", o.text, o.base, word }
  if pos then vim.list_extend(args, { "--pos", pos }) end
  local out = vim.fn.system(util.cli(args))
  if vim.v.shell_error ~= 0 then return word end
  out = vim.trim(out)
  return out ~= "" and out or word
end

-- --- building the card --------------------------------------------------------------------------------------------------------

local function wrap_plain(text, width, indent)
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

-- The card as lines plus the words on them: { lines = {...}, spans = { [line] = { {s=, e=, word=, pos=, group=}, ... } } }.
-- Words are wrapped like text; the span under the cursor is the word you can pick.
function M.build(result, filter)
  local lines, spans, group = {}, {}, 0
  local f = filter and filter ~= "" and filter:lower() or nil
  local function add(text) lines[#lines + 1] = text end
  local function add_words(items, indent)             -- items: { {word=, pos=, note=}, ... }
    group = group + 1
    local cur, row = indent, {}
    local function flush()
      if #row > 0 then
        lines[#lines + 1] = cur
        spans[#lines] = row
      end
      cur, row = indent, {}
    end
    local shown = 0
    for _, it in ipairs(items) do
      if not f or it.word:lower():find(f, 1, true) then
        shown = shown + 1
        local label = it.word .. (it.note and (" (" .. it.note .. ")") or "")
        if #row > 0 and #cur + #label + 2 > M.WIDTH - 1 then flush() end
        local s = #cur
        cur = cur .. label .. "  "
        row[#row + 1] = { s = s, e = s + #it.word, word = it.word, pos = it.pos, group = group }
      end
    end
    flush()
    return shown
  end
  local function words(list, pos)
    local out = {}
    for _, w in ipairs(list or {}) do out[#out + 1] = { word = w, pos = pos } end
    return out
  end

  if not result.found then
    add(" No entry for '" .. (result.word ~= "" and result.word or result.query) .. "'.")
    if #result.suggestions > 0 then
      add("")
      add(" Did you mean (Enter looks it up):")
      add_words(words(result.suggestions), "   ")
    end
    return { lines = lines, spans = spans }
  end
  for _, e in ipairs(result.entries) do
    local form_of = nz(e.form_of)
    add(" " .. e.word .. (form_of and ("   (form of “" .. form_of .. "”)") or ""))
    for _, part in ipairs(e.parts) do
      add(" " .. part.pos)
      for i, s in ipairs(part.senses) do
        for _, l in ipairs(wrap_plain(i .. ". " .. s.definition, M.WIDTH - 2, "   ")) do add(l) end
        if s.examples[1] then add("      “" .. s.examples[1] .. "”") end
        if #s.kind_of > 0 then add("      a kind of: " .. table.concat(s.kind_of, ", ")) end
        if #s.synonyms > 0 then
          local n = add_words(words(s.synonyms, part.pos), "      ")
          if f and n == 0 then add("      (none match the filter)") end
        end
      end
    end
    add("")
    if #e.wide_synonyms > 0 then
      add(" More similar words (" .. #e.wide_synonyms .. ")")
      local n = add_words(words(e.wide_synonyms), "   ")
      if f and n == 0 then add("   (none match the filter)") end
      add("")
    end
    if #e.antonyms > 0 then
      add(" Opposite words")
      add_words(words(e.antonyms), "   ")
      add("")
    end
    if #e.indirect_antonyms > 0 then
      add(" Opposite words, indirect (opposites of similar words)")
      local items = {}
      for _, a in ipairs(e.indirect_antonyms) do items[#items + 1] = { word = a.word, note = a.via } end
      add_words(items, "   ")
      add("")
    end
    local related = {}
    for kind, list in pairs(e.related_forms) do for _, w in ipairs(list) do related[#related + 1] = { word = w, note = kind } end end
    if #related > 0 then
      add(" Related forms")
      add_words(related, "   ")
      add("")
    end
  end
  add(" Open English WordNet (CC BY 4.0); Moby Thesaurus (public domain)")
  return { lines = lines, spans = spans }
end

-- --- showing it -----------------------------------------------------------------------------------------------------------------

local function first_span(card)
  for i = 1, #card.lines do
    if card.spans[i] then return i, card.spans[i][1] end
  end
end

function M.span_at(line, col)
  local row = M.card and M.card.spans[line]
  if not row then return nil end
  for _, sp in ipairs(row) do
    if col >= sp.s and col <= sp.e then return sp end
  end
  local best, dist = nil, 1e9
  for _, sp in ipairs(row) do
    local d = math.min(math.abs(col - sp.s), math.abs(col - sp.e))
    if d < dist then best, dist = sp, d end
  end
  return best
end

function M.current()
  if not (M.win and vim.api.nvim_win_is_valid(M.win)) then return nil end
  local c = vim.api.nvim_win_get_cursor(M.win)
  return M.span_at(c[1], c[2])
end

local function highlight()
  if not (M.buf and vim.api.nvim_buf_is_valid(M.buf)) then return end
  vim.api.nvim_buf_clear_namespace(M.buf, M.ns, 0, -1)
  local sp = M.current()
  if sp then
    local line = vim.api.nvim_win_get_cursor(M.win)[1] - 1
    vim.api.nvim_buf_set_extmark(M.buf, M.ns, line, sp.s, { end_col = sp.e, hl_group = "PmenuSel" })
  end
end

local function title()
  local r = M.result
  local name = (r and r.found and r.entries[1].word) or (r and r.word) or "Look up"
  local extra = (M.filter and M.filter ~= "") and ("  ·  filter: " .. M.filter) or ""
  local hist = #M.history > 1 and ("  [" .. M.pos .. "/" .. #M.history .. "]") or ""
  return " " .. name .. hist .. extra .. " "
end

local function footer()
  local keys = " Enter look up · b back · r replace · i insert · c copy · / filter · w new word · Esc close "
  if not M.origin or not M.target then keys = " Enter look up · b back · i insert · c copy · / filter · w new word · Esc close " end
  return keys
end

function M.render(keep_cursor)
  local card = M.build(M.result, M.filter)
  M.card = card
  vim.bo[M.buf].modifiable = true
  vim.api.nvim_buf_set_lines(M.buf, 0, -1, false, card.lines)
  vim.bo[M.buf].modifiable = false
  vim.api.nvim_win_set_config(M.win, { title = title(), title_pos = "center", footer = footer(), footer_pos = "center" })
  if not keep_cursor then
    local l, sp = first_span(card)
    vim.api.nvim_win_set_cursor(M.win, { l or 1, sp and sp.s or 0 })
  end
  highlight()
end

local function ensure_window()
  if M.win and vim.api.nvim_win_is_valid(M.win) then return end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.bo[buf].bufhidden = "wipe"
  vim.bo[buf].modifiable = false
  local height = math.max(8, vim.o.lines - 8)
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", row = 2, col = math.max(0, math.floor((vim.o.columns - M.WIDTH) / 2)), width = M.WIDTH, height = height,
    style = "minimal", border = "rounded", title = " Look up ", title_pos = "center", footer = footer(), footer_pos = "center",
  })
  vim.wo[win].cursorline = false
  vim.wo[win].wrap = false
  M.win, M.buf = win, buf
  vim.cmd("stopinsert")
  M.map_keys(buf)
  vim.api.nvim_create_autocmd("CursorMoved", { buffer = buf, callback = highlight })
  vim.api.nvim_create_autocmd("WinClosed", { pattern = tostring(win), once = true, callback = function() M.win = nil end })
end

-- --- moving about and picking ----------------------------------------------------------------------------------------------------

local function all_spans()
  local out = {}
  for l = 1, #M.card.lines do
    for _, sp in ipairs(M.card.spans[l] or {}) do out[#out + 1] = { l, sp } end
  end
  return out
end

local function go_to(entry)
  if entry then vim.api.nvim_win_set_cursor(M.win, { entry[1], entry[2].s }) end
end

local function step(dir)                           -- the next / previous word
  local list = all_spans()
  local c = vim.api.nvim_win_get_cursor(M.win)
  local cur = M.span_at(c[1], c[2])
  for i, it in ipairs(list) do
    if it[1] == c[1] and it[2] == cur then go_to(list[i + dir]) return end
  end
  go_to(list[1])
end

local function vertical(dir)                       -- the nearest word on the next line that has words
  local c = vim.api.nvim_win_get_cursor(M.win)
  local l = c[1] + dir
  while l >= 1 and l <= #M.card.lines do
    if M.card.spans[l] then
      local sp = M.span_at(l, c[2])
      vim.api.nvim_win_set_cursor(M.win, { l, sp.s })
      return
    end
    l = l + dir
  end
end

local function next_section()
  local c = vim.api.nvim_win_get_cursor(M.win)
  local cur = M.span_at(c[1], c[2])
  for _, it in ipairs(all_spans()) do
    if cur and it[2].group > cur.group then go_to(it) return end
  end
  go_to(all_spans()[1])
end

function M.close()
  if M.win and vim.api.nvim_win_is_valid(M.win) then vim.api.nvim_win_close(M.win, true) end
  M.win = nil
  local layout = require("sw.layout")
  if layout.main and vim.api.nvim_win_is_valid(layout.main) then vim.api.nvim_set_current_win(layout.main) end
end

local function leave()
  M.close()
  require("sw.notepad").insert(true)
end

-- r: replace the word that was under the cursor when the card was opened, in the same form, keeping capitalization
function M.replace(word, pos)
  local target, original = M.target, M.origin and M.origin.text
  if not target or not original then
    vim.api.nvim_echo({ { "Nothing to replace: no word was under the cursor when you opened the card. Use i to insert it.", "WarningMsg" } }, true, {})
    return false
  end
  local new = M.apply_case(original, M.inflected(word, pos))
  local layout = require("sw.layout")
  M.close()
  local buf = vim.api.nvim_win_get_buf(layout.main)
  local row, s, e = target[1], target[2], target[3]
  local now = vim.api.nvim_buf_get_text(buf, row, s, row, e, {})[1]
  if now ~= original then
    vim.api.nvim_echo({ { "The text changed since you looked it up; nothing replaced.", "WarningMsg" } }, true, {})
  else
    vim.api.nvim_buf_set_text(buf, row, s, row, e, { new })
    vim.api.nvim_win_set_cursor(layout.main, { row + 1, s + #new })
  end
  require("sw.notepad").insert(true)
  return true
end

-- i: insert the word at the cursor (where it was when the card was opened)
function M.insert(word)
  local layout = require("sw.layout")
  local c = M.cursor or vim.api.nvim_win_get_cursor(layout.main)
  M.close()
  local buf = vim.api.nvim_win_get_buf(layout.main)
  vim.api.nvim_buf_set_text(buf, c[1] - 1, c[2], c[1] - 1, c[2], { word })
  vim.api.nvim_win_set_cursor(layout.main, { c[1], c[2] + #word })
  require("sw.notepad").insert(true)
end

function M.copy(word)
  pcall(vim.fn.setreg, "+", word)
  pcall(vim.fn.setreg, '"', word)
  vim.api.nvim_echo({ { "Copied “" .. word .. "”.", "Normal" } }, true, {})
end

function M.map_keys(buf)
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  local function with_word(fn)
    return function()
      local sp = M.current()
      if sp then fn(sp) else vim.api.nvim_echo({ { "Move to a word first.", "Normal" } }, false, {}) end
    end
  end
  map("<CR>", with_word(function(sp) M.lookup(sp.word) end))
  map("<2-LeftMouse>", with_word(function(sp) M.lookup(sp.word) end))
  map("<LeftMouse>", function()
    local pos = vim.fn.getmousepos()
    if pos.winid ~= M.win then leave() return end
    vim.api.nvim_win_set_cursor(M.win, { math.max(1, pos.line), math.max(0, pos.column - 1) })
  end)
  map("r", with_word(function(sp) M.replace(sp.word, sp.pos) end))
  map("i", with_word(function(sp) M.insert(sp.word) end))
  map("c", with_word(function(sp) M.copy(sp.word) end))
  map("b", function() M.back() end)
  map("<BS>", function() M.back() end)
  map("n", function() M.forward() end)
  map("/", function() M.ask_filter() end)
  map("w", function() M.ask_word() end)
  map("<Tab>", next_section)
  map("<Right>", function() step(1) end)
  map("l", function() step(1) end)
  map("<Left>", function() step(-1) end)
  map("h", function() step(-1) end)
  map("<Down>", function() vertical(1) end)
  map("j", function() vertical(1) end)
  map("<Up>", function() vertical(-1) end)
  map("k", function() vertical(-1) end)
  map("<PageDown>", "<C-d>")
  map("<PageUp>", "<C-u>")
  map("<Esc>", function()
    if M.filter and M.filter ~= "" then M.filter = "" M.render() else leave() end
  end)
  map("q", leave)
end

-- --- looking things up ------------------------------------------------------------------------------------------------------------

-- Look a word up in the open card (adds to the history unless it is the one shown).
function M.lookup(word, from_history)
  local result, err = M.fetch(word)
  if not result then
    M.warn(err)
    return false
  end
  ensure_window()
  M.result = result
  M.filter = ""
  if not from_history then
    for i = #M.history, M.pos + 1, -1 do M.history[i] = nil end        -- a new word after going back drops the old forward trail
    M.history[#M.history + 1] = word
    M.pos = #M.history
  end
  M.render()
  return true
end

function M.back()
  if M.pos > 1 then M.pos = M.pos - 1 M.lookup(M.history[M.pos], true)
  else vim.api.nvim_echo({ { "That is the first word you looked up.", "Normal" } }, false, {}) end
end

function M.forward()
  if M.pos < #M.history then M.pos = M.pos + 1 M.lookup(M.history[M.pos], true)
  else vim.api.nvim_echo({ { "That is the last word you looked up.", "Normal" } }, false, {}) end
end

function M.ask_filter()
  vim.ui.input({ prompt = "Show only words containing: ", default = M.filter or "" }, function(text)
    if text ~= nil and M.win and vim.api.nvim_win_is_valid(M.win) then
      M.filter = vim.trim(text)
      M.render()
    end
  end)
end

function M.ask_word()
  vim.ui.input({ prompt = "Look up: " }, function(text)
    if text and vim.trim(text) ~= "" and M.win and vim.api.nvim_win_is_valid(M.win) then M.lookup(vim.trim(text)) end
  end)
end

-- Open the card for `word`. `origin` is the word to be replaced (the text under the cursor) with its range `target`.
function M.show(word, target, origin_text)
  M.history, M.pos, M.filter = {}, 0, ""
  M.target = target
  local layout = require("sw.layout")
  M.cursor = vim.api.nvim_win_get_cursor(layout.main)
  M.origin = nil
  local first, err = M.fetch(word)
  if not first then
    M.warn(err)
    return false
  end
  -- what form the original is in (running = the -ing form of run), for putting a replacement in the same form
  if origin_text then
    local o = origin_text == word and first or M.fetch(origin_text)
    if o then M.origin = { text = origin_text, base = o.base, kind = o.form_kind } end
  end
  M.close()
  ensure_window()
  M.result = first
  M.history = { word }
  M.pos = 1
  M.render()
  return true
end

-- F7: the word under the cursor (or the selection).
function M.word()
  local word, target = M.word_at_cursor()
  if not word then
    vim.api.nvim_echo({ { "Put the cursor on a word first (or select one), or press the other lookup key to type a word.", "Normal" } }, true, {})
    return false
  end
  return M.show(word, target, word)
end

-- F6: a typed word; the word under the cursor (if any) is what r replaces.
function M.ask(_unused)
  local word, target = M.word_at_cursor()
  vim.ui.input({ prompt = "Look up: " }, function(text)
    if text and vim.trim(text) ~= "" then
      M.show(vim.trim(text), target, word)
    else
      require("sw.notepad").insert(true)
    end
  end)
end

return M
