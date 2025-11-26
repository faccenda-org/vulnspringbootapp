#!/usr/bin/env python3
"""
Auto-merge decision script for Dependabot PRs.

- Reads GitHub Actions event payload when available.
- Supports local execution with CLI flags or env vars to fetch PR info.
- Outputs MERGE_ALLOWED for Actions and prints a concise decision for local runs.
"""

import argparse
import json
import os
import re
import sys
from typing import Optional, Tuple

try:
    from github import Github, Auth
except Exception:  # pragma: no cover - fallback if PyGithub is not installed
    Github = None
    Auth = None


def parse_version(v: str) -> Optional[Tuple[int, int, int]]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$", v.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def get_upgrade_type(title: str) -> str:
    bump = re.search(r"Bump\s+.+\s+from\s+([0-9]+\.[0-9]+\.[0-9]+)\s+to\s+([0-9]+\.[0-9]+\.[0-9]+)", title, re.IGNORECASE)
    if not bump:
        return "unknown"
    from_v = parse_version(bump.group(1))
    to_v = parse_version(bump.group(2))
    if not from_v or not to_v:
        return "unknown"
    if to_v[0] != from_v[0]:
        return "major"
    if to_v[1] != from_v[1]:
        return "minor"
    if to_v[2] != from_v[2]:
        return "patch"
    return "unknown"


def get_compat_score(body: str) -> Optional[int]:
    patterns = (
        re.compile(r"Compatibility\s+score\s*[:|-]?\s*(\d{1,3})%", re.IGNORECASE),
        re.compile(r"Update\s+confidence[\s\S]*?(\d{1,3})%", re.IGNORECASE),
        re.compile(r"Confidence[\s\S]*?(\d{1,3})%", re.IGNORECASE),
    )
    for rx in patterns:
        match = rx.search(body or "")
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def read_event() -> Optional[dict]:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def write_output(key: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write(f"{key}={value}\n")


def append_summary(text: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(f"\n{text}\n")


def load_threshold(event_inputs: Optional[dict]) -> int:
    dispatch = None
    if isinstance(event_inputs, dict):
        dispatch = event_inputs.get("compat_threshold")
    threshold_str = (
        (dispatch if dispatch else None)
        or os.environ.get("DEPENDABOT_COMPAT_THRESHOLD")
        or os.environ.get("DEFAULT_COMPAT_THRESHOLD")
        or "80"
    )
    try:
        return int(threshold_str)
    except ValueError:
        return 80


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dependabot auto-merge decision script")
    parser.add_argument("--repo", help="Repository in the form owner/repo")
    parser.add_argument("--pr", type=int, help="Pull request number")
    parser.add_argument("--compat-threshold", type=int, help="Threshold percentage override")
    parser.add_argument("--enable-automerge", action="store_true", help="Attempt to enable auto-merge (local runs)")
    return parser.parse_args(argv)


def resolve_pr_context(args: argparse.Namespace, token: str) -> tuple[str, int, str, str, str, Optional[dict]]:
    """Resolve repo/pr, title/body/author and event inputs from Actions or CLI/env."""
    event = read_event()
    inputs = event.get("inputs") if isinstance(event, dict) else None
    if event and "pull_request" in event:
        repo_full = os.environ.get("GITHUB_REPOSITORY")
        pr_number = event["pull_request"].get("number")
        title = event["pull_request"].get("title") or ""
        body = event["pull_request"].get("body") or ""
        author_login = event["pull_request"].get("user", {}).get("login") or ""
        return repo_full, pr_number, title, body, author_login, inputs
    # Local mode
    pr_ref = os.environ.get("PR_REF")
    repo_full = args.repo
    pr_number = args.pr
    if pr_ref and "#" in pr_ref and (not repo_full or not pr_number):
        repo_full, pr_num = pr_ref.split("#", 1)
        pr_number = int(pr_num)
    if not repo_full or not pr_number:
        raise ValueError("Provide --repo owner/repo and --pr 123 or PR_REF=owner/repo#123")
    gh = Github(auth=Auth.Token(token)) if Auth else Github(token)
    repo = gh.get_repo(repo_full)
    pr_obj = repo.get_pull(number=int(pr_number))
    title = pr_obj.title or ""
    body = pr_obj.body or ""
    author_login = pr_obj.user.login or ""
    return repo_full, int(pr_number), title, body, author_login, inputs


def build_reasons(upgrade_type: str, compat_score: Optional[int], threshold: int) -> list[str]:
    return [
        f"upgrade type: {upgrade_type}",
        f"compatibility score: {str(compat_score) + '%' if compat_score is not None else 'not found'}",
        f"threshold: {threshold}%",
    ]


def compute_decision(upgrade_type: str, compat_score: Optional[int], threshold: int) -> bool:
    return (upgrade_type == "patch") or (upgrade_type == "minor" and compat_score is not None and compat_score >= threshold)


def connect_github(token: str, repo_full: str, pr_number: int):
    gh = Github(auth=Auth.Token(token)) if Auth else Github(token)
    repo = gh.get_repo(repo_full)
    issue = repo.get_issue(number=pr_number)
    pr_obj = repo.get_pull(number=pr_number)
    return repo, issue, pr_obj


def handle_skip_label(pr_obj, issue, reason_parts: list[str]) -> bool:
    skip_label = (os.environ.get("NO_AUTO_MERGE_LABEL", "no-auto-merge") or "no-auto-merge").lower()
    label_names = [lbl.name for lbl in pr_obj.get_labels()]
    if skip_label in [name.lower() for name in label_names]:
        issue.create_comment(
            (
                f"Skipping auto-merge due to '{skip_label}' label.\n\n"
                + "**Decision Details**\n"
                + "- "
                + "\n- ".join(reason_parts)
            )
        )
        append_summary("Result: skip (comment posted)")
        write_output("MERGE_ALLOWED", "false")
        print("Skip: label present")
        return True
    return False


def post_manual_review(issue, reason_parts: list[str]) -> None:
    body = (
        "Requires manual review.\n\n"
        + "**Decision Details**\n"
        + "- "
        + "\n- ".join(reason_parts)
    )
    issue.create_comment(body)
    append_summary("Result: manual review requested (comment posted)")
    write_output("MERGE_ALLOWED", "false")
    print("Manual review required")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.compat_threshold is not None:
        os.environ["DEPENDABOT_COMPAT_THRESHOLD"] = str(args.compat_threshold)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    try:
        repo_full, pr_number, title, body, author_login, inputs = resolve_pr_context(args, token)
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 1

    upgrade_type = get_upgrade_type(title)
    compat_score = get_compat_score(body)
    threshold = load_threshold(inputs)
    reason_parts = build_reasons(upgrade_type, compat_score, threshold)
    should_merge = compute_decision(upgrade_type, compat_score, threshold)

    _, issue, pr_obj = connect_github(token, repo_full, pr_number)

    if handle_skip_label(pr_obj, issue, reason_parts):
        return 0

    is_dependabot = (author_login.lower() == "dependabot[bot]")
    if should_merge and is_dependabot:
        write_output("MERGE_ALLOWED", "true")
        append_summary("Decision: auto-merge enabled when checks pass")
        print("Allowed: auto-merge can be enabled")
        if args.enable_automerge:
            merge_method = os.environ.get("MERGE_METHOD", "squash")
            try:
                issue.create_comment(
                    (
                        "Local run: would enable auto-merge.\n\n"
                        + "**Settings**\n"
                        + f"- merge method: `{merge_method}`\n"
                    )
                )
            except Exception as exc:
                issue.create_comment(
                    (
                        "Local run: failed to enable auto-merge.\n\n"
                        + "<details><summary>Error details</summary>\n\n"
                        + "```\n"
                        + f"{exc}"
                        + "\n```\n"
                        + "</details>\n"
                    )
                )
        return 0

    post_manual_review(issue, reason_parts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
