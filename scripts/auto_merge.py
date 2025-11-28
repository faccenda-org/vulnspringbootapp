#!/usr/bin/env python3
"""
Dependabot auto-merge decision helper.

Why these choices:
- Read event payload when present to avoid extra API calls in Actions.
- Prefer native auto-merge enabling so runners don't wait for checks.
- Post comments with dedupe markers to avoid noisy duplicates across reruns.
"""

import argparse
import json
import logging
import os
import re
import sys
import requests

from typing import Optional, Tuple

try:
    from github import Github, Auth
except Exception:  # Fallback: allow local syntax checks without PyGithub installed
    Github = None
    Auth = None


def parse_version(v: str) -> Optional[Tuple[int, int, int]]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$", v.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def get_upgrade_type(title: str) -> str:
    logging.debug(f"Parsing upgrade type from title: {title}")
    bump = re.search(
        r"bump\s+.+\s+from\s+([0-9]+\.[0-9]+\.[0-9]+)\s+to\s+([0-9]+\.[0-9]+\.[0-9]+)",
        title,
        re.IGNORECASE,
    )
    if not bump:
        return "not-semver"
    from_v = parse_version(bump.group(1))
    to_v = parse_version(bump.group(2))
    logging.debug(
        f"Upgrade: {bump.group(1)} -> {bump.group(2)} | parsed: {from_v} -> {to_v}"
    )
    if not from_v or not to_v:
        return "unknown"
    if to_v[0] != from_v[0]:
        return "Major"
    if to_v[1] != from_v[1]:
        return "Minor"
    if to_v[2] != from_v[2]:
        return "Patch"
    return "unknown"


def get_compat_score(body: str) -> Optional[int]:
    svg_url_patterns = (
        re.compile(r"\[!\[Dependabot compatibility score\]\((.*)\)\]", re.IGNORECASE),
    )
    for rx in svg_url_patterns:
        svg_url_match = rx.search(body or "")
        if svg_url_match:
            try:
                score_svg_url = svg_url_match.group(1)
                logging.debug(f"Found compatibility score SVG URL: {score_svg_url}")
                compat_score_pattern = re.compile(r"<title>compatibility: (\d+)%</title>")
                svg = requests.get(score_svg_url).text
                compat_score_match = compat_score_pattern.search(svg)
                if compat_score_match:
                    logging.debug(f"Extracted compatibility score: {compat_score_match.group(1)}%")
                    return int(compat_score_match.group(1))
            except ValueError:
                continue
    return "unkown"


def read_event() -> Optional[dict]:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if path and os.path.exists(path):
        logging.debug(f"Reading GitHub event payload from {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def write_output(key: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write(f"{key}={value}\n")


def append_summary(text: str) -> None:
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as fh:
            fh.write(f"{text}\n")


def load_threshold(event_inputs: Optional[dict]) -> int:
    dispatch = None
    if isinstance(event_inputs, dict):
        dispatch = event_inputs.get("compat_threshold")
        logging.debug(f"Workflow dispatch input compat_threshold: {dispatch}")
    threshold_str = (
        (dispatch if dispatch else None)
        or os.environ.get("DEPENDABOT_COMPAT_THRESHOLD")
        or os.environ.get("DEFAULT_COMPAT_THRESHOLD")
        or "80"
    )
    try:
        threshold_val = int(threshold_str)
        logging.debug(f"Resolved compatibility threshold: {threshold_val}")
        return threshold_val
    except ValueError:
        logging.warning(f"Invalid threshold value '{threshold_str}', defaulting to 80")
        return 80


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dependabot auto-merge decision script"
    )
    parser.add_argument("--repo", help="Repository in the form owner/repo")
    parser.add_argument("--pr", type=int, help="Pull request number")
    parser.add_argument(
        "--pr-url",
        help="PR URL (e.g., https://github.com/owner/repo/pull/123 or owner/repo/pull/123)",
    )
    parser.add_argument(
        "--compat-threshold", type=int, help="Threshold percentage override"
    )
    parser.add_argument(
        "--enable-automerge",
        action="store_true",
        help="Attempt to enable auto-merge (local runs)",
    )
    return parser.parse_args(argv)


def parse_pr_url(pr_url: str) -> tuple[str, int]:
    """Parse PR URL or path into (owner/repo, pr_number)."""
    pr_url = pr_url.strip()
    pattern = r"(?:https?://github\.com/)?([^/]+/[^/]+)/pull/(\d+)"
    match = re.match(pattern, pr_url)
    if not match:
        raise ValueError(
            f"Invalid PR URL format: {pr_url}. Expected format: owner/repo/pull/123 or full URL"
        )
    return match.group(1), int(match.group(2))


def resolve_pr_context(
    args: argparse.Namespace, token: str
) -> tuple[str, int, str, str, str, Optional[dict]]:
    """Resolve PR context from Actions event when available, else API.

    Why: Using the event payload avoids unnecessary GitHub API calls during
    Actions runs and reduces rate-limit pressure.
    """
    event = read_event()
    inputs = event.get("inputs") if isinstance(event, dict) else None
    if event and "pull_request" in event:
        repo_full = os.environ.get("GITHUB_REPOSITORY")
        pr_number = event["pull_request"].get("number")
        title = event["pull_request"].get("title", "")
        body = event["pull_request"].get("body", "")
        author_login = event["pull_request"].get("user", {}).get("login", "")
        logging.info(
            f"Event PR context: repo={repo_full}, pr={pr_number}, author={author_login}"
        )
        return repo_full, pr_number, title, body, author_login, inputs

    repo_full = args.repo
    pr_number = args.pr

    if args.pr_url:
        repo_full, pr_number = parse_pr_url(args.pr_url)
        logging.debug(f"Parsed PR URL: repo={repo_full}, pr={pr_number}")

    pr_ref = os.environ.get("PR_REF")
    if pr_ref and "#" in pr_ref and (not repo_full or not pr_number):
        repo_full, pr_num = pr_ref.split("#", 1)
        pr_number = int(pr_num)

    if not repo_full or not pr_number:
        raise ValueError(
            "Provide --pr-url, --repo owner/repo and --pr 123, or PR_REF=owner/repo#123"
        )
    if not Github:
        raise ImportError("PyGithub is required. Install with: pip install PyGithub")
    gh = Github(auth=Auth.Token(token)) if Auth else Github(token)
    repo = gh.get_repo(repo_full)
    pr_obj = repo.get_pull(number=int(pr_number))
    title = pr_obj.title or ""
    body = pr_obj.body or ""
    author_login = pr_obj.user.login or ""
    logging.info(
        f"Local PR context: repo={repo_full}, pr={pr_number}, author={author_login}"
    )
    return repo_full, int(pr_number), title, body, author_login, inputs


def build_reasons(
    upgrade_type: str, compat_score: Optional[int], threshold: int
) -> list[str]:
    return [
        f"Upgrade type: {upgrade_type}",
        f"Current Compatibility score: {str(compat_score)} {'%' if compat_score is isinstance(compat_score, int) else ''}",
        f"Minimal Compatibility score: {threshold}%",
    ]


def compute_decision(
    upgrade_type: str, compat_score: Optional[int], threshold: int
) -> bool:
    decision = (upgrade_type == "Patch") or (
        upgrade_type == "Minor"
        and isinstance(compat_score, int)
        and compat_score >= threshold
    )
    logging.debug(
        f"Decision compute: upgrade_type={upgrade_type}, compat_score={compat_score}, threshold={threshold} -> should_merge={decision}"
    )
    return decision


def connect_github(token: str, repo_full: str, pr_number: int) -> tuple:
    if not Github:
        raise ImportError("PyGithub is required. Install with: pip install PyGithub")
    gh = Github(auth=Auth.Token(token)) if Auth else Github(token)
    repo = gh.get_repo(repo_full)
    issue = repo.get_issue(number=pr_number)
    pr_obj = repo.get_pull(number=pr_number)
    logging.debug("Connected to GitHub and fetched issue/PR objects")
    return repo, issue, pr_obj


def disable_automerge(token: str, pr_obj) -> None:
    """Disable auto-merge on PR using GraphQL API."""
    node_id = pr_obj.node_id
    mutation = """
    mutation($pullRequestId: ID!) {
      disablePullRequestAutoMerge(input: {pullRequestId: $pullRequestId}) {
        clientMutationId
      }
    }
    """
    variables = {"pullRequestId": node_id}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    import requests
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": mutation, "variables": variables},
        headers=headers,
    )
    if response.status_code == 200:
        logging.info("Disabled auto-merge on PR")
    else:
        logging.warning(f"Failed to disable auto-merge: {response.text}")


def enable_automerge(token: str, pr_obj, merge_method: str = "SQUASH") -> None:
    """Enable auto-merge on PR using GraphQL API."""
    node_id = pr_obj.node_id
    mutation = """
    mutation($pullRequestId: ID!, $mergeMethod: PullRequestMergeMethod!) {
      enablePullRequestAutoMerge(input: {pullRequestId: $pullRequestId, mergeMethod: $mergeMethod}) {
        clientMutationId
      }
    }
    """
    variables = {"pullRequestId": node_id, "mergeMethod": merge_method.upper()}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    import requests
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": mutation, "variables": variables},
        headers=headers,
    )
    if response.status_code == 200:
        logging.info(f"Enabled auto-merge on PR with method {merge_method}")
    else:
        logging.warning(f"Failed to enable auto-merge: {response.text}")


def handle_skip_label(pr_obj, issue, reason_parts: list[str]) -> bool:
    skip_label = os.environ.get("NO_AUTO_MERGE_LABEL", "no-auto-merge").lower()
    label_names = [lbl.name for lbl in pr_obj.get_labels()]
    logging.debug(f"PR labels: {label_names}; skip_label={skip_label}")
    if skip_label in [name.lower() for name in label_names]:
        issue.create_comment(
            (
                f"## Dependabot Auto-merge: ⛔ **Skipping auto-merge** due to `{skip_label}` label\n\n"
                + "### 📋 Decision Details\n"
                + "\n".join(f"- {part}" for part in reason_parts)
            )
        )
        append_summary(
            f"## ⛔ Skipping Auto-merge\n\n"
            f"PR has the `{skip_label}` label.\n\n"
            f"### Decision Details\n" + "\n".join(f"- {part}" for part in reason_parts)
        )
        write_output("MERGE_ALLOWED", "false")
        with open("decision_outcome.txt", "w") as f:
            f.write("⛔ Auto-merge skipped - Label present")
        print("⛔ Auto-merge skipped - Label present")
        return True
    return False


def post_manual_review(issue, reason_parts: list[str]) -> None:
    marker = "<!-- dependabot-manual-review -->"
    existing = list(issue.get_comments())
    body = (
        marker
        + "\n"
        + "## Dependabot Auto-merge: 👀 **Manual review required**\n\n"
        + "This PR doesn't meet the auto-merge criteria.\n\n"
        + "### 📋 Decision Details\n"
        + "\n".join(f"- {part}" for part in reason_parts)
    )

    existing_comment = next((c for c in existing if marker in (c.body or "")), None)
    if existing_comment:
        if existing_comment.body != body:
            existing_comment.edit(body)
            logging.info("Updated manual review comment")
        else:
            logging.debug("Manual review comment already exists with same content, skipping")
    else:
        issue.create_comment(body)
        logging.info("Posted manual review comment")

    append_summary("Result: manual review requested (comment posted)")
    write_output("MERGE_ALLOWED", "false")
    with open("decision_outcome.txt", "w") as f:
        f.write("👀 Manual review required")
    print("👀 Manual review required")


def post_success_comment(
    issue,
    upgrade_type: str,
    compat_score: Optional[int],
    threshold: int,
    reason_parts: list[str],
) -> None:
    existing = list(issue.get_comments())
    marker = "<!-- dependabot-auto-merge-success -->"
    merge_method = os.environ.get("MERGE_METHOD", "squash")
    if upgrade_type == "Patch":
        rationale = "🩹 patch upgrade"
    elif upgrade_type == "Minor" and compat_score is not None:
        rationale = f"✨ minor upgrade with compatibility score **{compat_score}%** ≥ threshold **{threshold}%**"
    else:
        rationale = "✅ meets configured criteria"
    comment_body = (
        marker
        + "\n"
        + f"## Dependabot Auto-merge: 🚀 **Auto-merge enabled** — {rationale}\n\n"
        + "### 📋 Decision Details\n"
        + "\n".join(f"- {part}" for part in reason_parts)
        + "\n"
        + f"- **Merge method:** `{merge_method}`\n\n"
        + "⏳ Native auto-merge will proceed after required checks pass."
    )

    existing_comment = next((c for c in existing if marker in (c.body or "")), None)
    if existing_comment:
        if existing_comment.body != comment_body:
            existing_comment.edit(comment_body)
            logging.info("Updated success criteria comment")
        else:
            logging.debug("Success comment already exists with same content, skipping")
    else:
        issue.create_comment(comment_body)
        logging.info("Posted success criteria comment")


def local_automerge_note(issue) -> None:
    merge_method = os.environ.get("MERGE_METHOD", "squash")
    issue.create_comment(
        (
            "## Dependabot Auto-merge: 🧪 **Local run simulation**\n\n"
            + "Would enable auto-merge in production.\n\n"
            + "### ⚙️ Settings\n"
            + f"- **Merge method:** `{merge_method}`"
        )
    )
    logging.info("Posted local auto-merge settings comment")


def run_decision_flow(args: argparse.Namespace, token: str) -> int:
    repo_full, pr_number, title, body, author_login, inputs = resolve_pr_context(
        args, token
    )
    upgrade_type = get_upgrade_type(title)
    compat_score = get_compat_score(body)
    threshold = load_threshold(inputs)
    reason_parts = build_reasons(upgrade_type, compat_score, threshold)
    should_merge = compute_decision(upgrade_type, compat_score, threshold)
    logging.info(
        f"Parsed PR: upgrade_type={upgrade_type}, compat_score={compat_score}, threshold={threshold}, should_merge={should_merge}, author={author_login}"
    )

    _, issue, pr_obj = connect_github(token, repo_full, pr_number)

    try:
        disable_automerge(token, pr_obj)
    except Exception:
        logging.exception("Failed to disable auto-merge")
        try:
            import traceback
            error_details = traceback.format_exc()
            issue.create_comment(
                f"## Dependabot Auto-merge: ⚠️ **Warning** - Failed to disable auto-merge\n\n"
                f"This is usually not critical, but you may want to check the PR settings.\n\n"
                f"<details>\n<summary>📋 Error details</summary>\n\n"
                f"```\n{error_details}\n```\n</details>"
            )
        except Exception:
            pass

    if handle_skip_label(pr_obj, issue, reason_parts):
        logging.info("Skipping due to label")
        return 0

    is_dependabot = author_login.lower() == "dependabot[bot]"
    if should_merge and is_dependabot:
        merge_method = os.environ.get("MERGE_METHOD", "squash")

        # Build rationale string for summary
        if upgrade_type == "Patch":
            rationale = "🩹 patch upgrade"
        elif upgrade_type == "Minor" and compat_score is not None:
            rationale = f"✨ minor upgrade with compatibility score **{compat_score}%** ≥ threshold **{threshold}%**"
        else:
            rationale = "✅ meets configured criteria"

        try:
            enable_automerge(token, pr_obj, merge_method)
            write_output("MERGE_ALLOWED", "true")
            append_summary(
                f"## 🚀 Auto-merge Enabled\n\n"
                f"{rationale}\n\n"
                f"### Decision Details\n" + "\n".join(f"- {part}" for part in reason_parts) +
                f"\n- **Merge method:** `{merge_method}`\n\n"
                f"⏳ Native auto-merge will proceed after required checks pass."
            )
            with open("decision_outcome.txt", "w") as f:
                f.write("🚀 Auto-merge enabled")
            print("🚀 Auto-merge enabled")
        except Exception:
            logging.exception("Failed to enable auto-merge")
            write_output("MERGE_ALLOWED", "false")
            try:
                import traceback
                error_details = traceback.format_exc()
                issue.create_comment(
                    f"## Dependabot Auto-merge: ❌ **Error** - Failed to enable auto-merge\n\n"
                    f"The PR meets the criteria for auto-merge, but enabling it failed. "
                    f"You may need to enable it manually or merge the PR directly.\n\n"
                    f"<details>\n<summary>📋 Full error message</summary>\n\n"
                    f"```\n{error_details}\n```\n</details>"
                )
            except Exception:
                pass
            return 1
        try:
            post_success_comment(
                issue, upgrade_type, compat_score, threshold, reason_parts
            )
        except Exception:
            logging.exception("Failed posting success criteria comment")
            try:
                import traceback
                error_details = traceback.format_exc()
                issue.create_comment(
                    f"## Dependabot Auto-merge: ⚠️ **Warning** - Failed to post details comment\n\n"
                    f"Auto-merge is active and will proceed when checks pass.\n\n"
                    f"<details>\n<summary>📋 Error details</summary>\n\n"
                    f"```\n{error_details}\n```\n</details>"
                )
            except Exception:
                pass
        if args.enable_automerge:
            try:
                local_automerge_note(issue)
            except Exception:
                logging.exception("Failed to enable auto-merge in local mode")
                try:
                    import traceback
                    error_details = traceback.format_exc()
                    issue.create_comment(
                        f"## Dependabot Auto-merge: ⚠️ **Warning** - Local run simulation failed\n\n"
                        f"<details>\n<summary>📋 Error details</summary>\n\n"
                        f"```\n{error_details}\n```\n</details>"
                    )
                except Exception:
                    pass
        return 0

    post_manual_review(issue, reason_parts)
    return 0


def setup_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "DEBUG"),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def prepare_env(args: argparse.Namespace) -> Optional[str]:
    if args.compat_threshold is not None:
        os.environ["DEPENDABOT_COMPAT_THRESHOLD"] = str(args.compat_threshold)
    return os.environ.get("GITHUB_TOKEN")


def main(argv: list[str]) -> int:
    setup_logging()
    args = parse_args(argv)
    token = prepare_env(args)
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1
    try:
        return run_decision_flow(args, token)
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
