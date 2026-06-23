#!/usr/bin/env python3
"""Manage SQLite-backed tmp/shared_ctx handoff tasks."""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DB_NAME = "shared_ctx.sqlite"
STATUS_VALUES = ("pending", "progress", "done")
STATUS_LINES = {
    "pending": "[STATUS=PENDING]",
    "progress": "[STATUS=PROGRESS]",
    "done": "[STATUS=DONE]",
}
TASK_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,127}")


class SharedCtxError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_task_id(raw: str) -> str:
    task_id = Path(raw).name
    for suffix in (".md", ".pending.md", ".progress.md", ".done.md"):
        if task_id.endswith(suffix):
            task_id = task_id[: -len(suffix)]
            break
    if not TASK_RE.fullmatch(task_id):
        raise SharedCtxError(
            "Task id must use lowercase letters, digits, underscores, or hyphens."
        )
    return task_id


def nearest_existing_dir(path: Path) -> Path:
    if path.exists():
        return path if path.is_dir() else path.parent
    for parent in path.parents:
        if parent.exists():
            return parent if parent.is_dir() else parent.parent
    return path


def git_root(path: Path) -> Path | None:
    probe = nearest_existing_dir(path)
    try:
        result = subprocess.run(
            ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    if result.returncode == 0:
        output = result.stdout.strip()
        if output:
            return Path(output).resolve()
    return None


def git_text(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None
    return result.stdout.strip()


def parse_worktree_list(output: str) -> list[dict[str, str]]:
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in output.splitlines():
        if not line:
            if current:
                worktrees.append(current)
                current = {}
            continue

        key, separator, value = line.partition(" ")
        if key == "worktree":
            if current:
                worktrees.append(current)
            current = {"worktree": value}
        elif separator:
            current[key] = value
        else:
            current[key] = "1"

    if current:
        worktrees.append(current)
    return worktrees


def branch_name(worktree: dict[str, str]) -> str:
    branch = worktree.get("branch", "")
    prefix = "refs/heads/"
    if branch.startswith(prefix):
        return branch[len(prefix) :]
    if branch:
        return branch
    if "detached" in worktree:
        return "detached"
    return ""


def worktree_info(root: Path) -> dict[str, str | int]:
    output = git_text(root, "worktree", "list", "--porcelain")
    if output is None:
        return {
            "is_git_worktree": 0,
            "is_linked_worktree": 0,
            "worktree_name": "",
            "worktree_path": "",
            "main_worktree_path": "",
            "branch": "",
        }

    current_root = root.resolve()
    worktrees = parse_worktree_list(output)
    main_path = Path(worktrees[0]["worktree"]).resolve() if worktrees else current_root
    current = None
    for worktree in worktrees:
        path = Path(worktree["worktree"]).resolve()
        if path == current_root:
            current = worktree
            break

    if current is None:
        current = {"worktree": str(current_root)}

    current_path = Path(current["worktree"]).resolve()
    return {
        "is_git_worktree": 1,
        "is_linked_worktree": 1 if current_path != main_path else 0,
        "worktree_name": current_path.name,
        "worktree_path": str(current_path),
        "main_worktree_path": str(main_path),
        "branch": branch_name(current),
    }


def normalize_shared_ctx_root(path: Path) -> Path:
    for current in (path, *path.parents):
        if current.name == "shared_ctx" and current.parent.name == "tmp":
            return current.parent.parent
    return path


def project_root(raw: str) -> Path:
    raw_path = Path(raw).resolve()
    discovered = git_root(raw_path)
    if discovered is not None:
        return discovered
    return normalize_shared_ctx_root(raw_path)


def ctx_dir(root: Path) -> Path:
    return root / "tmp" / "shared_ctx"


def tasks_dir(root: Path) -> Path:
    return ctx_dir(root) / "tasks"


def db_path(root: Path) -> Path:
    return ctx_dir(root) / DB_NAME


@contextmanager
def immediate_transaction(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def connect(root: Path, *, create: bool) -> sqlite3.Connection:
    if create:
        tasks_dir(root).mkdir(parents=True, exist_ok=True)
    elif not db_path(root).exists():
        raise SharedCtxError(f"Shared context database does not exist: {db_path(root)}")

    conn = sqlite3.connect(db_path(root), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    if create:
        conn.execute("PRAGMA journal_mode = WAL")
        ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK (status IN ('pending', 'progress', 'done')),
            title TEXT NOT NULL,
            body_md TEXT NOT NULL DEFAULT '',
            created_by TEXT,
            target_owner TEXT,
            claimed_by TEXT,
            completed_by TEXT,
            created_at TEXT NOT NULL,
            claimed_at TEXT,
            done_at TEXT,
            updated_at TEXT NOT NULL,
            md_path TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status_created
            ON tasks(status, created_at);

        CREATE TABLE IF NOT EXISTS project_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            is_gitignore_checked INTEGER NOT NULL DEFAULT 0 CHECK (is_gitignore_checked IN (0, 1)),
            is_project_in_gitignore INTEGER NOT NULL DEFAULT 0 CHECK (is_project_in_gitignore IN (0, 1)),
            user_asked INTEGER NOT NULL DEFAULT 0 CHECK (user_asked IN (0, 1)),
            checked_at TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    now = utc_now()
    conn.execute(
        """
        INSERT OR IGNORE INTO project_state (id, updated_at)
        VALUES (1, ?)
        """,
        (now,),
    )


def get_task(conn: sqlite3.Connection, task_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise SharedCtxError(f"Task does not exist: {task_id}")
    return row


def get_project_state(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM project_state WHERE id = 1").fetchone()
    if row is None:
        raise SharedCtxError("Project state row is missing.")
    return row


def clean_body_md(body_md: str) -> str:
    lines = body_md.splitlines()
    if lines and re.fullmatch(r"\[STATUS=(PENDING|PROGRESS|DONE)\]", lines[0].strip()):
        return "\n".join(lines[1:]).lstrip("\n")
    return body_md


def render_task_markdown(row: sqlite3.Row) -> str:
    body = clean_body_md(row["body_md"])
    parts = [
        STATUS_LINES[row["status"]],
        "",
        f"# Task: {row['title']}",
        "",
        f"Task ID: `{row['id']}`",
        f"Status: `{row['status']}`",
        f"Created by: `{row['created_by'] or ''}`",
        f"Target owner: `{row['target_owner'] or ''}`",
        f"Claimed by: `{row['claimed_by'] or ''}`",
        f"Completed by: `{row['completed_by'] or ''}`",
        f"Created at: `{row['created_at']}`",
        f"Updated at: `{row['updated_at']}`",
        "",
        "Source of truth: `tmp/shared_ctx/shared_ctx.sqlite`.",
        "",
        "---",
        "",
        body.rstrip(),
        "",
    ]
    return "\n".join(parts)


def write_task_markdown(root: Path, row: sqlite3.Row) -> Path:
    path = root / row["md_path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(render_task_markdown(row), encoding="utf-8")
    os.replace(tmp, path)
    return path


def refresh_task_markdown(root: Path, conn: sqlite3.Connection, task_id: str) -> Path:
    row = get_task(conn, task_id)
    return write_task_markdown(root, row)


def body_from_args(args: argparse.Namespace) -> str:
    if getattr(args, "body_file", None):
        return Path(args.body_file).read_text(encoding="utf-8")
    return getattr(args, "body", None) or ""


def check_gitignore(root: Path) -> bool:
    target = "tmp/shared_ctx/shared_ctx.sqlite"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "--", target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
    except FileNotFoundError:
        pass

    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return False

    patterns = []
    for raw_line in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        patterns.append(line)

    accepted = {
        "tmp/",
        "/tmp/",
        "tmp/*",
        "/tmp/*",
        "tmp/**",
        "/tmp/**",
        "tmp/shared_ctx",
        "/tmp/shared_ctx",
        "tmp/shared_ctx/",
        "/tmp/shared_ctx/",
        "tmp/shared_ctx/*",
        "/tmp/shared_ctx/*",
        "tmp/shared_ctx/**",
        "/tmp/shared_ctx/**",
    }
    return any(pattern in accepted for pattern in patterns)


def update_gitignore_state(root: Path, conn: sqlite3.Connection) -> sqlite3.Row:
    ignored = 1 if check_gitignore(root) else 0
    now = utc_now()
    conn.execute(
        """
        UPDATE project_state
        SET is_gitignore_checked = 1,
            is_project_in_gitignore = ?,
            checked_at = ?,
            updated_at = ?
        WHERE id = 1
        """,
        (ignored, now, now),
    )
    return get_project_state(conn)


def print_state(row: sqlite3.Row) -> None:
    print(f"is_gitignore_checked={int(row['is_gitignore_checked'])}")
    print(f"is_project_in_gitignore={int(row['is_project_in_gitignore'])}")
    print(f"user_asked={int(row['user_asked'])}")
    print(f"checked_at={row['checked_at'] or ''}")


def print_worktree_info(info: dict[str, str | int]) -> None:
    print(f"is_git_worktree={info['is_git_worktree']}")
    print(f"is_linked_worktree={info['is_linked_worktree']}")
    print(f"worktree_name={info['worktree_name']}")
    print(f"worktree_path={info['worktree_path']}")
    print(f"main_worktree_path={info['main_worktree_path']}")
    print(f"branch={info['branch']}")


def cmd_init(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    conn = connect(root, create=True)
    state = update_gitignore_state(root, conn)
    print(f"database={db_path(root)}")
    print(f"tasks_dir={tasks_dir(root)}")
    print_state(state)
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    task_id = normalize_task_id(args.task)
    conn = connect(root, create=True)
    now = utc_now()
    md_path = f"tmp/shared_ctx/tasks/{task_id}.md"
    body_md = body_from_args(args)
    title = args.title or task_id.replace("_", " ").replace("-", " ")

    with immediate_transaction(conn):
        if conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone():
            raise SharedCtxError(f"Task already exists: {task_id}")
        conn.execute(
            """
            INSERT INTO tasks (
                id, status, title, body_md, created_by, target_owner,
                created_at, updated_at, md_path
            )
            VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                title,
                clean_body_md(body_md),
                args.created_by,
                args.target_owner,
                now,
                now,
                md_path,
            ),
        )

    path = refresh_task_markdown(root, conn, task_id)
    print(f"created={task_id}")
    print(f"status=pending")
    print(f"markdown={path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    if not db_path(root).exists():
        print(f"No shared context database: {db_path(root)}")
        return 0

    conn = connect(root, create=False)
    params: list[str] = []
    query = (
        "SELECT id, status, title, created_by, target_owner, claimed_by, updated_at, md_path "
        "FROM tasks"
    )
    if args.status:
        query += " WHERE status = ?"
        params.append(args.status)
    query += " ORDER BY created_at, id"

    rows = conn.execute(query, params).fetchall()
    if not rows:
        print("No matching shared context tasks.")
        return 0

    for row in rows:
        print(
            "\t".join(
                [
                    row["id"],
                    row["status"],
                    row["title"],
                    row["target_owner"] or "",
                    row["claimed_by"] or "",
                    row["updated_at"],
                    row["md_path"],
                ]
            )
        )
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    task_id = normalize_task_id(args.task)
    conn = connect(root, create=False)
    now = utc_now()

    with immediate_transaction(conn):
        row = get_task(conn, task_id)
        if row["status"] != "pending":
            raise SharedCtxError(f"Task is not pending: {task_id} status={row['status']}")
        conn.execute(
            """
            UPDATE tasks
            SET status = 'progress',
                claimed_by = ?,
                claimed_at = ?,
                updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (args.agent, now, now, task_id),
        )
        if conn.execute("SELECT changes()").fetchone()[0] != 1:
            raise SharedCtxError(f"Task was claimed by another agent: {task_id}")

    path = refresh_task_markdown(root, conn, task_id)
    row = get_task(conn, task_id)
    print(f"claimed={task_id}")
    print(f"status=progress")
    print(f"markdown={path}")
    if not args.no_body:
        print("")
        print(clean_body_md(row["body_md"]).rstrip())
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    task_id = normalize_task_id(args.task)
    conn = connect(root, create=False)
    now = utc_now()
    note = body_from_args(args).strip()

    with immediate_transaction(conn):
        row = get_task(conn, task_id)
        if row["status"] != "progress":
            raise SharedCtxError(f"Task is not in progress: {task_id} status={row['status']}")
        body_md = row["body_md"]
        if note:
            body_md = body_md.rstrip() + f"\n\n## Completion\n\n{note}\n"
        conn.execute(
            """
            UPDATE tasks
            SET status = 'done',
                completed_by = ?,
                done_at = ?,
                updated_at = ?,
                body_md = ?
            WHERE id = ? AND status = 'progress'
            """,
            (args.agent, now, now, body_md, task_id),
        )
        if conn.execute("SELECT changes()").fetchone()[0] != 1:
            raise SharedCtxError(f"Task was changed by another agent: {task_id}")

    path = refresh_task_markdown(root, conn, task_id)
    print(f"done={task_id}")
    print(f"status=done")
    print(f"markdown={path}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    task_id = normalize_task_id(args.task)
    conn = connect(root, create=False)
    row = get_task(conn, task_id)
    if args.body_only:
        print(clean_body_md(row["body_md"]).rstrip())
    else:
        print(render_task_markdown(row).rstrip())
    return 0


def cmd_export_md(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    task_id = normalize_task_id(args.task)
    conn = connect(root, create=False)
    path = refresh_task_markdown(root, conn, task_id)
    print(path)
    return 0


def cmd_gitignore_status(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    conn = connect(root, create=True)
    state = update_gitignore_state(root, conn)
    print_state(state)
    return 0


def gitignore_has_shared_ctx(root: Path) -> bool:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return False
    for raw_line in gitignore.read_text(encoding="utf-8").splitlines():
        if raw_line.strip() in {"tmp/shared_ctx/", "/tmp/shared_ctx/"}:
            return True
    return False


def cmd_add_gitignore(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    conn = connect(root, create=True)
    gitignore = root / ".gitignore"
    if not check_gitignore(root) and not gitignore_has_shared_ctx(root):
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        gitignore.write_text(existing + prefix + "tmp/shared_ctx/\n", encoding="utf-8")

    now = utc_now()
    conn.execute(
        """
        UPDATE project_state
        SET user_asked = 1,
            updated_at = ?
        WHERE id = 1
        """,
        (now,),
    )
    state = update_gitignore_state(root, conn)
    print(".gitignore covers tmp/shared_ctx/")
    print_state(state)
    return 0


def cmd_mark_user_asked(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    conn = connect(root, create=True)
    now = utc_now()
    conn.execute(
        """
        UPDATE project_state
        SET user_asked = 1,
            updated_at = ?
        WHERE id = 1
        """,
        (now,),
    )
    state = get_project_state(conn)
    print_state(state)
    return 0


def cmd_precommit_check(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    conn = connect(root, create=True)
    state = update_gitignore_state(root, conn)
    if int(state["is_project_in_gitignore"]) == 1:
        print("OK: tmp/shared_ctx/ is ignored.")
        return 0

    if int(state["user_asked"]) == 0:
        print("ASK_USER: tmp/shared_ctx/ is not ignored.")
        print("Ask whether to add `tmp/shared_ctx/` to .gitignore.")
        print(
            "If yes, run: python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py "
            "add-gitignore --root <project>"
        )
        print(
            "If no, run: python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py "
            "mark-user-asked --root <project>"
        )
        return 2

    print("WARN: tmp/shared_ctx/ is not ignored, but the user has already been asked.")
    return 0


def cmd_worktree_info(args: argparse.Namespace) -> int:
    root = project_root(args.root)
    print_worktree_info(worktree_info(root))
    return 0


def add_common_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="Project root. Default: .")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage project-local SQLite-backed tmp/shared_ctx handoff tasks."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create the database and check .gitignore.")
    add_common_root(init_parser)
    init_parser.set_defaults(func=cmd_init)

    create_parser = subparsers.add_parser("create", help="Create a pending task.")
    create_parser.add_argument("task", help="Task id.")
    create_parser.add_argument("--title", help="Human-readable title.")
    create_parser.add_argument("--body", help="Markdown body.")
    create_parser.add_argument("--body-file", help="Path to a Markdown body file.")
    create_parser.add_argument("--created-by", help="Writer agent/session name.")
    create_parser.add_argument("--target-owner", help="Expected reader agent/session name.")
    add_common_root(create_parser)
    create_parser.set_defaults(func=cmd_create)

    list_parser = subparsers.add_parser("list", help="List task metadata without body.")
    list_parser.add_argument("--status", choices=STATUS_VALUES, default="pending")
    add_common_root(list_parser)
    list_parser.set_defaults(func=cmd_list)

    claim_parser = subparsers.add_parser("claim", help="Atomically claim a pending task.")
    claim_parser.add_argument("task", help="Task id.")
    claim_parser.add_argument("--agent", required=True, help="Claiming agent/session name.")
    claim_parser.add_argument("--no-body", action="store_true", help="Do not print task body.")
    add_common_root(claim_parser)
    claim_parser.set_defaults(func=cmd_claim)

    done_parser = subparsers.add_parser("done", help="Mark a claimed task as done.")
    done_parser.add_argument("task", help="Task id.")
    done_parser.add_argument("--agent", required=True, help="Completing agent/session name.")
    done_parser.add_argument("--body", help="Completion note in Markdown.")
    done_parser.add_argument("--body-file", help="Path to a completion note file.")
    add_common_root(done_parser)
    done_parser.set_defaults(func=cmd_done)

    show_parser = subparsers.add_parser("show", help="Show a task body.")
    show_parser.add_argument("task", help="Task id.")
    show_parser.add_argument("--body-only", action="store_true")
    add_common_root(show_parser)
    show_parser.set_defaults(func=cmd_show)

    export_parser = subparsers.add_parser("export-md", help="Rewrite a task Markdown mirror.")
    export_parser.add_argument("task", help="Task id.")
    add_common_root(export_parser)
    export_parser.set_defaults(func=cmd_export_md)

    gitignore_parser = subparsers.add_parser(
        "gitignore-status", help="Check whether tmp/shared_ctx/ is ignored."
    )
    add_common_root(gitignore_parser)
    gitignore_parser.set_defaults(func=cmd_gitignore_status)

    add_gitignore_parser = subparsers.add_parser(
        "add-gitignore", help="Append tmp/shared_ctx/ to .gitignore."
    )
    add_common_root(add_gitignore_parser)
    add_gitignore_parser.set_defaults(func=cmd_add_gitignore)

    asked_parser = subparsers.add_parser(
        "mark-user-asked", help="Remember that the user was asked about .gitignore."
    )
    add_common_root(asked_parser)
    asked_parser.set_defaults(func=cmd_mark_user_asked)

    precommit_parser = subparsers.add_parser(
        "precommit-check", help="Warn before committing if shared_ctx is not ignored."
    )
    add_common_root(precommit_parser)
    precommit_parser.set_defaults(func=cmd_precommit_check)

    worktree_parser = subparsers.add_parser(
        "worktree-info", help="Print current git worktree identity."
    )
    add_common_root(worktree_parser)
    worktree_parser.set_defaults(func=cmd_worktree_info)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SharedCtxError as exc:
        print(f"shared_ctx: {exc}", file=sys.stderr)
        return 1
    except sqlite3.OperationalError as exc:
        print(f"shared_ctx sqlite: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
