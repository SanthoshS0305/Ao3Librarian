# Security Fix: Removing .env from Git History

GitHub detected a Discord bot token in the `.env` file that was committed to Git. 

## What Happened

The `.env` file (containing secrets) was accidentally committed in commit `07b8c90` (initial build). Even though `.env` is now in `.gitignore`, it still exists in Git history.

## Fix: Remove .env from Git History

Run these commands to remove `.env` from all commits:

```bash
# Remove .env from Git history using git filter-branch
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (warning: this rewrites history)
git push origin --force --all
```

**⚠️ IMPORTANT:** After running this, you should:
1. Reset your Discord bot token (the old one is now exposed)
2. Update your `.env` file with a new token
3. Notify team members that they need to re-clone the repository

## Alternative: Use git filter-repo (Recommended)

```bash
# Install git-filter-repo first (if not installed)
pip install git-filter-repo

# Remove .env from history
git filter-repo --path .env --invert-paths

# Force push
git push origin --force --all
```
