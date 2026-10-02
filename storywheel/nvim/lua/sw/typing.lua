-- What happens as you type: curly quotes become straight (the manuscript keeps straight ones; the export makes them curly), and common
-- slips are corrected when you finish the word (i -> I, im -> I'm, dont -> don't...).
local story = require("sw.story")
local M = {}

M.CURLY = {
  { "\226\128\152", "'" }, { "\226\128\153", "'" }, { "\226\128\154", "'" }, { "\226\128\155", "'" },
  { "\226\128\156", '"' }, { "\226\128\157", '"' }, { "\226\128\158", '"' }, { "\226\128\159", '"' },
}

function M.straighten(text)
  for _, pair in ipairs(M.CURLY) do text = text:gsub(pair[1], pair[2]) end
  return text
end

M.CORRECTIONS = {
  ["i"] = "I", ["im"] = "I'm", ["i'm"] = "I'm", ["ive"] = "I've", ["i've"] = "I've", ["i'll"] = "I'll", ["i'd"] = "I'd",
  ["dont"] = "don't", ["doesnt"] = "doesn't", ["didnt"] = "didn't", ["isnt"] = "isn't", ["wasnt"] = "wasn't", ["arent"] = "aren't",
  ["werent"] = "weren't", ["cant"] = "can't", ["couldnt"] = "couldn't", ["wouldnt"] = "wouldn't", ["shouldnt"] = "shouldn't",
  ["hasnt"] = "hasn't", ["havent"] = "haven't", ["hadnt"] = "hadn't", ["wont"] = "won't", ["thats"] = "that's", ["theyre"] = "they're",
  ["youre"] = "you're", ["theyve"] = "they've", ["weve"] = "we've", ["youve"] = "you've", ["theyll"] = "they'll", ["youll"] = "you'll",
  ["teh"] = "the", ["adn"] = "and", ["taht"] = "that", ["wiht"] = "with", ["recieve"] = "receive",
  ["definately"] = "definitely", ["seperate"] = "separate", ["occured"] = "occurred", ["untill"] = "until",
}

-- The correction for a word as typed, keeping a capital first letter ("Dont" -> "Don't"); nil if there is none.
function M.correct(word)
  local fix = M.CORRECTIONS[word:lower()]
  if not fix then return nil end
  if word == "i" or fix:sub(1, 1) == "I" then return fix end            -- "I" and "I'm" are always capital
  if word:sub(1, 1):match("%u") then fix = fix:sub(1, 1):upper() .. fix:sub(2) end
  if fix == word then return nil end
  return fix
end

-- After a space or punctuation has been typed, fix the word before it.
local function fix_before_cursor(buf, want_row, want_col)
  if not vim.api.nvim_buf_is_valid(buf) or vim.api.nvim_get_current_buf() ~= buf or vim.fn.mode() ~= "i" then return end
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  if row ~= want_row or col ~= want_col then return end            -- more was typed already (keys queued up): leave the text alone
  local line = vim.api.nvim_get_current_line()
  local delim = col                                          -- 1-based index of the delimiter just typed
  local e = delim - 1
  local s = e
  while s > 0 and line:sub(s, s):match("[%a']") do s = s - 1 end
  s = s + 1
  if e < s then return end
  local word = line:sub(s, e)
  if word:sub(1, 1) == "'" then word = word:sub(2) s = s + 1 end
  if word == "" then return end
  local fix = M.correct(word)
  if not fix then return end
  vim.api.nvim_buf_set_text(buf, row - 1, s - 1, row - 1, e, { fix })
  vim.api.nvim_win_set_cursor(0, { row, col + #fix - #word })
end

function M.setup()
  local group = vim.api.nvim_create_augroup("sw_typing", { clear = true })
  vim.api.nvim_create_autocmd("InsertCharPre", { group = group, callback = function(ev)
    if vim.bo[ev.buf].filetype ~= "storywheel" then return end
    local buf = ev.buf
    local c = vim.v.char
    for _, pair in ipairs(M.CURLY) do
      if c == pair[1] then vim.v.char = pair[2] c = pair[2] break end
    end
    if story.setting("autocorrect", true) ~= false and c:match("^[%s%.,;:!%?%)%]\"]$") then
      local at = vim.api.nvim_win_get_cursor(0)               -- where the delimiter is going in; the fix only applies if the cursor is right after it
      vim.schedule(function() fix_before_cursor(buf, at[1], at[2] + 1) end)
    end
  end })
end

return M
