#!/bin/bash
# Sync fork with upstream open-webui repo while preserving QC feature changes.
#
# Usage: bash scripts/sync-upstream.sh
#
# What this does:
#   1. Fetches latest from upstream (open-webui/open-webui)
#   2. Creates a backup branch of your current state
#   3. Merges upstream/main into your main branch
#   4. If conflicts occur, lists them so you can resolve manually
#
# Files most likely to conflict (QC touches these shared files):
#   - backend/open_webui/config.py          (QC permission defaults)
#   - backend/open_webui/main.py            (QC router registration)
#   - backend/requirements.txt              (pymupdf dependency)
#   - pyproject.toml                        (pymupdf dependency)
#   - src/lib/components/layout/Sidebar.svelte (QC nav entry)
#   - src/lib/stores/index.ts               (QC store)
#   - Alembic migration chain               (new migrations from upstream)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Open WebUI Fork Sync ===${NC}"
echo ""

# Ensure we're on main
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}Error: Not on main branch (currently on '$CURRENT_BRANCH').${NC}"
    echo "Switch to main first: git checkout main"
    exit 1
fi

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${RED}Error: You have uncommitted changes. Commit or stash them first.${NC}"
    git status --short
    exit 1
fi

# Fetch upstream
echo -e "${YELLOW}Fetching upstream...${NC}"
git fetch upstream

# Check if there's anything new
BEHIND=$(git rev-list --count main..upstream/main)
if [ "$BEHIND" -eq 0 ]; then
    echo -e "${GREEN}Already up to date with upstream. Nothing to do.${NC}"
    exit 0
fi

echo -e "${YELLOW}$BEHIND commits behind upstream/main${NC}"

# Create backup branch
BACKUP_BRANCH="backup/pre-sync-$(date +%Y%m%d-%H%M%S)"
echo -e "${YELLOW}Creating backup branch: $BACKUP_BRANCH${NC}"
git branch "$BACKUP_BRANCH"

# Attempt merge
echo -e "${YELLOW}Merging upstream/main...${NC}"
if git merge upstream/main --no-edit; then
    echo ""
    echo -e "${GREEN}=== Merge successful! ===${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test the application to make sure QC feature still works"
    echo "  2. Push to your fork:  git push origin main"
    echo "  3. Delete backup branch if all good:  git branch -d $BACKUP_BRANCH"
else
    echo ""
    echo -e "${RED}=== Merge conflicts detected ===${NC}"
    echo ""
    echo "Conflicting files:"
    git diff --name-only --diff-filter=U
    echo ""
    echo -e "${YELLOW}How to resolve:${NC}"
    echo "  1. Open each conflicting file and resolve the conflicts"
    echo "  2. For QC-related conflicts, keep BOTH upstream changes and your QC additions"
    echo "  3. Stage resolved files:  git add <file>"
    echo "  4. Complete the merge:    git commit"
    echo "  5. Test the application"
    echo "  6. Push to your fork:     git push origin main"
    echo ""
    echo "  To abort the merge:       git merge --abort"
    echo "  Backup branch available:  $BACKUP_BRANCH"
fi
