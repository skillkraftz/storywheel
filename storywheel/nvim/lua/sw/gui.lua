-- Neovide (an optional window with real fonts): the same config, plus a font and extra line spacing from the settings.
-- storywheel starts Neovide with STORYWHEEL_GUI=neovide; vim.g.neovide says the same once the window is up.
local story = require("sw.story")
local M = {}

M.active = false

function M.detected()
  return os.getenv("STORYWHEEL_GUI") == "neovide" or vim.g.neovide ~= nil
end

function M.setup()
  M.active = M.detected()
  if not M.active then return end
  local font = story.setting("writer_font", "")
  local size = tonumber(story.setting("writer_font_size", 15)) or 15
  if font and font ~= "" then
    vim.o.guifont = font:gsub(" ", "\\ ") .. ":h" .. size
  else
    vim.o.guifont = "monospace:h" .. size
  end
  -- extra pixels between lines: about the font size looks double spaced
  vim.o.linespace = tonumber(story.setting("line_spacing", 12)) or 12
  vim.g.neovide_scroll_animation_length = 0.12
  vim.g.neovide_cursor_animation_length = 0.04
  vim.g.neovide_cursor_vfx_mode = ""
  vim.g.neovide_hide_mouse_when_typing = true
end

-- Extra blank space between paragraphs, for the terminal (Neovide has real line spacing instead).
function M.paragraph_spacing()
  if M.active then return 0 end
  local n = tonumber(story.setting("paragraph_spacing", 0)) or 0
  return math.max(0, math.min(n, 3))
end

return M
