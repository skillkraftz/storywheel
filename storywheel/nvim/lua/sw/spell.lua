-- Spelling: the universe's own word list (names of its people, places and things, and the story's proper nouns), words you add with
-- "Add to Dictionary", and the language setting applied to the buffer you are really writing in.
local story = require("sw.story")
local M = {}

M.dir = nil

function M.setup()
  M.dir = os.getenv("STORYWHEEL_SPELL_DIR")
  if not M.dir or M.dir == "" then return end
  vim.fn.mkdir(M.dir, "p")
  M.mine = M.dir .. "/en.utf-8.add"          -- words you add (zg / "Add to Dictionary")
  M.names = M.dir .. "/names.utf-8.add"      -- written by storywheel when the Writer starts
  for _, f in ipairs({ M.mine, M.names }) do
    if vim.uv.fs_stat(f) then pcall(vim.cmd, "silent! mkspell! " .. vim.fn.fnameescape(f)) end       -- Vim reads the compiled form
  end
end

-- Language and word lists for one buffer (spelllang and spellfile belong to the buffer, spell itself to the window).
function M.apply(buf)
  if not (buf and vim.api.nvim_buf_is_valid(buf)) then return end
  vim.bo[buf].spelllang = "en_us"
  if M.mine then vim.bo[buf].spellfile = M.mine .. "," .. M.names end
end

function M.apply_all()
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    local name = vim.api.nvim_buf_get_name(b)
    if vim.api.nvim_buf_is_loaded(b) and name ~= "" and story.manuscript and name:find(story.manuscript, 1, true) then M.apply(b) end
  end
end

-- "Add to Dictionary": the word goes into the universe's own list (every story in it stops flagging the word).
function M.add_word(word)
  if not word or word == "" then return false end
  local main = require("sw.layout").main
  local buf = vim.api.nvim_win_get_buf(main)
  M.apply(buf)
  vim.api.nvim_buf_call(buf, function() vim.cmd("silent! spellgood " .. word) end)
  vim.api.nvim_echo({ { "Added “" .. word .. "” to this universe's dictionary.", "Normal" } }, true, {})
  return true
end

return M
