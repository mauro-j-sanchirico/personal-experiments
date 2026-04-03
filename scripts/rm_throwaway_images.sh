#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
image_dir="${script_dir}/../throwaway/jupyter/images"
force_delete=false

while getopts ":f" option; do
    case "${option}" in
        f)
            force_delete=true
            ;;
        *)
            echo "Usage: $0 [-f]"
            exit 1
            ;;
    esac
done

echo "Removing all images in ${image_dir}:"

find "${image_dir}" -maxdepth 1 -type f \( \
    -iname '*.png' -o \
    -iname '*.jpg' -o \
    -iname '*.jpeg' -o \
    -iname '*.gif' -o \
    -iname '*.bmp' -o \
    -iname '*.webp' -o \
    -iname '*.tif' -o \
    -iname '*.tiff' \
\) -print

if [[ "${force_delete}" != true ]]; then
    read -r -p "Delete these files? [y/N] " confirm
    if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
        echo "Deletion cancelled."
        exit 0
    fi
fi

find "${image_dir}" -maxdepth 1 -type f \( \
    -iname '*.png' -o \
    -iname '*.jpg' -o \
    -iname '*.jpeg' -o \
    -iname '*.gif' -o \
    -iname '*.bmp' -o \
    -iname '*.webp' -o \
    -iname '*.tif' -o \
    -iname '*.tiff' \
\) -delete
