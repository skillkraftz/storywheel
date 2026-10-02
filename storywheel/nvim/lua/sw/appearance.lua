-- How the Writer looks: a transparent background (the terminal's own background, so a translucent terminal shows through), your text
-- color and accent color. Settings > Appearance; the same choices style the Textual modes. kitty (and other terminals) apply their
-- background opacity only to cells that use the DEFAULT background, so every group below gets bg NONE rather than a color.
local story = require("sw.story")
local M = {}

-- every group that may paint a background
local CLEAR = {
  "Normal", "NormalNC", "NormalFloat", "FloatBorder", "FloatTitle", "FloatFooter", "SignColumn", "EndOfBuffer", "WinSeparator", "VertSplit",
  "StatusLine", "StatusLineNC", "MsgArea", "MsgSeparator", "Pmenu", "PmenuSbar", "PmenuKind", "PmenuExtra", "WinBar", "WinBarNC", "TabLine",
  "TabLineFill", "TabLineSel", "LineNr", "CursorLineNr", "FoldColumn", "Folded", "ColorColumn", "NonText", "Whitespace", "SwPad", "CursorLine",
  "QuickFixLine", "Question", "MoreMsg",
}

local function get(name)
  local ok, hl = pcall(vim.api.nvim_get_hl, 0, { name = name, link = false })
  return ok and hl or {}
end

function M.wanted()
  return {
    transparent = story.setting("transparent_background", true) ~= false,
    text = story.setting("text_color", ""),
    accent = story.setting("accent_color", ""),
  }
end

local function hex(c)
  if type(c) ~= "string" or c == "" then return nil end
  return c
end

function M.apply()
  local want = M.wanted()
  local text, accent = hex(want.text), hex(want.accent)
  local function set(name, patch)
    local cur = get(name)
    cur.link = nil
    for k, v in pairs(patch) do cur[k] = v end
    vim.api.nvim_set_hl(0, name, cur)
  end
  if want.transparent then
    for _, g in ipairs(CLEAR) do set(g, { bg = "NONE", ctermbg = "NONE" }) end
    set("PmenuSel", { reverse = true, bg = "NONE", ctermbg = "NONE" })       -- (the chosen menu entry is shown by reversing, not by a color)
  end
  if text then
    set("Normal", { fg = text })
    set("NormalFloat", { fg = text })
    set("Pmenu", { fg = text })
  end
  if accent then
    set("SwBreak", { fg = accent })
    set("FloatBorder", { fg = accent })
    set("FloatTitle", { fg = accent, bold = true })
    set("FloatFooter", { fg = accent })
    set("Search", { bg = accent, fg = "#000000" })
    set("IncSearch", { bg = accent, fg = "#000000" })
    set("Title", { fg = accent, bold = true })
    set("Visual", { bg = accent, fg = "#000000" })
    if not want.transparent then set("PmenuSel", { bg = accent, fg = "#000000" }) end
  end
  M.applied = want
  return want
end

function M.setup()
  M.apply()
  vim.api.nvim_create_autocmd("ColorScheme", { group = vim.api.nvim_create_augroup("sw_appearance", { clear = true }), callback = M.apply })
end

return M
