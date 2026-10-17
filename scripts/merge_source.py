#!/usr/bin/env python3
"""Clone NagarSeva, merge the local evidence pack, and optionally publish anew.

The original remote is read only. A clean, committed fresh repository is required.
No credentials are accepted as command-line arguments or written into this repo.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://github.com/vishal88736/affordable-housing-slum-redevelopment-and-basic-service-assurance.git"
TARGET = "vishal88736/nagarseva-seva-first"
TARGET_URL = "https://github.com/" + TARGET
STATUS = ROOT / "integration/status.json"


def run(args, cwd=ROOT, capture=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1")
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=capture)
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip() if capture else ""
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}" + ("\n" + detail if detail else ""))
    return result.stdout.strip() if capture else ""


def save_status(state):
    STATUS.write_text(json.dumps(state, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_plan(source, destination):
    """Plan all imports before copying; no silent overwrites or external links."""
    entries = run(["git", "ls-tree", "-r", "-z", "--full-tree", "HEAD"], cwd=source, capture=True)
    files, special = [], {}
    for line in entries.split("\0"):
        if not line:
            continue
        info, name = line.split("\t", 1)
        mode, kind, _ = info.split()
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or any(p in {".git", ".aws", ".codex", ".agents", "node_modules", ".venv"} for p in rel.parts):
            raise RuntimeError(f"Unsafe or local-only source path: {name}")
        if any(p == ".env" or (p.startswith(".env.") and p not in {".env.example", ".env.sample", ".env.template"}) for p in rel.parts) or rel.suffix in {".sqlite", ".sqlite3", ".db", ".pem", ".key"}:
            raise RuntimeError(f"Review potentially private source file before import: {name}")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise RuntimeError(f"Review non-regular tracked source path before import: {name}")
        src = source / rel
        if not src.is_file() or src.is_symlink():
            raise RuntimeError(f"Source checkout file is unavailable or a link: {name}")
        if name in {".gitignore", "README.md"}:
            special[name] = src
            continue
        dest = destination / rel
        if dest.is_symlink() or any(p.is_symlink() for p in dest.parents if p != destination):
            raise RuntimeError(f"Destination contains a symlink: {name}")
        if dest.exists() and (not dest.is_file() or digest(src) != digest(dest)):
            raise RuntimeError(f"Merge conflict; existing work will not be overwritten: {name}")
        for parent in dest.parents:
            if parent == destination:
                break
            if parent.exists() and not parent.is_dir():
                raise RuntimeError(f"Destination parent is not a directory: {name}")
        files.append((name, src, dest))
    if not any(name == "nagarseva/README.md" for name, _, _ in files):
        raise RuntimeError("Expected NagarSeva application structure was not found.")
    return files, special


def merge_source(state):
    cache = ROOT / ".merge-work/source"
    cache.parent.mkdir(exist_ok=True)
    if cache.exists():
        actual = run(["git", "remote", "get-url", "origin"], cwd=cache, capture=True)
        if actual != SOURCE or run(["git", "status", "--porcelain"], cwd=cache, capture=True):
            raise RuntimeError("Existing source cache has a different remote or local edits; review it first.")
    else:
        run(["git", "clone", "--branch", "main", "--single-branch", "--", SOURCE, str(cache)])
    commit = run(["git", "rev-parse", "HEAD"], cwd=cache, capture=True)
    files, special = source_plan(cache, ROOT)
    public = ROOT / "nagarseva/website/public/evidence/index.html"
    if public.exists() or any(name == "nagarseva/website/public/evidence/index.html" for name, _, _ in files):
        raise RuntimeError("The evidence public route already exists; review the conflict first.")
    manifest = {name: {"bytes": src.stat().st_size, "sha256": digest(src)} for name, src, _ in files}
    for name, src, dest in files:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(src, dest)
        if digest(src) != digest(dest):
            raise RuntimeError(f"Imported file failed its hash check: {name}")
    if ".gitignore" in special:
        upstream_ignore = special[".gitignore"].read_text()
        current = (ROOT / ".gitignore").read_text()
        (ROOT / ".gitignore").write_text(upstream_ignore + "\n# Integrated evidence work and local exclusions\n" + current)
        manifest[".gitignore"] = {"upstream_sha256": digest(special[".gitignore"]), "handling": "combined with local rules"}
    if "README.md" in special:
        shutil.copy2(special["README.md"], ROOT / "integration/upstream-root-README.txt")
        manifest["README.md"] = {"upstream_sha256": digest(special["README.md"]), "handling": "original retained in integration/upstream-root-README.txt"}
    (ROOT / "integration/source-manifest.json").write_text(json.dumps({"repository": SOURCE, "commit": commit, "imported_at": datetime.now(timezone.utc).isoformat(), "files": manifest}, indent=2) + "\n")
    (ROOT / "README.md").write_text("""# NagarSeva + Seva Evidence

NagarSeva's urban-housing and service-assurance application, combined with a research-led evidence workbench and Seva First submission materials.

- [NagarSeva application and run instructions](nagarseva/README.md)
- [Evidence workbench and demonstration](prototype/README.md)
- [Open the self-contained evidence workbench](prototype/dist/standalone.html)
- [Research overview](research/README.md) and [executive findings](research/research_summary.md)
- [Draft application, six-slide deck, budget and pitch](submission/README.md)
- [Source lineage, merge procedure and limits](integration/README.md)
- [Executed evidence checks](research/prototype_validation.md)

## Run the applications

Follow the NagarSeva guide for the FastAPI backend and React/Vite frontend. The evidence workbench is additionally served at `/evidence/` by Vite and included in its production build. It can also be opened independently from `prototype/dist/standalone.html`, without a server or credentials.

Run `python3 prototype/scripts/verify.py` and then `python3 submission/scripts/prepare_pack.py` to verify and rebuild the evidence/submission materials. Refresh the Vite copy with `python3 scripts/sync_evidence.py` after changing the standalone artifact.

## Evidence boundaries

Synthetic planning data, trained models, hypothetical budgets and author-written test fixtures do not establish field accuracy, cost savings or government adoption. Preserve NagarSeva's synthetic-data labels and model limitations. The evidence workbench keeps public-record audits, historical statistics, unknown service baselines and a clearly labelled synthetic sandbox separate. It does not make eligibility or relocation decisions.

Browser checks in the preparation environment were blocked before assertions; no new browser or original-application test pass is claimed by this merge. Original-application tests must be run separately in a compatible environment. Applicant personal details remain omitted, and authenticated application limits remain unverified.

The original repository is unchanged. Its commit and imported-file hashes are recorded in `integration/source-manifest.json`. This fresh repository does not import its Git history or imply that either prototype is a production public service.
""")
    run([sys.executable, "prototype/scripts/verify.py"])
    run([sys.executable, "submission/scripts/prepare_pack.py"])
    run([sys.executable, "scripts/sync_evidence.py"])
    state.update(state="MERGED_LOCALLY", source_commit=commit, source_merged=True, original_application_tests="not run by the merge helper", evidence_validation="passed", field_validation=False, blockers=[])
    save_status(state)
    run(["git", "add", "--all"])
    # Preserve upstream tracked artifacts even when its own ignore rules match.
    names = [name for name, _, _ in files]
    for start in range(0, len(names), 80):
        run(["git", "add", "-f", "--", *names[start:start + 80]])
    run(["git", "commit", "-m", "Merge NagarSeva source with research, evidence workbench and submission pack"])


def publish(state):
    if run(["gh", "api", "user", "--jq", ".login"], capture=True).lower() != "vishal88736":
        raise RuntimeError("The GitHub account must be vishal88736 for this new repository.")
    remotes = run(["git", "remote"], capture=True).splitlines()
    if "origin" in remotes:
        actual = run(["git", "remote", "get-url", "origin"], capture=True)
        if actual.removesuffix(".git") not in {TARGET_URL, "git@github.com:" + TARGET}:
            raise RuntimeError("An origin remote already exists; refusing to repoint or push to it.")
    elif state.get("new_github_repository_created") and state.get("new_repository_url") == TARGET_URL:
        run(["git", "remote", "add", "origin", TARGET_URL + ".git"])
    else:
        run(["gh", "repo", "create", TARGET, "--private", "--source", str(ROOT), "--remote", "origin", "--description", "NagarSeva urban housing and service assurance with research and an evidence workbench"])
        state.update(remote_created_by_this_helper=True, new_github_repository_created=True, new_repository_url=TARGET_URL, state="REMOTE_CREATED", push_verification="Check the local .merge-work/published.json receipt or compare git ls-remote with HEAD.")
        save_status(state)
        run(["git", "add", "integration/status.json"])
        run(["git", "commit", "-m", "Record new private repository location"])
    run(["git", "push", "-u", "origin", "main"])
    local = run(["git", "rev-parse", "HEAD"], capture=True)
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"], capture=True).split()[0]
    if remote != local:
        raise RuntimeError("Push could not be verified against the local main commit.")
    receipt = ROOT / ".merge-work/published.json"
    receipt.parent.mkdir(exist_ok=True)
    receipt.write_text(json.dumps({"repository": TARGET_URL, "verified_main_commit": local, "verified_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"Verified new repository: {TARGET_URL}\nVerified main commit: {local}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Create and push a new private GitHub repository after merging")
    args = parser.parse_args()
    if run(["git", "rev-parse", "--show-toplevel"], capture=True) != str(ROOT):
        raise RuntimeError("Run this inside its own fresh repository.")
    if run(["git", "branch", "--show-current"], capture=True) != "main":
        raise RuntimeError("The fresh repository must be on main.")
    if run(["git", "status", "--porcelain"], capture=True):
        raise RuntimeError("Commit or review existing local changes before merging; nothing was overwritten.")
    state = json.loads(STATUS.read_text())
    if not state.get("source_merged"):
        merge_source(state)
    if args.publish:
        publish(state)
    else:
        print("NagarSeva source merged and committed locally. No GitHub repository was created by this invocation.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Merge/publish stopped: {error}", file=sys.stderr)
        print("Original repository unchanged. Inspect integration/status.json and git status before retrying.", file=sys.stderr)
        raise SystemExit(1)
