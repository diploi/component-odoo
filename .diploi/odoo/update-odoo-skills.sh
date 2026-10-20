#!/usr/bin/env bash
# Replace Odoo's skills in .agents/skills/ with the ones from Odoo's repository.
#
#   .diploi/odoo/update-odoo-skills.sh [ref]    # ref defaults to 20.0
#
# The skills are copied unchanged from skills/ on the branch of the Odoo version
# this component runs. Our own skills (odoo-scss-check) are never touched.
set -euo pipefail

ref="${1:-20.0}"
script_dir="$(cd "$(dirname "$0")" && pwd)"
skills_dir="$(cd "$script_dir/../../.agents/skills" && pwd)"
commit_file="$script_dir/odoo-skills-commit"
previous="$(cat "$commit_file" 2>/dev/null || true)"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Fetch only the requested commit, and of it only skills/: Odoo's full history
# is several gigabytes.
repo="$tmp/odoo"
git init --quiet "$repo"
git -C "$repo" remote add origin https://github.com/odoo/odoo
git -C "$repo" sparse-checkout set --no-cone /skills/
echo "Fetching skills/ from odoo/odoo@$ref..."
git -C "$repo" fetch --quiet --depth 1 --filter=blob:none origin "$ref"
git -C "$repo" checkout --quiet FETCH_HEAD
commit="$(git -C "$repo" rev-parse HEAD)"

if [ "$commit" = "$previous" ]; then
    echo "Already at odoo/odoo@$commit."
    exit 0
fi

for upstream in "$repo/skills"/*/; do
    name="$(basename "$upstream")"
    rm -rf "${skills_dir:?}/$name"
    cp -r "$upstream" "$skills_dir/$name"
    echo "Updated $name"
done
echo "$commit" > "$commit_file"

echo
if [ -n "$previous" ]; then
    echo "Upstream changes since odoo/odoo@${previous:0:10}:"
    git -C "$repo" fetch --quiet --depth 1 --filter=blob:none origin "$previous"
    git -C "$repo" diff --stat "$previous" "$commit" -- skills
    echo "Commits: https://github.com/odoo/odoo/compare/$previous...$commit"
else
    echo "Now at odoo/odoo@$commit."
fi
echo
echo "Review these changes, then commit."
