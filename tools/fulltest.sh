#!/bin/sh
# The end-of-batch full run (CLAUDE.md, testing policy): everything in parallel, then the serial tests alone, with the time of each pass.
# (The cache is kept, so `pytest --lf` reruns what failed.)
# Usage: tools/fulltest.sh [extra pytest options]
# It runs from the repository root, uses ./.venv/bin/python when that exists (else $PYTHON, else python3), and points STORYWHEEL_HOME and
# STORYWHEEL_LIBRARY at fresh temporary folders unless they are already set, so it never touches ~/.storywheel or ~/Writing.
cd "$(dirname "$0")/.." || exit 1
if [ -n "$PYTHON" ]; then PY="$PYTHON"
elif [ -x ./.venv/bin/python ]; then PY=./.venv/bin/python
else PY=python3; fi
tmp=
if [ -z "$STORYWHEEL_HOME" ] || [ -z "$STORYWHEEL_LIBRARY" ]; then
    tmp=$(mktemp -d)
    : "${STORYWHEEL_HOME:=$tmp/home}"
    : "${STORYWHEEL_LIBRARY:=$tmp/library}"
fi
: "${STORYWHEEL_MANUSCRIPTS:=${tmp:-$(mktemp -d)}/manuscripts}"
export STORYWHEEL_HOME STORYWHEEL_LIBRARY STORYWHEEL_MANUSCRIPTS
mkdir -p "$STORYWHEEL_HOME" "$STORYWHEEL_LIBRARY" "$STORYWHEEL_MANUSCRIPTS"
echo "python: $PY; STORYWHEEL_HOME=$STORYWHEEL_HOME; STORYWHEEL_LIBRARY=$STORYWHEEL_LIBRARY"
start=$(date +%s)
"$PY" -m pytest -q -n auto -m "not serial" "$@"
a=$?
mid=$(date +%s)
"$PY" -m pytest -q -m serial "$@"
b=$?
end=$(date +%s)
echo "parallel pass: $((mid - start)) s (exit $a); serial pass: $((end - mid)) s (exit $b); total: $((end - start)) s"
[ -n "$tmp" ] && rm -rf "$tmp"
[ "$a" -eq 0 ] && [ "$b" -eq 0 ]
