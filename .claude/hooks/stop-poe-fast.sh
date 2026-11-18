#!/usr/bin/env bash
# Hook Stop de Claude Code (ADR 0012).
# Si el árbol de trabajo tiene cambios, corre `uv run poe fast`.
# Si falla, sale con código 2: Claude ve el error y no puede cerrar el turno.
set -uo pipefail

input=$(cat)

# Si Claude ya está continuando por este mismo hook, no lo bloquea de nuevo (evita el bucle).
if grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true' <<<"$input"; then
    exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Sin cambios no hay nada que revisar.
if [ -z "$(git status --porcelain)" ]; then
    exit 0
fi

if ! output=$(uv run poe fast 2>&1); then
    {
        echo "poe fast falló. Arréglalo antes de terminar el turno; no lo esquives (ADR 0012)."
        echo "$output" | tail -n 40
    } >&2
    exit 2
fi
