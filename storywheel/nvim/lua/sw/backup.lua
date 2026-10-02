-- Never lose writing: autosave, and rolling backups of the manuscript files in <story>/.backups/<date>/.
-- A backup is a copy named HHMM-<scene>.md, made when the scene changed since its last backup and at least
-- INTERVAL seconds after the previous one. The newest DAYS days of folders are kept.
local util = require("sw.util")
local story = require("sw.story")
local M = {}

M.INTERVAL = 15 * 60
M.DAYS = 30
M.last = {}                 -- scene name -> { time=, text= }

function M.dir()
  return story.dir .. "/.backups"
end

function M.snapshot(force)
  if not story.dir then return 0 end
  local made = 0
  local now = os.time()
  for _, s in ipairs(story.files()) do
    local text = util.read(s.path) or ""
    local last = M.last[s.name]
    local latest_text = last and last.text
    if latest_text == nil then
      -- first time this session: compare with the newest backup on disk
      local folder = M.dir() .. "/" .. util.today()
      if util.exists(folder) then
        local newest
        for _, f in ipairs(vim.fn.readdir(folder)) do
          if f:match("^%d%d%d%d%-" .. vim.pesc(s.name) .. "$") then newest = f end
        end
        if newest then latest_text = util.read(folder .. "/" .. newest) end
      end
    end
    local due = force or not last or (now - last.time) >= M.INTERVAL
    if text:match("%S") and text ~= latest_text and due then
      local folder = M.dir() .. "/" .. util.today()
      util.mkdir(folder)
      util.write(folder .. "/" .. os.date("%H%M") .. "-" .. s.name, text)
      M.last[s.name] = { time = now, text = text }
      made = made + 1
    elseif not last then
      M.last[s.name] = { time = now, text = latest_text or text }
    end
  end
  M.prune()
  return made
end

function M.prune()
  if not util.exists(M.dir()) then return end
  local days = vim.fn.readdir(M.dir())
  table.sort(days)
  while #days > M.DAYS do
    vim.fn.delete(M.dir() .. "/" .. table.remove(days, 1), "rf")
  end
end

-- Write every modified manuscript buffer. Returns how many were written.
function M.save_all()
  local n = 0
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(b) and vim.bo[b].modified and vim.bo[b].buftype == "" and vim.api.nvim_buf_get_name(b) ~= "" then
      local ok = pcall(vim.api.nvim_buf_call, b, function() vim.cmd("silent! write") end)
      if ok then n = n + 1 end
    end
  end
  return n
end

function M.setup()
  if not story.dir then return end
  vim.o.updatetime = 2000
  vim.o.autowriteall = true
  M.snapshot(false)
  local group = vim.api.nvim_create_augroup("sw_autosave", { clear = true })
  vim.api.nvim_create_autocmd({ "InsertLeave", "FocusLost", "BufLeave", "CursorHold", "CursorHoldI", "VimLeavePre" }, {
    group = group,
    callback = function()
      if M.save_all() > 0 then
        M.snapshot(false)
        require("sw.stats").save()
      end
    end,
  })
end

return M
