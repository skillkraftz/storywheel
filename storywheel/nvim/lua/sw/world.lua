-- The universe inside the Writer: peek at the character or place under the cursor, and complete their names.
local util = require("sw.util")
local story = require("sw.story")
local M = {}

M.entities = {}
M.names = {}        -- { text=, entity= }, longest first

function M.load()
  M.entities, M.names = {}, {}
  if not story.universe then return end
  local data = util.cli_json({ "entity", "list", story.universe, "--json" })
  if not data then return end
  M.entities = data
  M.index()
end

-- A proper name is a person's or place's name ("Stacie Gise", "Red Draw"), not a description ("a locked box").
local function is_proper(e)
  if e.proper ~= nil and e.proper ~= vim.NIL then return e.proper end
  return e.type ~= "thing" and e.name:match("^%u") ~= nil
end
M.is_proper = is_proper

function M.index()
  M.names = {}
  M.words = {}          -- lowercase word -> { word = "Gise", entity = e }, for the words of proper names
  for _, e in ipairs(M.entities) do
    if e.type ~= "note" and e.name and e.name ~= "" and is_proper(e) then
      for _, w in ipairs(vim.split(e.name, "[%s]+", { trimempty = true })) do
        local clean = w:gsub("^[%p]+", ""):gsub("[%p]+$", "")
        if #clean >= 3 and clean:match("^%u") then M.words[clean:lower()] = M.words[clean:lower()] or { word = clean, entity = e } end
      end
    end
    if e.type ~= "note" and e.name and e.name ~= "" then
      M.names[#M.names + 1] = { text = e.name, entity = e }
      local words = vim.split(e.name, "%s+", { trimempty = true })
      if #words > 1 then
        for _, w in ipairs({ words[1], words[#words] }) do
          if #w >= 3 then M.names[#M.names + 1] = { text = w, entity = e, partial = true } end
        end
      end
    end
  end
  table.sort(M.names, function(a, b) return #a.text > #b.text end)
end

-- The entity whose name covers the cursor (the longest match wins). Returns entity, start col, end col.
function M.at_cursor(line, col)
  line = line or vim.api.nvim_get_current_line()
  col = col or vim.api.nvim_win_get_cursor(0)[2] + 1
  local lower = line:lower()
  for _, n in ipairs(M.names) do
    local name = n.text:lower()
    local init = 1
    while true do
      local s, e = lower:find(name, init, true)
      if not s then break end
      local before = lower:sub(s - 1, s - 1)
      local after = lower:sub(e + 1, e + 1)
      local ok_before = s == 1 or not before:match("[%w]")
      local ok_after = e == #lower or not after:match("[%w]")
      if ok_before and ok_after and col >= s and col <= e then return n.entity, s, e end
      init = s + 1
    end
  end
  return nil
end

function M.card_lines(e)
  local lines = { string.format("%s  (%s)", e.name, e.type), string.rep("─", 40) }
  local labels = e.labels or {}
  local order = {}
  for k in pairs(e.fields or {}) do order[#order + 1] = k end
  table.sort(order)
  for _, k in ipairs(order) do
    local v = (e.display or {})[k] or e.fields[k]
    if type(v) == "table" then v = table.concat(v, ", ") end
    if v and v ~= "" and k ~= "name" and k ~= "body" then
      lines[#lines + 1] = string.format("%s: %s", labels[k] or k, v)
    end
  end
  for k, v in pairs(e.custom or {}) do lines[#lines + 1] = string.format("%s: %s", k, v) end
  local notes = e.notes or ""
  if e.type == "note" then notes = (e.fields or {}).body or notes end
  if notes ~= "" then
    lines[#lines + 1] = ""
    for _, l in ipairs(vim.split(notes, "\n", { plain = true })) do
      if #lines > 22 then lines[#lines + 1] = "…" break end
      lines[#lines + 1] = l
    end
  end
  return lines
end

-- A read-only floating card for the name under the cursor.
function M.peek()
  local e = M.at_cursor()
  if not e then
    vim.api.nvim_echo({ { "No character, place or thing from this universe under the cursor.", "Normal" } }, false, {})
    return nil
  end
  local lines = M.card_lines(e)
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  local width = 10
  for _, l in ipairs(lines) do width = math.max(width, math.min(70, vim.fn.strdisplaywidth(l))) end
  local win = vim.api.nvim_open_win(buf, false, {
    relative = "cursor", row = 1, col = 0, width = width + 2, height = math.min(#lines, 24),
    style = "minimal", border = "rounded", focusable = false,
  })
  vim.wo[win].wrap = true
  local function close()
    if vim.api.nvim_win_is_valid(win) then vim.api.nvim_win_close(win, true) end
  end
  vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI", "InsertEnter", "BufLeave" }, { once = true, callback = close })
  M.last_peek = { win = win, buf = buf, lines = lines }
  return e
end

-- Completions for what has been typed of a word: any word of a proper name that starts with it (case does not matter), and the whole
-- name when it is the first word. Accepting inserts the name's own capitals. Needs 3 letters.
function M.matches(prefix)
  local items, seen = {}, {}
  if #prefix < 3 then return items end
  local lp = prefix:lower()
  for _, e in ipairs(M.entities) do
    if e.type ~= "note" and e.name and e.name ~= "" and is_proper(e) then
      local words = vim.split(e.name, "%s+", { trimempty = true })
      for i, w in ipairs(words) do
        local clean = w:gsub("^[%p]+", ""):gsub("[%p]+$", "")
        if #clean > #prefix and clean:lower():sub(1, #prefix) == lp and clean:match("^%u") and not seen[clean] then
          seen[clean] = true
          items[#items + 1] = { word = clean, menu = "[" .. e.type .. "]" }
        end
        if i == 1 and #words > 1 and #clean >= #prefix and clean:lower():sub(1, #prefix) == lp and not seen[e.name] then
          seen[e.name] = true
          items[#items + 1] = { word = e.name, menu = "[" .. e.type .. "]" }
        end
      end
    end
  end
  return items
end

-- While typing a word of 3 or more letters, offer matching names from the universe.
function M.complete()
  if vim.fn.pumvisible() == 1 or #M.entities == 0 then return end
  local line = vim.api.nvim_get_current_line()
  local col = vim.api.nvim_win_get_cursor(0)[2]
  local before = line:sub(1, col)
  local prefix = before:match("([%a][%a'’]*)$")
  if not prefix or #prefix < 3 then return end
  local items = M.matches(prefix)
  if #items > 0 then vim.fn.complete(col - #prefix + 1, items) end
end

-- A finished word that is a known proper name in the wrong case ("gise ") is put right, unless the lowercase word is ordinary English.
function M.fix_case(word)
  if #word < 3 or word:match("^%u") then return nil end
  local hit = M.words and M.words[word:lower()]
  if not hit or hit.word == word then return nil end
  if not vim.wo.spell then return nil end                                -- without the spellchecker there is no telling "hope" from "Gise"
  if (vim.fn.spellbadword(word)[1] or "") == "" then return nil end      -- the lowercase word is a real word ("hope", "will"): leave it
  return hit.word
end

function M.setup()
  M.load()
  vim.o.completeopt = "menuone,noselect,noinsert"
  vim.api.nvim_create_autocmd("TextChangedI", { group = vim.api.nvim_create_augroup("sw_world", { clear = true }),
    callback = function() M.complete() end })
end

return M
