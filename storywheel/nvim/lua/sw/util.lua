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

function M.count_words(text)
  local n = 0
  for w in text:gmatch("%S+") do
    if w:find("%w") or (w:find("[\128-\255]") and keyword:match_str(w)) then n = n + 1 end
  end
  return n
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
