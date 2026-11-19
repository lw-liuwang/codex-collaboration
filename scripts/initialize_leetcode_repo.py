#!/usr/bin/env python3
"""Initialize the current account's LeetCode repository with gh and Git."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS = {"A": "lw-liuwang", "B": "ZicongHe2002"}


def command(arguments, directory=None):
    result = subprocess.run(arguments, cwd=directory, text=True, encoding="utf-8", capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def check_window():
    hour = datetime.now(timezone(timedelta(hours=8))).hour
    if not 9 <= hour < 23:
        raise RuntimeError("GitHub writes are restricted to 09:00–23:00 Asia/Shanghai")


def api(endpoint, method="GET", body=None):
    arguments = ["gh", "api", "--method", method, endpoint]
    payload = None
    if method != "GET":
        check_window()
    if body is not None:
        arguments += ["--input", "-"]
        payload = json.dumps(body)
    result = subprocess.run(arguments, input=payload, text=True, encoding="utf-8", capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout) if result.stdout.strip() else None


def pages(endpoint):
    result = []
    page = 1
    while True:
        data = api(f"{endpoint}?per_page=100&page={page}")
        result.extend(data)
        if len(data) < 100:
            return result
        page += 1


def matches(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(matches(actual.get(k), v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(matches(a, e) for a, e in zip(actual, expected))
    return actual == expected


def initialize(actor, directory):
    owner = ACCOUNTS[actor]
    peer = ACCOUNTS["B" if actor == "A" else "A"]
    if api("user")["login"] != owner:
        raise RuntimeError(f"Use only the local {owner} account; do not switch credentials")
    repository = f"{owner}/leetcode-solutions"
    # Only an explicit 404 means absent; network/authentication failures are not absence.
    probe = subprocess.run(["gh", "api", f"repos/{repository}"], text=True, encoding="utf-8", capture_output=True)
    if probe.returncode:
        try:
            absent = json.loads(probe.stdout).get("status") == "404"
        except (ValueError, AttributeError):
            absent = False
        if not absent:
            raise RuntimeError(probe.stderr.strip() or probe.stdout.strip())
        check_window()
        creation = subprocess.run(["gh", "repo", "create", repository, "--public", "--description", "LeetCode双账号题解协作：A Python，B C++17，正式Code review"], text=True, encoding="utf-8", capture_output=True)
        # Read back before any retry after an uncertain creation response.
        info = api(f"repos/{repository}")
        if creation.returncode and info["full_name"] != repository:
            raise RuntimeError(creation.stderr.strip())
    info = api(f"repos/{repository}")
    if not info["permissions"]["admin"] or info["private"]:
        raise RuntimeError("Expected the current account's public repository with admin access")
    directory = directory.resolve()
    if not directory.exists():
        directory.parent.mkdir(parents=True, exist_ok=True)
        command(["git", "clone", info["clone_url"], str(directory)])
    remote = command(["git", "remote", "get-url", "origin"], directory)
    if remote.removesuffix(".git") != info["clone_url"].removesuffix(".git"):
        raise RuntimeError(f"Existing directory has a different origin: {directory}")
    initial = not command(["git", "ls-remote", "origin", "HEAD"], directory)
    if initial:
        if command(["git", "status", "--porcelain"], directory):
            raise RuntimeError("The empty checkout contains local files; preserve and inspect them first")
        command(["git", "symbolic-ref", "HEAD", "refs/heads/main"], directory)
        paths = []
        for source in sorted((ROOT / "templates" / "leetcode").rglob("*")):
            if source.is_file():
                relative = source.relative_to(ROOT / "templates" / "leetcode")
                target = directory / relative
                if target.exists():
                    raise RuntimeError(f"Refusing to overwrite {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                content = source.read_text(encoding="utf-8").replace("{{OWNER}}", owner).replace("{{PEER}}", peer)
                target.write_text(content, encoding="utf-8", newline="\n")
                paths.append(relative.as_posix())
        command(["git", "add", "--", *paths], directory)
        command(["git", "diff", "--cached", "--check"], directory)
        email = "90660621+lw-liuwang@users.noreply.github.com" if actor == "A" else "113126532+ZicongHe2002@users.noreply.github.com"
        command(["git", "-c", f"user.name={owner}", "-c", f"user.email={email}", "commit", "-m", "建立LeetCode题解目录与双仓库互投评审约定", "-m", "初始化由本机账号完成；脚手架由A提供、OpenAI Codex辅助整理，不将模板使用冒充共同创作。"], directory)
        check_window()
        command(["git", "push", "-u", "origin", "main"], directory)
    api(f"repos/{repository}", "PATCH", {"default_branch": "main", "has_issues": True, "allow_merge_commit": True, "allow_squash_merge": False, "allow_rebase_merge": False})
    desired = json.loads((ROOT / "config" / "required-review-ruleset.json").read_text(encoding="utf-8"))
    managed = [r for r in pages(f"repos/{repository}/rulesets") if r["name"] == desired["name"]]
    if len(managed) > 1:
        raise RuntimeError("Multiple managed rulesets; inspect before changing anything")
    if not managed:
        api(f"repos/{repository}/rulesets", "POST", desired)
        managed = [r for r in pages(f"repos/{repository}/rulesets") if r["name"] == desired["name"]]
    rule = api(f"repos/{repository}/rulesets/{managed[0]['id']}")
    if not matches(rule, desired):
        raise RuntimeError("Existing review rules differ; inspect instead of overwriting")
    effective = pages(f"repos/{repository}/rules/branches/main")
    if not any(r["ruleset_id"] == rule["id"] and r["type"] == "pull_request" and matches(r["parameters"], desired["rules"][0]["parameters"]) for r in effective):
        raise RuntimeError("Required review rule is not effective on main")
    if rule["bypass_actors"] or rule["current_user_can_bypass"] != "never":
        raise RuntimeError("Expected no approval bypass")
    collaborators = pages(f"repos/{repository}/collaborators")
    pending = pages(f"repos/{repository}/invitations")
    if not any(c["login"] == peer for c in collaborators) and not any(i["invitee"]["login"] == peer for i in pending):
        api(f"repos/{repository}/collaborators/{peer}", "PUT", {"permission": "push"})
        pending = pages(f"repos/{repository}/invitations")
    return {"repository": repository, "directory": str(directory), "initialContentCreated": initial, "rulesetUrl": rule["_links"]["html"]["href"], "requiredApprovals": 1, "bypassActors": [], "peerInvitationPending": any(i["invitee"]["login"] == peer for i in pending), "existingContentOverwritten": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", choices=ACCOUNTS, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(initialize(args.actor, args.directory), ensure_ascii=False, indent=2))
    except (RuntimeError, OSError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
