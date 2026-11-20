#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$repository_root"

media_directory="$(mktemp -d)"
trap 'rm -rf -- "$media_directory"' EXIT

while IFS= read -r source; do
    [[ -z "$source" ]] && continue

    case "$source" in
        *.md) format=gfm ;;
        *.ipynb) format=ipynb ;;
        *) echo "Unsupported input format: $source" >&2; exit 1 ;;
    esac

    echo "Generating ${source%.*}.pdf from $source"
    pandoc "$source" \
        -f "$format" \
        --resource-path="$(dirname "$source")" \
        --extract-media="$media_directory" \
        -o "${source%.*}.pdf" \
        --pdf-engine=xelatex \
        --lua-filter=pandoc-title.lua \
        --lua-filter=pandoc-abstract.lua \
        --include-in-header=pandoc-header.tex \
        --number-sections \
        --toc \
        --toc-depth=2 \
        -V geometry:margin=1in
done < <(sed -n '/^pdfs:/,$ { /^[[:space:]]*-[[:space:]]*/ { s///; p; } }' pdfs.yaml)

echo "PDF generation complete."
