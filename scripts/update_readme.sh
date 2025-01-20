#!/usr/bin/env bash

set -euo pipefail

git_root=$(git rev-parse --show-toplevel)
venv_activate="${git_root}/.venv/bin/activate"
# Ensure .venv created
if [ ! -f "${venv_activate}" ]; then
    echo "Please create a virtual environment .venv in the project root directory."
    exit 1
fi

# Create a temporary file to store the new policy documentation
tmpfile=$(mktemp)

# Extract policies data from each YAML file and add to the temporary file
# shellcheck disable=SC1090
source "${venv_activate}"
echo '```mono' > "$tmpfile"
bundleutils help-pages >> "$tmpfile"
echo '```' >> "$tmpfile"

# Check if any policy data was extracted
if [[ -s $tmpfile ]]; then
    # Replace the old policy section in README.md with the new content
    mv "$tmpfile" new_section.md
    awk '
        /<!-- START help-pages-doc -->/ { print; found=1; while (getline < "new_section.md") print; next }
        /<!-- END help-pages-doc -->/ { found=0 }
        !found
    ' README.md > README.tmp && mv README.tmp README.md
fi

# Cleanup
rm -f "$tmpfile" new_section.md
