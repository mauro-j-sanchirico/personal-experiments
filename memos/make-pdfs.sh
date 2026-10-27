#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$repository_root"

while IFS= read -r markdown; do
    [[ -z "$markdown" ]] && continue

    pandoc "$markdown" \
        -f gfm \
        --resource-path="$(dirname "$markdown")" \
        -o "${markdown%.md}.pdf" \
        --pdf-engine=xelatex \
        --lua-filter=pandoc-title.lua \
        --include-in-header=pandoc-header.tex \
        --toc \
        --toc-depth=2 \
        -V geometry:margin=1in
done < <(sed -n '/^pdfs:/,$ { /^[[:space:]]*-[[:space:]]*/ { s///; p; } }' pdfs.yaml)
