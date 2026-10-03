-- Spelling: the universe's own word list (names of its people, places and things, and the story's proper nouns), words you add with
-- "Add to Dictionary", and the language setting applied to the buffer you are really writing in.
local story = require("sw.story")
local M = {}

M.dir = nil

-- The dictionary's words (and words built from them) are compiled lists in a folder on the runtimepath (see storywheel/spelldict.py).
function M.languages()
  local langs = { "en_us" }
  local root = os.getenv("STORYWHEEL_SPELLLANG_DIR")
  if root and root ~= "" then
    local function has(name) return vim.uv.fs_stat(root .. "/spell/" .. name .. ".utf-8.spl") ~= nil end
    if story.setting("spell_dictionary", true) ~= false and has("swdict") then
      langs[#langs + 1] = "swdict"
      if story.setting("spell_lenient", true) ~= false and has("swlenient") then langs[#langs + 1] = "swlenient" end
    end
  end
  return table.concat(langs, ",")
end

-- Red wavy (SpellBad) always means "not a word". The other three marks can be softened or hidden (Settings > Writer > Spelling marks):
-- SpellCap = lowercase where a capital belongs, SpellRare = rare word, SpellLocal = another region's spelling.
function M.marks()
  local mode = story.setting("spell_marks", "subtle")
  for _, g in ipairs({ "SpellCap", "SpellRare", "SpellLocal" }) do
    if mode == "all" then
      vim.api.nvim_set_hl(0, g, { undercurl = true, sp = ({ SpellCap = "Blue", SpellRare = "Magenta", SpellLocal = "Cyan" })[g] })
    elseif mode == "misspellings only" then
      vim.api.nvim_set_hl(0, g, {})
    else
      vim.api.nvim_set_hl(0, g, { underdotted = true, sp = "Gray" })
    end
  end
end

function M.setup()
  local root = os.getenv("STORYWHEEL_SPELLLANG_DIR")
  if root and root ~= "" then vim.opt.rtp:append(root) end
  M.marks()
  vim.api.nvim_create_autocmd("ColorScheme", { group = vim.api.nvim_create_augroup("sw_spell_marks", { clear = true }), callback = M.marks })
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
  vim.bo[buf].spelllang = M.languages()
  if story.setting("spell_marks", "subtle") == "misspellings only" then vim.bo[buf].spellcapcheck = "" end
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
