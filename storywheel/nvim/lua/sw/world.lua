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

function M.index()
  M.names = {}
  for _, e in ipairs(M.entities) do
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

-- While typing a capitalised word, offer matching names from the universe (Tab picks the next one).
function M.complete()
  if vim.fn.pumvisible() == 1 or #M.names == 0 then return end
  local line = vim.api.nvim_get_current_line()
  local col = vim.api.nvim_win_get_cursor(0)[2]
  local before = line:sub(1, col)
  local prefix = before:match("(%u[%w'’]*)$")
  if not prefix or #prefix < 2 then return end
  local items, seen = {}, {}
  local lp = prefix:lower()
  for _, n in ipairs(M.names) do
    if #n.text > #prefix and n.text:lower():sub(1, #prefix) == lp and not seen[n.text] then
      seen[n.text] = true
      items[#items + 1] = { word = n.text, menu = "[" .. n.entity.type .. "]" }
    end
  end
  if #items > 0 then vim.fn.complete(col - #prefix + 1, items) end
end

function M.setup()
  M.load()
  vim.o.completeopt = "menuone,noselect,noinsert"
  vim.api.nvim_create_autocmd("TextChangedI", { group = vim.api.nvim_create_augroup("sw_world", { clear = true }),
    callback = function() M.complete() end })
end

return M
