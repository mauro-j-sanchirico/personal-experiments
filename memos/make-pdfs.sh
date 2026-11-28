#!/usr/bin/env bash
# Build all PDFs: ./make-pdfs.sh
# Build selected folders: ./make-pdfs.sh example_memo_markdown example_memo_notebook

set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$repository_root"

mapfile -t sources < <(sed -n '/^pdfs:/,$ { /^[[:space:]]*-[[:space:]]*/ { s///; p; } }' pdfs.yaml)

for folder in "$@"; do
    found=false
    for source in "${sources[@]}"; do
        if [[ "$(dirname "$source")" == "$folder" ]]; then
            found=true
            break
        fi
    done
    if [[ "$found" == false ]]; then
        echo "No PDF source found for folder: $folder" >&2
        exit 1
    fi
done

media_directory="$(mktemp -d)"
trap 'rm -rf -- "$media_directory"' EXIT

for source in "${sources[@]}"; do
    [[ -z "$source" ]] && continue

    if (( $# > 0 )); then
        selected=false
        for folder in "$@"; do
            if [[ "$(dirname "$source")" == "$folder" ]]; then
                selected=true
                break
            fi
        done
        [[ "$selected" == true ]] || continue
    fi

    case "$source" in
        *.md) format=markdown ;;
        *.ipynb) format=ipynb+citations+fenced_divs ;;
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
        --lua-filter=pandoc-copyright.lua \
        --lua-filter=pandoc-header.lua \
        --metadata=autoEqnLabels:true \
        --filter=pandoc-crossref \
        --csl=ieee.csl \
        --citeproc \
        --number-sections \
        --toc \
        --toc-depth=2 \
        -V geometry:margin=1in
done

echo "PDF generation complete."
