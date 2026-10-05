#!/bin/sh
# The end-of-batch full run (CLAUDE.md, testing policy): everything in parallel, then the serial tests alone, with the time of each pass.
# Usage: tools/fulltest.sh [extra pytest options]       (run it from the repository root, with STORYWHEEL_* pointing at a temporary folder)
PY="${PYTHON:-python3}"
start=$(date +%s)
"$PY" -m pytest -q -p no:cacheprovider -n auto -m "not serial" "$@"
a=$?
mid=$(date +%s)
"$PY" -m pytest -q -p no:cacheprovider -m serial "$@"
b=$?
end=$(date +%s)
echo "parallel pass: $((mid - start)) s (exit $a); serial pass: $((end - mid)) s (exit $b); total: $((end - start)) s"
[ "$a" -eq 0 ] && [ "$b" -eq 0 ]
