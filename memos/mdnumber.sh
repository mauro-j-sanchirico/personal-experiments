#!/usr/bin/env bash

# Generate a copy of a Markdown file with numbered headings, starting at ##.
# Usage: mdnumber.sh input.md [output.md]

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 || ! -f "$1" ]]; then
    echo "Usage: $(basename "$0") input.md [output.md]"
    exit 1
fi

input="$1"
output="${2:-${input%.md}_numbered.md}"

if [[ "$input" == "$output" ]]; then
    echo "Error: Input and output must be different files."
    exit 1
fi

awk '
/^ *(```+|~~~+)/ {
    s=$0; sub(/^ */, "", s)
    c=substr(s,1,1); k=0
    while(substr(s,k+1,1)==c) k++
    if(!f && k>=3) {f=1;fc=c;fn=k}
    else if(f && c==fc && k>=fn && substr(s,k+1)~/^[[:space:]]*$/) f=0
    print; next
}
f {print; next}
/^#{2,6} / {
    match($0,/^#+/); d=RLENGTH
    s=substr($0,d+2)
    sub(/^[0-9]+(\.[0-9]+)*[.)]? +/,"",s)
    n[d]++
    for(i=d+1;i<=6;i++) n[i]=0
    num=n[2]
    for(i=3;i<=d;i++) num=num "." n[i]
    print substr("######",1,d) " " num " " s
    next
}
{print}
' "$input" > "$output"

echo "Created: $output"