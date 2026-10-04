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

-- The misspelled word under the cursor and its suggestions: nil when the word is fine (or spelling is off).
function M.bad_word()
  if not vim.wo.spell then return nil end
  local bad = vim.fn.spellbadword()
  if (bad[1] or "") == "" then return nil end
  return bad[1]
end

-- "Fix spelling…": a small list of suggestions at the cursor; Enter or a click replaces the word, Esc closes.
function M.suggest()
  local word = M.bad_word()
  if not word then
    vim.api.nvim_echo({ { "Put the cursor on a word marked as misspelled first.", "Normal" } }, true, {})
    return
  end
  local sugg = vim.fn.spellsuggest(word, 8)
  local lines = {}
  for i, w in ipairs(sugg) do lines[#lines + 1] = string.format(" %d  %s", i, w) end
  if #lines == 0 then lines[1] = " (no suggestions)" end
  local width = 20
  for _, l in ipairs(lines) do width = math.max(width, vim.fn.strdisplaywidth(l) + 2) end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  local origin = vim.api.nvim_get_current_win()
  local cursor = vim.api.nvim_win_get_cursor(origin)
  local win = vim.api.nvim_open_win(buf, true, { relative = "cursor", row = 1, col = 0, width = width, height = #lines, style = "minimal",
    border = "rounded", title = " " .. word .. " ", title_pos = "center" })
  vim.wo[win].cursorline = true
  vim.cmd("stopinsert")
  local function close()
    if vim.api.nvim_win_is_valid(win) then vim.api.nvim_win_close(win, true) end
    if vim.api.nvim_win_is_valid(origin) then vim.api.nvim_set_current_win(origin) end
    require("sw.notepad").insert(true)
  end
  local function pick(i)
    local w = sugg[i]
    close()
    if not w then return end
    local row = cursor[1] - 1
    local line = vim.api.nvim_buf_get_lines(0, row, row + 1, false)[1] or ""
    local a = line:find(word, math.max(1, cursor[2] - #word + 1), true) or line:find(word, 1, true)
    if a then vim.api.nvim_buf_set_text(0, row, a - 1, row, a - 1 + #word, { w }) end
  end
  local function map(lhs, fn) vim.keymap.set("n", lhs, fn, { buffer = buf, nowait = true, silent = true }) end
  map("<CR>", function() pick(vim.api.nvim_win_get_cursor(win)[1]) end)
  map("<Esc>", close)
  map("q", close)
  for i = 1, math.min(9, #sugg) do map(tostring(i), function() pick(i) end) end
  map("<LeftMouse>", function()
    local pos = vim.fn.getmousepos()
    if pos.winid ~= win then close() return end
    pick(pos.line)
  end)
  return win
end

return M
