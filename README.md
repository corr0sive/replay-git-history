# replay-git-history

CLI utility to replay a public GitHub repo's commit history (full or limited) into a new repo in your organization, with automated Veracode scans on major release tags.

Goal: Create a "historical security posture" demo repo showing how Veracode results would have looked over time if scans ran on major releases.

## Features
- Creates target repo in your org if missing
- Replays commits (using `git format-patch` + `git am` for fidelity)
- Adds Veracode workflow in first commit
- Triggers scans only on major semver tags (configurable pattern)
- Limits to last N most-recent major tags (default 24) to control cost/runtime
- Incremental: resumes from last replay using `replay-state` branch
- Optional PR mirroring
- Warnings for LFS/submodules
- Single bot committer: "replay-git-history bot <no-reply@veracode.com>"
- Detailed logs + JSON summary per repo

## Prerequisites
- Python 3.10+
- Git installed
- Fine-grained GitHub PAT with:
  - Repository permissions: Contents (read/write), Pull requests (read/write if mirroring), Metadata (read)
  - Ability to create repositories in your org
- Veracode org-level secrets: `VERACODE_API_ID`, `VERACODE_API_KEY` (add in org Settings → Secrets → Actions)

## Installation
Clone this repo:
```bash
git clone https://github.com/corr0sive/replay-git-history.git
cd replay-git-history
pip install -r requirements.txt
