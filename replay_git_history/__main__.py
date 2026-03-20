
### Updated Code Skeleton (replay_git_history/__main__.py)

```python
# replay_git_history/__main__.py
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import git
import typer
import yaml
from github import Github, GithubException
from packaging import version as semver
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer()
console = Console()


def get_pat() -> str:
    pat = os.getenv("GH_PAT")
    if not pat:
        raise typer.Exit(
            "GH_PAT environment variable required. "
            "Set it with: export GH_PAT=ghp_...\n"
            "See README for fine-grained PAT setup."
        )
    return pat


@app.command()
def replay(
    config_path: Path = typer.Option(
        Path("config.yaml"), "--config", "-c", exists=True
    ),
    max_commits: int = typer.Option(
        5000, "--max-commits", help="Max commits to replay per repo (0 = unlimited)"
    ),
):
    with config_path.open() as f:
        cfg = yaml.safe_load(f)

    g = Github(get_pat())
    org_name = cfg["org"]
    org = g.get_organization(org_name)

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    for repo_cfg in cfg["repos"]:
        source_url = repo_cfg["source"]
        repo_name = source_url.rstrip("/").split("/")[-1]
        suffix = cfg.get("target_suffix", "")
        target_name = f"{repo_name}{suffix}"

        console.rule(f"Replaying {source_url} → {org_name}/{target_name}")

        start_time = datetime.now()
        summary: Dict = {
            "repo": target_name,
            "start_time": start_time.isoformat(),
            "commits_replayed": 0,
            "major_tags_detected": 0,
            "major_tags_triggered": 0,
            "warnings": [],
        }

        try:
            # 1. Create target repo if missing
            try:
                target_repo = org.get_repo(target_name)
                console.print("[yellow]Target exists — checking for incremental replay[/yellow]")
            except GithubException as e:
                if e.status == 404:
                    target_repo = org.create_repo(target_name, private=False, auto_init=False)
                    console.print("[green]Created new target repo[/green]")
                else:
                    raise

            # 2. Pause for secrets/org setup reminder
            console.print(
                "\n[bold yellow]PAUSE[/bold yellow]: Ensure org-level secrets VERACODE_API_ID / VERACODE_API_KEY are set.\n"
                "Press Enter to continue..."
            )
            input()

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp = Path(tmp_dir)
                source_path = tmp / "source"
                target_path = tmp / "target"

                # Clone source (shallow if possible, but need tags/history)
                git.Repo.clone_from(source_url, source_path, mirror=True)  # bare clone for efficiency
                source_git = git.Repo(source_path)

                # Init or clone target
                if target_path.exists():
                    target_git = git.Repo(target_path)
                else:
                    target_git = git.Repo.init(target_path)

                # TODO: Read replay-state branch for last_sha
                # last_sha = get_last_replayed_sha(target_git, target_repo)

                # Discover tags & filter majors
                tags = source_git.tags
                major_tags = []
                pattern = repo_cfg.get("major_tag_pattern", r"^v[0-9]+\.")
                import re
                regex = re.compile(pattern)
                for tag in tags:
                    if regex.match(tag.name):
                        major_tags.append(tag)
                major_tags.sort(key=lambda t: semver.parse(t.name.lstrip("v")), reverse=True)  # newest first
                summary["major_tags_detected"] = len(major_tags)

                max_scans = repo_cfg.get("max_scans", 24)
                if max_scans > 0:
                    major_tags = major_tags[:max_scans]
                summary["major_tags_triggered"] = len(major_tags)

                console.print(
                    f"Detected {summary['major_tags_detected']} major tags; "
                    f"will trigger scans on {summary['major_tags_triggered']} most recent."
                )

                # Determine replay range (from root or last_sha to HEAD, or up to earliest major tag commit if limited)
                # For simplicity: replay from root if first run, else delta
                # TODO: implement delta patches

                # Placeholder replay loop (expand later)
                with Progress(
                    SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
                ) as progress:
                    task = progress.add_task("Replaying commits...", total=100)  # placeholder
                    # ... git format-patch range > patches.mbox
                    # target_git.git.am("--committer-date-is-author-date", "--signoff", input=patches)
                    # Override committer: target_git.config_writer().set_value("user", "name", "replay-git-history bot").release()
                    # target_git.config_writer().set_value("user", "email", "no-reply@veracode.com").release()
                    progress.update(task, completed=50)  # simulate

                # Create/add Veracode workflow if first run
                # Push tags for majors
                # Update replay-state branch

                # Warnings example
                if ".gitmodules" in source_git.tree().traverse():
                    summary["warnings"].append("Submodules detected — may affect build")
                # LFS check via .gitattributes

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            summary["error"] = str(e)

        finally:
            end_time = datetime.now()
            summary["runtime_seconds"] = (end_time - start_time).total_seconds()
            log_file = logs_dir / f"replay-{repo_name}.json"
            with log_file.open("w") as f:
                json.dump(summary, f, indent=2)
            console.print(f"Summary saved to {log_file}")
            console.print("[green]Done.[/green]")

if __name__ == "__main__":
    app()