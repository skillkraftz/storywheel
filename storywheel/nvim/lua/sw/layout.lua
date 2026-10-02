-- The writing room: one centered column. Two blank "pad" windows hold the margins, and the left one doubles as
-- the scene sidebar when that is switched on.
local story = require("sw.story")
local M = {}

M.main, M.left, M.right = nil, nil, nil
M.sidebar_width = 42
M.sidebar_open = false

local function pad_window(win)
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_win_set_buf(win, buf)
  vim.bo[buf].buftype = "nofile"
  vim.bo[buf].bufhidden = "hide"
  vim.bo[buf].swapfile = false
  vim.bo[buf].modifiable = false
  vim.bo[buf].buflisted = false
  local o = vim.wo[win]
  o.number, o.relativenumber, o.signcolumn, o.cursorline, o.list = false, false, "no", false, false
  o.winfixwidth, o.wrap, o.statuscolumn = true, false, ""
  o.winhighlight = "Normal:SwPad,EndOfBuffer:SwPad,NormalNC:SwPad"
  return buf
end

function M.column()
  local cols = vim.o.columns
  return math.max(20, math.min(story.setting("column_width", 72), cols - 4))
end

function M.setup(main)
  M.main = main
  vim.opt.fillchars = { vert = " ", horiz = " ", eob = " ", fold = " " }
  vim.api.nvim_set_hl(0, "SwPad", { link = "Normal", default = true })
  vim.api.nvim_set_hl(0, "WinSeparator", { link = "Normal" })
  vim.api.nvim_set_current_win(main)
  vim.cmd("topleft vnew")
  M.left = vim.api.nvim_get_current_win()
  M.left_buf = pad_window(M.left)
  vim.api.nvim_set_current_win(main)
  vim.cmd("botright vnew")
  M.right = vim.api.nvim_get_current_win()
  M.right_buf = pad_window(M.right)
  vim.api.nvim_set_current_win(main)
  M.apply()
  local group = vim.api.nvim_create_augroup("sw_layout", { clear = true })
  vim.api.nvim_create_autocmd({ "VimResized" }, { group = group, callback = function() M.apply() end })
  vim.api.nvim_create_autocmd("WinEnter", {
    group = group,
    callback = function()
      local w = vim.api.nvim_get_current_win()
      if w == M.right or (w == M.left and not M.sidebar_open) then
        vim.schedule(function() if vim.api.nvim_win_is_valid(M.main) then vim.api.nvim_set_current_win(M.main) end end)
      end
    end,
  })
  vim.api.nvim_create_autocmd("WinClosed", {
    group = group,
    callback = function(ev)
      if tonumber(ev.match) == M.main then vim.schedule(function() vim.cmd("qa!") end) end
    end,
  })
end

function M.apply()
  if not (M.main and vim.api.nvim_win_is_valid(M.main)) then return end
  local cols = vim.o.columns
  local width = M.column()
  local left = M.sidebar_open and M.sidebar_width or math.max(0, math.floor((cols - width) / 2) - 1)
  if M.sidebar_open then width = math.min(width, cols - left - 4) end
  local right = math.max(1, cols - left - width - 2)
  -- the two pads have fixed widths; the writing window gets whatever is left, which is `width`
  if M.left and vim.api.nvim_win_is_valid(M.left) then vim.api.nvim_win_set_width(M.left, math.max(1, left)) end
  if M.right and vim.api.nvim_win_is_valid(M.right) then vim.api.nvim_win_set_width(M.right, right) end
  require("sw.prose").decorate(vim.api.nvim_win_get_buf(M.main))
end

return M
