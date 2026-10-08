"""Drive the Writer step by step with real input: keys go through nvim_input (so mappings, modes and autocmds see what a keyboard would
send) and mouse events through nvim_input_mouse (what a terminal's mouse codes become). Each step runs only after the one before has been
fully processed, so a click lands on the menu the previous click opened. Coordinates are Lua expressions, evaluated when the step runs
(for example "text_row()" or "item_row('Undo')"), because where things are on screen depends on the layout."""
import json
import subprocess
import textwrap

from storywheel import writer
from test_notepad import ROOT

HELPERS = """
function win_pos(w) local p = vim.fn.win_screenpos(w); return p[1], p[2] end
function text_row(n) local r = win_pos(require('sw.layout').main); return r + (n or 1) - 1 end
function text_col(n) local _, c = win_pos(require('sw.layout').main); return c + (n or 0) end
-- the screen row of a line of the open context menu (1-based line) / of the item with this label
function ctx_win() return require('sw.context').last and require('sw.context').last.win end
function ctx_line(label)
  local m = require('sw.context').last
  for i, l in ipairs(m.lines) do if l:find(label, 1, true) then return i end end
end
function item_row(label) local r = win_pos(ctx_win()); return r + ctx_line(label) - 1 end
function item_col() local _, c = win_pos(ctx_win()); return c + 2 end
"""


def drive(story, steps, check, columns=100, lines=40, setup="", env_extra=None):
    """steps: ("keys", "<F9>") or ("mouse", button, action, row_expr, col_expr). Returns the dict `check` (Lua) filled in R."""
    argv, env = writer.command(story, story.path.parent / "return.txt")
    env.update({"PYTHONPATH": str(ROOT), "TERM": "xterm-256color", "COLUMNS": str(columns), "LINES": str(lines),
                "STORYWHEEL_INTERNAL_CLIPBOARD": "1"})
    env.update(env_extra or {})
    funcs = []
    for st in steps:
        if st[0] == "keys":
            funcs.append("function() vim.api.nvim_input(%s) end" % json.dumps(st[1], ensure_ascii=False))
        elif st[0] == "mouse":
            _, button, action, row, col = st
            funcs.append("function() vim.cmd('redraw!'); vim.api.nvim_input_mouse('%s', '%s', '', 0, (%s) - 1, (%s) - 1) end" % (button, action, row, col))
        else:
            raise ValueError(st)
    script = story.path.parent / "drive.lua"
    script.write_text(
        "vim.o.columns = %d\nvim.o.lines = %d\nrequire('sw').start()\nvim.wait(150)\nR = {}\n%s\n%s\n"
        "function CHECK()\n%s\nio.stdout:write(next(R) == nil and '{}' or vim.json.encode(R))\nvim.cmd('qa!')\nend\n"
        "STEPS = { %s }\nlocal i = 0\n"
        "function NEXT()\n  i = i + 1\n  if os.getenv('NVDRIVE_LOG') then local f = io.open(os.getenv('NVDRIVE_LOG'), 'a'); f:write('step ' .. i .. ' mode=' .. vim.fn.mode() .. '\\n'); f:close() end\n  local f = STEPS[i]\n  if f then local ok, err = pcall(f); if not ok then R.step_error = tostring(err); CHECK() return end; vim.api.nvim_input('<Cmd>lua NEXT()<CR>') else CHECK() end\nend\n"
        "vim.defer_fn(function() R.timeout = true; pcall(CHECK) io.stdout:write(vim.json.encode(R)) vim.cmd('qa!') end, 8000)\n"
        "vim.api.nvim_input('<Cmd>lua NEXT()<CR>')\n"
        % (columns, lines, HELPERS, textwrap.dedent(setup), textwrap.dedent(check), ",\n".join(funcs)))
    res = subprocess.run([argv[0], "--headless", "-c", f"luafile {script}"], env=env, capture_output=True, text=True, timeout=15)
    out = res.stdout[res.stdout.index("{"):] if "{" in res.stdout else ""
    try:
        return json.loads(out)
    except ValueError:
        raise AssertionError(f"no JSON from Neovim.\nstdout: {res.stdout}\nstderr: {res.stderr}")


def keys(k):
    return ("keys", k)


def mouse(button, action, row, col):
    return ("mouse", button, action, str(row), str(col))


def right_click_text(n=1, col=3):
    """A right press and release on the text (what a right-click is)."""
    return [mouse("right", "press", f"text_row({n})", f"text_col({col})"), mouse("right", "release", f"text_row({n})", f"text_col({col})")]


CONTEXT_ORDER = ["Undo", "Redo", "Cut", "Copy", "Paste", "Look Up", "Add to Dictionary", "More…"]       # (no misspelled word under the cursor)


def context_keys(name, misspelled=False):
    """Open the right-click menu (at a fixed place) and choose `name` with Down and Enter."""
    order = CONTEXT_ORDER[:5] + ["Fix Spelling…"] + CONTEXT_ORDER[5:] if misspelled else CONTEXT_ORDER      # (Fix Spelling… shows on a misspelled word)
    return "<Cmd>lua require('sw.context').open({4, 4})<CR>" + "<Down>" * order.index(name) + "<CR>"
