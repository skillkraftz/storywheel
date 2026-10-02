-- Small helpers shared by the Writer's modules.
local M = {}

function M.read(path)
  local f = io.open(path, "r")
  if not f then return nil end
  local text = f:read("*a")
  f:close()
  return text
end

function M.write(path, text)
  local tmp = path .. ".tmp"
  local f = assert(io.open(tmp, "w"))
  f:write(text)
  f:close()
  assert(os.rename(tmp, path))
end

function M.exists(path)
  return vim.uv.fs_stat(path) ~= nil
end

function M.mkdir(path)
  vim.fn.mkdir(path, "p")
end

function M.json_read(path, default)
  local text = M.read(path)
  if not text or text == "" then return default end
  local ok, data = pcall(vim.json.decode, text)
  if not ok then return default end
  return data
end

function M.json_write(path, data)
  M.mkdir(vim.fn.fnamemodify(path, ":h"))
  M.write(path, vim.json.encode(data))
end

-- Words in prose: runs of non-space characters that hold a letter or digit, so `* * *` is not three words.
-- (storywheel/vault.py counts the same way.)
local keyword = vim.regex([[\k]])

-- A scene marker is `* * *` or `* * * Title`. Returns nil for any other line, else the title ("" for a plain `* * *`).
-- A line holding only `***`, `* * *` or `#` is a scene break; `* * * Title` (or `*** Title`) is a break that names its scene.
-- `***bold italic***` inside a paragraph is not a break. (storywheel/vault.py: marker_label)
function M.marker_label(line)
  local s = line:gsub("%s+$", "")
  if s == "* * *" or s == "***" or s == "#" then return "" end
  local label = s:match("^%* %* %*%s+(.-)$") or s:match("^%*%*%*%s+([^%*%s].-)$")
  return label
end

-- <A-i> -> Alt+I, <C-q> -> Ctrl+Q, <F12> -> F12 (for menus and help). (storywheel/keys.py: label)
function M.key_label(key)
  local mods, k = key:match("^<(.-)%-?([^%-]+)>$")
  if not k then return key end
  local names = { A = "Alt", C = "Ctrl", S = "Shift" }
  local out = {}
  for m in (mods or ""):gmatch("[ACS]") do out[#out + 1] = names[m] end
  out[#out + 1] = #k == 1 and k:upper() or k
  return table.concat(out, "+")
end

-- Is this line a scene break that is only a break (no title)?
function M.is_plain_break(line)
  return M.marker_label(line) == ""
end

-- Words in prose: runs of non-space characters holding a letter or digit. Marker lines are not prose.
-- (storywheel/vault.py counts the same way.)
function M.count_words(text)
  local n = 0
  for line in (text .. "\n"):gmatch("(.-)\n") do
    if M.marker_label(line) == nil then
      for w in line:gmatch("%S+") do
        if w:find("%w") or (w:find("[\128-\255]") and keyword:match_str(w)) then n = n + 1 end
      end
    end
  end
  return n
end

-- Scenes in a list of lines, found by their markers. A marker at the very start names the first scene (it is not a
-- break); text before the first marker is a scene of its own. Returns { {start=, finish=, label=, marked=, first_line=, words=,
-- body=}, ... } with 1-based lines; `body` is the first line of real text.
function M.parse_scenes(lines)
  local scenes = {}
  for i, line in ipairs(lines) do
    local label = M.marker_label(line)
    if label ~= nil then
      scenes[#scenes + 1] = { start = (#scenes == 0) and 1 or i, label = label, marked = true }
    elseif line:match("%S") and #scenes == 0 then
      scenes[#scenes + 1] = { start = 1, label = "", marked = false }
    end
  end
  for k, sc in ipairs(scenes) do
    sc.finish = scenes[k + 1] and (scenes[k + 1].start - 1) or #lines
    sc.first_line, sc.body = "", sc.start
    local block = {}
    for i = sc.start, sc.finish do
      local line = lines[i]
      block[#block + 1] = line
      if sc.first_line == "" and line:match("%S") and M.marker_label(line) == nil then
        sc.first_line, sc.body = line, i
      end
    end
    sc.words = M.count_words(table.concat(block, "\n"))
  end
  return scenes
end

-- Load a file into a (hidden) buffer without the "path, 12L, 340B" message, which would scroll the status line.
function M.load_buffer(path)
  local b = vim.fn.bufadd(path)
  vim.cmd("silent! call bufload(" .. b .. ")")
  return b
end

function M.notify(msg, level)
  vim.schedule(function() vim.notify(msg, level or vim.log.levels.INFO) end)
end

-- The storywheel command line, as a list: {python, "-m", "storywheel", ...}
function M.cli(args)
  local py = os.getenv("STORYWHEEL_PY") or "python3"
  local cmd = { py, "-m", "storywheel" }
  for _, a in ipairs(args) do cmd[#cmd + 1] = a end
  return cmd
end

-- Run the CLI and decode its JSON output. Returns data or nil, error message.
function M.cli_json(args)
  local out = vim.fn.system(M.cli(args))
  if vim.v.shell_error ~= 0 then return nil, out end
  local ok, data = pcall(vim.json.decode, out)
  if not ok then return nil, "bad JSON from storywheel" end
  return data
end

function M.today()
  return os.date("%Y-%m-%d")
end

return M
