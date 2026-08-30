#!/usr/bin/env bash
# Run the tiles' tests. Each tile is a standalone project with its own package and its own
# `tests/` dir; a single root-level pytest run cannot import them together (same module names),
# so we run them one at a time. Usage: ./run_tests.sh [tile-name]
set -u
cd "$(dirname "$0")" || exit 1
PY="${PYTHON:-python3}"
only="${1:-}"
fail=0

# One legible failure instead of the same cryptic line repeated for every tile.
if ! "$PY" -c "import pytest" >/dev/null 2>&1; then
    echo "run_tests.sh: '$PY' has no pytest." >&2
    echo "  pip install numpy scipy scikit-image h5py matplotlib tifffile pandas pytest" >&2
    echo "  pip install -e ./gallery_style" >&2
    echo "  (or point PYTHON= at an environment that already has them)" >&2
    exit 1
fi

run() {  # run <label> <dir>
    local label="$1" dir="$2"
    local full summary
    local target="tests/"; [[ -d "$dir/tests" ]] || target="."
    full=$(cd "$dir" && "$PY" -m pytest "$target" -q 2>&1)
    summary=$(tail -1 <<<"$full")
    printf '%-30s %s\n' "$label" "$summary"
    if [[ "$summary" != *"passed"* || "$summary" == *"failed"* || "$summary" == *"error"* ]]; then
        fail=1
        sed 's/^/    | /' <<<"$full" | tail -30   # show WHY, not just the count
    fi
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
