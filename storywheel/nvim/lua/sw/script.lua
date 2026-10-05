-- Screenplays in the Writer: a story whose format is "screenplay" is one Fountain file (manuscript/script.fountain). The prose rules never
-- apply to it (blank lines mean something in Fountain). This module reads a script line by line the way storywheel/fountain.py does, and
-- gives the Writer its screenplay keys: Tab cycles the line's element, Enter knows what comes next, headings and cues are capitalized,
-- names and locations complete, the page is approximated with display-only indents, and the flip test lists what a reader would notice.
local story = require("sw.story")
local M = {}

M.ns = vim.api.nvim_create_namespace("sw_script")
M.WIDTH = { action = 60, heading = 60, dialogue = 35, parenthetical = 25, character = 38 }
M.INDENT = { character = 22, parenthetical = 16, dialogue = 10 }     -- display columns from the action margin (3.7", 3.1", 2.5" against 1.5")
M.LINES_PER_PAGE = 55
M.CYCLE = { "action", "character", "parenthetical", "dialogue", "transition" }

vim.api.nvim_set_hl(0, "SwScriptHeading", { bold = true, default = true })
vim.api.nvim_set_hl(0, "SwScriptNote", { link = "Comment", default = true })

-- --- is this a script? ---------------------------------------------------------------------------------------------------------

function M.is_script(buf)
  buf = (buf == nil or buf == 0) and vim.api.nvim_get_current_buf() or buf
  if not vim.api.nvim_buf_is_valid(buf) then return false end
  return vim.api.nvim_buf_get_name(buf):match("%.fountain$") ~= nil
end

-- --- reading a script (the same rules as storywheel/fountain.py) -----------------------------------------------------------------

local function trim(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end

function M.is_heading(s)
  if s:match("^%.[^%.]") then return true end
  local l = s:lower()
  for _, p in ipairs({ "int", "ext", "est", "int%.?/ext", "i/e", "e/i" }) do
    if l:match("^" .. p .. "[%. ]") or l:match("^" .. p .. "$") then return true end
  end
  return false
end

local function is_upper(s)
  return s:find("%a") ~= nil and s:find("%l") == nil
end

function M.is_transition(s)
  return s:match("^[A-Z0-9 %.,'%-]+TO:$") ~= nil
end

-- "MARA (V.O.) ^" -> "MARA", "(V.O.)", true
function M.split_cue(s)
  s = trim(s)
  local dual = s:sub(-1) == "^"
  if dual then s = trim(s:sub(1, -2)) end
  if s:sub(1, 1) == "@" then s = s:sub(2) end
  local name, ext = s, ""
  while true do
    local before, group = name:match("^(.-)%s*(%b())$")
    if not before then break end
    ext = group .. (ext ~= "" and (" " .. ext) or "")
    name = before
  end
  return trim(name), ext, dual
end

function M.is_cue(s)
  s = trim(s)
  if s == "" or s:match("^[!>%.#=~]") then return false end
  if s:sub(1, 1) == "@" then return #s > 1 end
  local name = M.split_cue(s)
  return is_upper(name) and not M.is_transition(s) and not M.is_heading(s)
end

-- The element of every line: title, blank, heading, action, character, parenthetical, dialogue, transition, centered, page_break,
-- section, synopsis, lyrics. `live_row` (optional) is a line being typed: it counts as text, so the cue above it reads as a cue.
-- Lines with the boneyard (/* ... */) and notes ([[ ... ]]) taken out: they print nothing (their lines stay, empty).
function M.without_notes(lines)
  local out, inside = {}, false
  for i, l in ipairs(lines) do
    local s = l
    if inside then
      local e = s:find("*/", 1, true)
      if e then s = s:sub(e + 2) inside = false else s = "" end
    end
    while true do
      local a = s:find("/*", 1, true)
      if not a then break end
      local e = s:find("*/", a + 2, true)
      if e then s = s:sub(1, a - 1) .. s:sub(e + 2) else s = s:sub(1, a - 1) inside = true break end
    end
    s = s:gsub("%[%[.-%]%]", "")
    out[i] = s
  end
  return out
end

function M.types(lines, live_row)
  lines = M.without_notes(lines)
  local n = #lines
  local t = {}
  local function blank(k) return k < 1 or k > n or not lines[k]:match("%S") end
  local function filled(k) return not blank(k) or (live_row ~= nil and k == live_row) end
  local i = 1
  if n > 0 and lines[1]:match("^%a[%a ]*:") then
    while i <= n and lines[i]:match("%S") do t[i] = "title" i = i + 1 end
  end
  while i <= n do
    local s = trim(lines[i]:gsub("\t", "    "))
    if s == "" then t[i] = "blank" i = i + 1
    elseif s:match("^===+$") then t[i] = "page_break" i = i + 1
    elseif s:sub(1, 1) == "#" then t[i] = "section" i = i + 1
    elseif s:sub(1, 1) == "=" and s:sub(1, 2) ~= "==" then t[i] = "synopsis" i = i + 1
    elseif s:sub(1, 1) == ">" and s:sub(-1) == "<" then t[i] = "centered" i = i + 1
    elseif s:sub(1, 1) == ">" then t[i] = "transition" i = i + 1
    elseif s:sub(1, 1) == "~" then t[i] = "lyrics" i = i + 1
    elseif blank(i - 1) and M.is_heading(s) and (blank(i + 1) or s:match("^%.[^%.]")) then t[i] = "heading" i = i + 1
    elseif blank(i - 1) and blank(i + 1) and M.is_transition(s) then t[i] = "transition" i = i + 1
    elseif blank(i - 1) and filled(i + 1) and M.is_cue(s) then
      t[i] = "character"
      i = i + 1
      while i <= n and (lines[i]:match("%S") or lines[i] == "  ") do
        local u = trim(lines[i])
        t[i] = (u:sub(1, 1) == "(" and u:sub(-1) == ")") and "parenthetical" or "dialogue"
        i = i + 1
      end
    else
      while i <= n and lines[i]:match("%S") do t[i] = "action" i = i + 1 end
    end
  end
  return t
end

-- Scenes: { n=, title=, start=, finish=, body=, section=, first_line=, label=, marked=true }
function M.scenes(lines)
  local t = M.types(lines)
  local out, sections = {}, {}
  local function section_text()
    local keys = vim.tbl_keys(sections)
    table.sort(keys)
    local parts = {}
    for _, k in ipairs(keys) do parts[#parts + 1] = sections[k] end
    return table.concat(parts, " / ")
  end
  for i, kind in ipairs(t) do
    if kind == "section" then
      local level = #(lines[i]:match("^%s*(#+)") or "#")
      sections[level] = trim(lines[i]:gsub("^%s*#+", ""))
      for k in pairs(sections) do if k > level then sections[k] = nil end end
    elseif kind == "heading" then
      if #out > 0 then out[#out].finish = i - 1 end
      local title = trim(lines[i]):gsub("^%.", ""):upper()
      out[#out + 1] = { n = #out + 1, title = title, label = title, start = i, finish = #lines, body = math.min(i + 2, #lines),
                        section = section_text(), first_line = "", marked = true, words = 0 }
    elseif #out > 0 and out[#out].first_line == "" and (kind == "action" or kind == "dialogue") then
      out[#out].first_line = trim(lines[i])
    end
  end
  for _, sc in ipairs(out) do
    local text = table.concat(vim.list_slice(lines, sc.start, sc.finish), "\n")
    sc.words = require("sw.util").count_words(text)
  end
  return out
end

-- The characters (from the cues) and locations (from the headings) of a script, in order of first use.
function M.names(lines)
  local t = M.types(lines)
  local chars, places, seen_c, seen_p = {}, {}, {}, {}
  for i, kind in ipairs(t) do
    if kind == "character" then
      local name = M.split_cue(lines[i])
      if name ~= "" and not seen_c[name] then seen_c[name] = true chars[#chars + 1] = name end
    elseif kind == "heading" then
      local loc = trim(lines[i]):gsub("^%.", ""):gsub("^%a+%.?/?%a*%.?%s+", "")
      local parts = vim.split(loc, "%s+%-%s+")
      if #parts > 1 then table.remove(parts) end
      loc = trim(table.concat(parts, " - ")):upper()
      if loc ~= "" and not seen_p[loc] then seen_p[loc] = true places[#places + 1] = loc end
    end
  end
  return chars, places
end

-- --- the page estimate ---------------------------------------------------------------------------------------------------------

-- How many printed lines a piece of text takes at `width` characters, broken between words.
function M.wrapped(text, width)
  local count = 0
  for _, piece in ipairs(vim.split(text, "\n", { plain = true })) do
    local n, used = 1, 0
    for word in piece:gmatch("%S+") do
      local w = vim.fn.strchars(word)
      if used == 0 then used = w
      elseif used + 1 + w <= width then used = used + 1 + w
      else n = n + 1 used = w end
      while used > width do n = n + 1 used = used - width end
    end
    count = count + n
  end
  return count
end

-- Printed lines (blank lines between elements included) and the line each script line starts on. Close to storywheel/screenplay_pdf.py:
-- it does not move speeches between pages, so it can run a little short on scripts with many long speeches.
function M.layout(lines)
  local t = M.types(lines)
  local total, at = 0, {}
  local i, n = 1, #lines
  local function add(space, count, row)
    if total > 0 then total = total + space end
    at[row] = total
    total = total + count
  end
  while i <= n do
    local kind = t[i]
    if kind == "heading" then add(2, M.wrapped(trim(lines[i]), M.WIDTH.heading), i) i = i + 1
    elseif kind == "action" or kind == "lyrics" then
      local j, buf = i, {}
      while j <= n and t[j] == kind do buf[#buf + 1] = trim(lines[j]) j = j + 1 end
      add(1, M.wrapped(table.concat(buf, "\n"), M.WIDTH.action), i)
      i = j
    elseif kind == "character" then
      local count, j = 1, i + 1
      while j <= n and (t[j] == "dialogue" or t[j] == "parenthetical") do
        count = count + M.wrapped(trim(lines[j]), t[j] == "dialogue" and M.WIDTH.dialogue or M.WIDTH.parenthetical)
        j = j + 1
      end
      add(1, count, i)
      i = j
    elseif kind == "transition" or kind == "centered" then add(1, 1, i) i = i + 1
    elseif kind == "page_break" then
      if total % M.LINES_PER_PAGE ~= 0 then total = total + (M.LINES_PER_PAGE - total % M.LINES_PER_PAGE) end
      at[i] = total
      i = i + 1
    else i = i + 1 end
  end
  return total, at
end

function M.estimate_pages(lines)
  local total = M.layout(lines)
  return math.floor(total / M.LINES_PER_PAGE * 1.04 * 10 + 0.5) / 10       -- (1.04: what moving speeches and keeping headings adds)
end

function M.target()
  return tonumber(story.info.target_pages) or tonumber(story.setting("target_pages", 0)) or 0
end

-- "p. 12 of ~15": the script's estimated length against its target.
function M.status(buf)
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local pages = M.estimate_pages(lines)
  local target = M.target()
  local p = math.max(1, math.ceil(pages))
  if target and target > 0 then return string.format("p. %d of ~%d", p, target) end
  return string.format("p. %d", p)
end

-- --- the page on screen: display-only indents ---------------------------------------------------------------------------------

function M.decorate(buf)
  buf = buf or vim.api.nvim_get_current_buf()
  if not vim.api.nvim_buf_is_valid(buf) then return end
  vim.api.nvim_buf_clear_namespace(buf, M.ns, 0, -1)
  vim.api.nvim_buf_clear_namespace(buf, require("sw.prose").ns, 0, -1)
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local live
  local win = vim.fn.bufwinid(buf)
  if win ~= -1 and vim.fn.mode():match("^i") then live = vim.api.nvim_win_get_cursor(win)[1] end
  local t = M.types(lines, live)
  for i, kind in ipairs(t) do
    local line = lines[i]
    local pad
    if M.INDENT[kind] then pad = M.INDENT[kind]
    elseif kind == "transition" then pad = math.max(0, M.WIDTH.action - vim.fn.strdisplaywidth(trim(line)))
    elseif kind == "centered" then pad = math.max(0, math.floor((M.WIDTH.action - vim.fn.strdisplaywidth(trim(line))) / 2)) end
    if pad and pad > 0 then
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, { virt_text = { { string.rep(" ", pad), "Normal" } }, virt_text_pos = "inline" })
    end
    if kind == "heading" then
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, { end_row = i - 1, end_col = #line, hl_group = "SwScriptHeading" })
    elseif kind == "section" or kind == "synopsis" or kind == "title" then
      vim.api.nvim_buf_set_extmark(buf, M.ns, i - 1, 0, { end_row = i - 1, end_col = #line, hl_group = "SwScriptNote" })
    end
  end
end

-- --- editing --------------------------------------------------------------------------------------------------------------------

local function set_lines(buf, a, b, new) vim.api.nvim_buf_set_lines(buf, a, b, false, new) end

-- The text of a line without the markers that force an element (!, @, ., >, <, the brackets of a parenthetical).
function M.bare(line)
  local s = trim(line)
  s = s:gsub("^[!@]", ""):gsub("^>%s*", ""):gsub("%s*<$", "")
  if s:match("^%.[^%.]") then s = s:sub(2) end
  if s:sub(1, 1) == "(" and s:sub(-1) == ")" then s = s:sub(2, -2) end
  return trim(s)
end

-- Make line `row` (1-based) an element of `kind`, fixing the blank lines around it so Fountain reads it that way. Returns the new row and
-- the column for the cursor.
function M.set_element(buf, row, kind)
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local t = M.types(lines, row)
  local text = M.bare(lines[row] or "")
  local function in_speech(k) return t[k] == "character" or t[k] == "dialogue" or t[k] == "parenthetical" end
  local prev = lines[row - 1]
  local new, col
  if kind == "character" or kind == "transition" or kind == "action" then
    if kind == "character" then
      new = text:upper()
      col = #new
    elseif kind == "transition" then
      new = text:upper()
      if not new:match("TO:$") then new = "> " .. new end
      col = #new
    else
      new = text
      if is_upper(new) and (M.is_cue(new) or M.is_heading(new) or M.is_transition(new)) then new = "!" .. new end
      col = #new
    end
    set_lines(buf, row - 1, row, { new })
    if prev and prev:match("%S") then                          -- these stand apart: a blank line before
      set_lines(buf, row - 1, row - 1, { "" })
      row = row + 1
    end
    if kind == "transition" then
      local nxt = vim.api.nvim_buf_get_lines(buf, row, row + 1, false)[1]
      if nxt and nxt:match("%S") then set_lines(buf, row, row, { "" }) end
    end
  else
    new = kind == "parenthetical" and ("(" .. text .. ")") or text
    col = kind == "parenthetical" and (#new - 1) or #new
    set_lines(buf, row - 1, row, { new })
    -- part of a speech: no blank line between it and the cue or line above
    if prev and not prev:match("%S") and row > 2 and in_speech(row - 2) then
      set_lines(buf, row - 2, row - 1, {})
      row = row - 1
    end
  end
  return row, col
end

-- Tab: the next element in the cycle (action, character, parenthetical, dialogue, transition). An empty line starts as a character cue.
function M.tab()
  local buf = vim.api.nvim_get_current_buf()
  local row = vim.api.nvim_win_get_cursor(0)[1]
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local kind = M.types(lines, row + 1)[row] or "action"          -- (the line being typed: what it says it is, as if words followed)
  local last = M.last_tab
  if last and last.buf == buf and last.row == row and last.text == lines[row] then
    kind = last.kind                                              -- (pressing Tab again: go on from what the last Tab made it)
  end
  if kind == "blank" then kind = "action" end
  local next_kind = "action"
  for i, k in ipairs(M.CYCLE) do
    if k == kind then next_kind = M.CYCLE[i % #M.CYCLE + 1] end
  end
  local r, c = M.set_element(buf, row, next_kind)
  vim.api.nvim_win_set_cursor(0, { r, c })
  M.last_tab = { buf = buf, row = r, text = vim.api.nvim_buf_get_lines(buf, r - 1, r, false)[1], kind = next_kind }
  M.decorate(buf)
  vim.api.nvim_echo({ { next_kind, "Comment" } }, false, {})
  return next_kind
end

-- Is this (as typed) the name of a character the script or the universe already knows?
function M.known_cue(lines, s)
  local name = M.split_cue(s):lower()
  if name == "" then return false end
  local chars = M.names(lines)
  for _, c in ipairs(chars) do if c:lower() == name then return true end end
  for _, e in ipairs(require("sw.world").entities or {}) do
    if e.type == "character" and e.name then
      local first = (vim.split(e.name, "%s+", { trimempty = true })[1] or ""):lower()
      if e.name:lower() == name or first == name then return true end
    end
  end
  return false
end

-- Headings and cues are capitalized when you leave them.
function M.capitalize(buf, row)
  local line = vim.api.nvim_buf_get_lines(buf, row - 1, row, false)[1]
  if not line or not line:match("%S") then return end
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local above_blank = row == 1 or not lines[row - 1]:match("%S")
  local s = trim(line)
  local up
  if above_blank and M.is_heading(s) and not s:match("^%.") then
    up = line:upper()
  elseif above_blank and (lines[row + 1] or ""):match("%S") then
    local name = M.split_cue(s)
    local chars = M.names(lines)
    for _, c in ipairs(chars) do if c:lower() == name:lower() then up = line:upper() end end
    if not up then
      local world = require("sw.world")
      for _, e in ipairs(world.entities or {}) do
        if e.type == "character" and e.name and e.name:lower() == name:lower() then up = line:upper() end
      end
    end
  end
  if up and up ~= line then set_lines(buf, row - 1, row, { up }) end
end

-- Enter: after a cue or a parenthetical, the next line is dialogue (no blank line); after dialogue, action, a heading or a transition, a
-- blank line and then the next element. In the middle of a line, Enter just splits it.
function M.enter()
  local buf = vim.api.nvim_get_current_buf()
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  local line = vim.api.nvim_get_current_line()
  if col < #line or not line:match("%S") then
    set_lines(buf, row - 1, row, { line:sub(1, col), line:sub(col + 1) })
    vim.api.nvim_win_set_cursor(0, { row + 1, 0 })
    M.decorate(buf)
    return
  end
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local above_blank = row == 1 or not lines[row - 1]:match("%S")
  local kind = M.types(lines, row + 1)[row]
  local s = trim(line)
  if above_blank and kind ~= "heading" and kind ~= "transition" and kind ~= "parenthetical" and kind ~= "dialogue"
      and ((M.is_cue(s) and s:upper() == s) or M.known_cue(lines, s)) then
    kind = "character"
  end
  M.capitalize(buf, row)
  if kind == "character" then
    set_lines(buf, row - 1, row, { vim.api.nvim_buf_get_lines(buf, row - 1, row, false)[1]:upper() })
    set_lines(buf, row, row, { "" })
    vim.api.nvim_win_set_cursor(0, { row + 1, 0 })
  elseif kind == "parenthetical" then
    set_lines(buf, row, row, { "" })
    vim.api.nvim_win_set_cursor(0, { row + 1, 0 })
  else
    set_lines(buf, row, row, { "", "" })
    vim.api.nvim_win_set_cursor(0, { row + 2, 0 })
  end
  M.decorate(buf)
end

function M.enter_expr()
  if vim.fn.pumvisible() == 1 and vim.fn.complete_info({ "selected" }).selected >= 0 then
    return vim.api.nvim_replace_termcodes("<C-y>", true, false, true)
  end
  return vim.api.nvim_replace_termcodes("<Cmd>lua require('sw.script').enter()<CR>", true, false, true)
end

-- --- completion -----------------------------------------------------------------------------------------------------------------

-- At a cue (an uppercase line after a blank one) offer character names; after INT./EXT. offer locations. From the script and the universe.
function M.complete()
  if vim.fn.pumvisible() == 1 then return true end
  local buf = vim.api.nvim_get_current_buf()
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local line = lines[row] or ""
  if col ~= #line then return false end
  local above_blank = row == 1 or not lines[row - 1]:match("%S")
  if not above_blank then return false end
  local chars, places = M.names(lines)
  local world = require("sw.world")
  local head, loc = line:match("^(%s*%.?%a+%.?/?%a*%.?%s+)(.*)$")
  if head and M.is_heading(trim(head)) then
    if #loc < 1 then return true end
    local items, seen = {}, {}
    local pool = vim.deepcopy(places)
    for _, e in ipairs(world.entities or {}) do if e.type == "place" and e.name then pool[#pool + 1] = e.name:upper() end end
    for _, p in ipairs(pool) do
      if p:lower():sub(1, #loc) == loc:lower() and #p > #loc and not seen[p] then seen[p] = true items[#items + 1] = { word = p, menu = "[place]" } end
    end
    if #items > 0 then vim.fn.complete(col - #loc + 1, items) end
    return true
  end
  local typed = trim(line)
  if #typed < 2 or typed:find("[^%a%s'%.%-]") then return false end
  local items, seen = {}, {}
  local pool = vim.deepcopy(chars)
  for _, e in ipairs(world.entities or {}) do
    if e.type == "character" and e.name and e.name ~= "" then
      pool[#pool + 1] = (vim.split(e.name, "%s+", { trimempty = true })[1] or e.name):upper()
    end
  end
  for _, c in ipairs(pool) do
    if c:lower():sub(1, #typed) == typed:lower() and #c > #typed and not seen[c] then seen[c] = true items[#items + 1] = { word = c, menu = "[character]" } end
  end
  if #items > 0 then
    vim.fn.complete(col - #typed + 1, items)
    return true
  end
  return false
end

-- --- the flip test ------------------------------------------------------------------------------------------------------------

M.results = {}

function M.flip_test()
  local buf = vim.api.nvim_get_current_buf()
  if not M.is_script(buf) then
    vim.api.nvim_echo({ { "The flip test is for screenplays.", "Normal" } }, false, {})
    return {}
  end
  vim.api.nvim_buf_call(buf, function() vim.cmd("silent! write") end)
  local args = { "script", "check", vim.api.nvim_buf_get_name(buf), "--json" }
  local target = M.target()
  if target and target > 0 then vim.list_extend(args, { "--target-pages", tostring(target) }) end
  local data = require("sw.util").cli_json(args)
  M.results = (data and data.problems) or {}
  M.show_results(buf)
  return M.results
end

function M.show_results(buf)
  local lines = {}
  for _, d in ipairs(M.results) do lines[#lines + 1] = string.format(" %5d  %s", d.line, d.message) end
  if #lines == 0 then lines = { "  Nothing to flag: the script reads cleanly on a flip." } end
  local fbuf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(fbuf, 0, -1, false, lines)
  vim.bo[fbuf].modifiable = false
  local width = math.min(100, vim.o.columns - 4)
  local height = math.min(#lines, math.max(3, vim.o.lines - 8))
  local win = vim.api.nvim_open_win(fbuf, true, { relative = "editor", row = 2, col = math.floor((vim.o.columns - width) / 2),
    width = width, height = height, border = "rounded", title = " Flip test (Enter jumps, q closes) ", style = "minimal" })
  vim.wo[win].cursorline = true
  local main = vim.fn.bufwinid(buf)
  local function close() if vim.api.nvim_win_is_valid(win) then vim.api.nvim_win_close(win, true) end end
  local function jump()
    local d = M.results[vim.api.nvim_win_get_cursor(win)[1]]
    close()
    if d and main ~= -1 then
      vim.api.nvim_set_current_win(main)
      pcall(vim.api.nvim_win_set_cursor, main, { d.line, 0 })
    end
  end
  for _, k in ipairs({ "<CR>", "<2-LeftMouse>" }) do vim.keymap.set("n", k, jump, { buffer = fbuf, silent = true }) end
  for _, k in ipairs({ "q", "<Esc>" }) do vim.keymap.set("n", k, close, { buffer = fbuf, silent = true }) end
end

-- --- a script buffer's keys -------------------------------------------------------------------------------------------------------

function M.map_buffer(buf)
  local function map(mode, lhs, rhs, opts)
    vim.keymap.set(mode, lhs, rhs, vim.tbl_extend("force", { buffer = buf, silent = true }, opts or {}))
  end
  map("i", "<CR>", function() return M.enter_expr() end, { expr = true, replace_keycodes = false })
  map("i", "<Tab>", function()
    if vim.fn.pumvisible() == 1 then return vim.api.nvim_replace_termcodes("<C-n>", true, false, true) end
    return vim.api.nvim_replace_termcodes("<Cmd>lua require('sw.script').tab()<CR>", true, false, true)
  end, { expr = true, replace_keycodes = false })
  map({ "n", "i" }, story.setting("key_flip_test", "<A-f>"), function() M.flip_test() end)
  vim.api.nvim_create_autocmd({ "InsertLeave", "CursorMovedI" }, {
    group = vim.api.nvim_create_augroup("sw_script_" .. buf, { clear = true }), buffer = buf,
    callback = function(ev)
      local row = vim.api.nvim_win_get_cursor(0)[1]
      if ev.event == "CursorMovedI" then
        if M.last_row and M.last_row ~= row then M.capitalize(buf, M.last_row) end
        M.last_row = row
      else
        M.capitalize(buf, row)
      end
    end })
end

return M
