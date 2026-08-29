#!/usr/bin/env bash
# Run the tiles' tests. Each tile is a standalone project with its own package and its own
# `tests/` dir; a single root-level pytest run cannot import them together (same module names),
# so we run them one at a time. Usage: ./run_tests.sh [tile-name]
set -u
cd "$(dirname "$0")" || exit 1
PY="${PYTHON:-python3}"
only="${1:-}"
fail=0

run() {  # run <label> <dir>
    local label="$1" dir="$2"
    local out
    local target="tests/"; [[ -d "$dir/tests" ]] || target="."
    out=$(cd "$dir" && "$PY" -m pytest "$target" -q 2>&1 | tail -1)
    printf '%-30s %s\n' "$label" "$out"
    [[ "$out" == *"passed"* && "$out" != *"failed"* ]] || fail=1
}

for d in methods/*/; do
    tile=$(basename "$d")
    [[ -n "$only" && "$only" != "$tile" ]] && continue
    run "$tile" "$d"
done
[[ -z "$only" ]] && run "_sync (de-identifier)" "_sync"

echo
if [[ $fail -eq 0 ]]; then echo "all green"; else echo "FAILURES — see above"; fi
exit $fail
