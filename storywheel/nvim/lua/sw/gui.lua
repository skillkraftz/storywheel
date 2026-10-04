-- The Writer's window. The font, size, line height, padding and opacity belong to the kitty window storywheel opens for the Writer
-- (see writer.py: kitty_command); inside Neovim there is nothing to set. What is left here is the extra space between paragraphs.
local story = require("sw.story")
local M = {}

M.active = os.getenv("STORYWHEEL_GUI") == "kitty"      -- true in the Writer's own kitty window

function M.detected()
  return os.getenv("STORYWHEEL_GUI") == "kitty"
end

function M.setup()
  M.active = os.getenv("STORYWHEEL_GUI") == "kitty"
end

-- Extra blank space between paragraphs, shown (not typed). A kitty window's line height usually makes this unnecessary (the setting is 0).
function M.paragraph_spacing()
  local n = tonumber(story.setting("paragraph_spacing", 0)) or 0
  return math.max(0, math.min(n, 3))
end

return M
