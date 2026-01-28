import argparse
import configparser
import csv
import io
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Read color settings from config file or environment variables
CONFIG_FILE = os.path.expanduser("~/.gitbarsrc")
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

COLORS = {
    "reset": config.get("colors", "reset", fallback="\033[0m"),
    "title": config.get("colors", "title", fallback="\033[1;36m"),
    "date": config.get("colors", "date", fallback="\033[0;32m"),
    "number": config.get("colors", "number", fallback="\033[0;33m"),
    "bar": config.get("colors", "bar", fallback="\033[0;34m"),
    "alert": config.get("colors", "alert", fallback="\033[0;31m"),
}


def get_git_logs(
    period: str = "day",
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    path: Optional[str] = None,
    max_commits: Optional[int] = None,
) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """Get git logs and group them by the specified period."""
    cmd = ["git", "log", "--format=%aI|%h|%an|%s"]
    if author:
        cmd.extend(["--author", author])
    if since:
        cmd.extend(["--since", since])
    if until:
        cmd.extend(["--until", until])
    if path:
        cmd.append(path)

    try:
        # First check if we're in a git repository
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        print(f"{COLORS['alert']}Error: Not a git repository{COLORS['reset']}")
        return {}, []

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        commits = result.stdout.strip().split("\n")
        if not commits[0]:
            print(
                f"{COLORS['alert']}No commits found for the specified period{COLORS['reset']}"
            )
            return {}, []

        commit_data = []
        for commit in commits:
            if not commit:
                continue
            try:
                date_str, hash, author, message = commit.split("|", 3)
                date = datetime.fromisoformat(date_str.strip())
                commit_data.append(
                    {
                        "hash": hash,
                        "date": date,
                        "author": author,
                        "message": message,
                    }
                )
            except (ValueError, IndexError) as e:
                print(
                    f"{COLORS['alert']}Warning: Skipping malformed commit entry{COLORS['reset']}"
                )
                continue

        if max_commits:
            commit_data = commit_data[:max_commits]

        grouped_commits = defaultdict(int)
        for commit in commit_data:
            date = commit["date"]
            if period == "day":
                key = date.strftime("%Y-%m-%d")
            elif period == "month":
                key = date.strftime("%Y-%m")
            elif period == "year":
                key = date.strftime("%Y")
            grouped_commits[key] += 1

        return dict(grouped_commits), commit_data

    except subprocess.CalledProcessError as e:
        print(f"{COLORS['alert']}Error executing git command{COLORS['reset']}")
        print(f"Error details: {e.stderr}")
        return {}, []
    except Exception as e:
        print(f"{COLORS['alert']}Unexpected error: {str(e)}{COLORS['reset']}")
        return {}, []


def get_commit_details(commit_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get repository statistics including commit patterns."""
    authors = defaultdict(int)
    hours = defaultdict(int)
    weekdays = defaultdict(int)
    commit_types = defaultdict(int)

    for commit in commit_data:
        authors[commit["author"]] += 1
        hours[commit["date"].hour] += 1
        weekdays[commit["date"].weekday()] += 1

        # Categorize commit types based on common prefixes
        message = commit["message"].lower()
        if message.startswith(("fix", "bug")):
            commit_types["fixes"] += 1
        elif message.startswith(("feat", "add")):
            commit_types["features"] += 1
        elif message.startswith(("doc", "readme")):
            commit_types["documentation"] += 1
        elif message.startswith(("refactor", "style", "clean")):
            commit_types["refactoring"] += 1
        elif message.startswith("test"):
            commit_types["tests"] += 1
        else:
            commit_types["other"] += 1

    # Find peak activity times
    peak_hour = max(hours.items(), key=lambda x: x[1])
    peak_weekday = max(weekdays.items(), key=lambda x: x[1])
    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    return {
        "first_commit": min(c["date"] for c in commit_data),
        "last_commit": max(c["date"] for c in commit_data),
        "total_commits": len(commit_data),
        "peak_hour": peak_hour,
        "peak_weekday": (weekday_names[peak_weekday[0]], peak_weekday[1]),
        "authors": dict(sorted(authors.items(), key=lambda x: x[1], reverse=True)),
        "commit_types": commit_types,
        "hours": dict(sorted(hours.items())),
        "weekdays": {weekday_names[k]: v for k, v in sorted(weekdays.items())},
    }


def calculate_streaks(commit_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate current and longest commit streaks (consecutive days with commits)."""
    if not commit_data:
        return {"current_streak": 0, "longest_streak": 0, "longest_streak_start": None, "longest_streak_end": None}

    commit_dates = sorted({c["date"].date() for c in commit_data})

    longest_streak = 1
    longest_start = commit_dates[0]
    longest_end = commit_dates[0]
    current_run = 1
    current_start = commit_dates[0]

    for i in range(1, len(commit_dates)):
        if commit_dates[i] - commit_dates[i - 1] == timedelta(days=1):
            current_run += 1
        else:
            if current_run > longest_streak:
                longest_streak = current_run
                longest_start = current_start
                longest_end = commit_dates[i - 1]
            current_run = 1
            current_start = commit_dates[i]

    if current_run > longest_streak:
        longest_streak = current_run
        longest_start = current_start
        longest_end = commit_dates[-1]

    # Current streak: count backwards from today (or most recent commit date)
    today = datetime.now().date()
    current_streak = 0
    check_date = today
    date_set = set(commit_dates)

    while check_date in date_set:
        current_streak += 1
        check_date -= timedelta(days=1)

    # If today has no commits, check if yesterday started a streak
    if current_streak == 0:
        check_date = today - timedelta(days=1)
        while check_date in date_set:
            current_streak += 1
            check_date -= timedelta(days=1)

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "longest_streak_start": longest_start,
        "longest_streak_end": longest_end,
    }


def get_file_churn(
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    path: Optional[str] = None,
    top_n: int = 15,
) -> List[Tuple[str, int]]:
    """Get the most frequently changed files in the repository."""
    cmd = ["git", "log", "--name-only", "--format="]
    if author:
        cmd.extend(["--author", author])
    if since:
        cmd.extend(["--since", since])
    if until:
        cmd.extend(["--until", until])
    if path:
        cmd.append(path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        file_counts: Dict[str, int] = defaultdict(int)
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                file_counts[line] += 1

        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:top_n]
    except subprocess.CalledProcessError:
        return []


def get_velocity(
    period: str = "day",
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    path: Optional[str] = None,
) -> Dict[str, Dict[str, int]]:
    """Get lines added/removed per period using git numstat."""
    cmd = ["git", "log", "--numstat", "--format=%aI"]
    if author:
        cmd.extend(["--author", author])
    if since:
        cmd.extend(["--since", since])
    if until:
        cmd.extend(["--until", until])
    if path:
        cmd.append(path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        velocity: Dict[str, Dict[str, int]] = defaultdict(lambda: {"added": 0, "removed": 0})
        current_date_key = None

        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Date lines start with a year (ISO format)
            if line and len(line) > 10 and line[4] == "-":
                try:
                    date = datetime.fromisoformat(line)
                    if period == "day":
                        current_date_key = date.strftime("%Y-%m-%d")
                    elif period == "month":
                        current_date_key = date.strftime("%Y-%m")
                    elif period == "year":
                        current_date_key = date.strftime("%Y")
                except ValueError:
                    pass
            elif current_date_key and "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 3:
                    try:
                        added = int(parts[0]) if parts[0] != "-" else 0
                        removed = int(parts[1]) if parts[1] != "-" else 0
                        velocity[current_date_key]["added"] += added
                        velocity[current_date_key]["removed"] += removed
                    except ValueError:
                        continue

        return dict(velocity)
    except subprocess.CalledProcessError:
        return {}


def render_velocity(velocity: Dict[str, Dict[str, int]]) -> None:
    """Render a velocity chart showing lines added/removed per period."""
    if not velocity:
        print(f"{COLORS['alert']}No velocity data found{COLORS['reset']}")
        return

    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80
    max_width = min(terminal_width - 40, 60)
    all_values = []
    for v in velocity.values():
        all_values.extend([v["added"], v["removed"]])
    max_val = max(all_values) if all_values else 1

    total_added = sum(v["added"] for v in velocity.values())
    total_removed = sum(v["removed"] for v in velocity.values())
    net = total_added - total_removed

    print(f"\n{COLORS['title']}Code Velocity (lines changed){COLORS['reset']}")
    print(
        f"Total: {COLORS['number']}+{total_added}{COLORS['reset']} / "
        f"{COLORS['alert']}-{total_removed}{COLORS['reset']} / "
        f"net {COLORS['number']}{'+' if net >= 0 else ''}{net}{COLORS['reset']}"
    )
    print()

    for date_key in sorted(velocity.keys(), reverse=True):
        v = velocity[date_key]
        added_width = int((v["added"] / max_val) * max_width) if max_val else 0
        removed_width = int((v["removed"] / max_val) * max_width) if max_val else 0
        added_bar = "+" * added_width
        removed_bar = "-" * removed_width
        print(
            f"{COLORS['date']}{date_key}{COLORS['reset']}  "
            f"\033[0;32m{added_bar}{COLORS['reset']}"
            f"{COLORS['alert']}{removed_bar}{COLORS['reset']}  "
            f"{COLORS['number']}+{v['added']}{COLORS['reset']}/"
            f"{COLORS['alert']}-{v['removed']}{COLORS['reset']}"
        )


def render_file_churn(churn_data: List[Tuple[str, int]]) -> None:
    """Render a chart of most frequently changed files."""
    if not churn_data:
        print(f"{COLORS['alert']}No file change data found{COLORS['reset']}")
        return

    max_changes = churn_data[0][1]
    max_width = 30

    print(f"\n{COLORS['title']}Most Frequently Changed Files (hotspots){COLORS['reset']}")
    for filepath, count in churn_data:
        bar_width = int((count / max_changes) * max_width)
        bar = "█" * bar_width
        # Truncate long paths from the left
        display_path = filepath
        if len(display_path) > 45:
            display_path = "..." + filepath[-42:]
        print(
            f"{COLORS['date']}{display_path.ljust(48)}{COLORS['reset']} "
            f"{COLORS['number']}{str(count).rjust(4)}{COLORS['reset']} "
            f"{COLORS['bar']}{bar}{COLORS['reset']}"
        )


def render_bars(
    commits: Dict[str, int], bar_char: str = "▀", max_width: Optional[int] = None
) -> None:
    """Render ASCII bars for commit counts."""
    if not commits:
        print(f"{COLORS['alert']}No commits found{COLORS['reset']}")
        return

    total_commits = sum(commits.values())
    unique_days = len(commits)

    print(
        f"\n{COLORS['title']}Activity Summary ({total_commits} commits over {unique_days} days){COLORS['reset']}"
    )

    max_commits = max(commits.values())
    if not max_width:
        try:
            max_width = os.get_terminal_size().columns - 20
        except OSError:
            max_width = 60
    bar_unit = max_width / max_commits

    for date in sorted(commits.keys(), reverse=True):
        count = commits[date]
        bar_width = int(count * bar_unit)
        bar = bar_char * bar_width
        count_str = str(count).rjust(4)
        print(
            f"{COLORS['date']}{date}{COLORS['reset']}  {COLORS['number']}{count_str}{COLORS['reset']}  {COLORS['bar']}{bar}{COLORS['reset']}"
        )


def render_activity_chart(
    data: Dict[Any, int], title: str, max_width: int = 40, bar_char: str = "█"
) -> None:
    """Render a horizontal bar chart for activity data."""
    if not data:
        return

    print(f"\n{COLORS['title']}{title}:{COLORS['reset']}")
    max_value = max(data.values())
    max_label_length = max(len(str(k)) for k in data.keys())

    for key, value in data.items():
        bar_width = int((value / max_value) * max_width)
        bar = bar_char * bar_width
        label = str(key).ljust(max_label_length)
        print(
            f"{label} {COLORS['number']}{str(value).rjust(4)}{COLORS['reset']} {COLORS['bar']}{bar}{COLORS['reset']}"
        )


def print_repository_insights(commit_data: List[Dict[str, Any]]) -> None:
    """Print detailed repository insights."""
    try:
        stats = get_commit_details(commit_data)
        project_age = (stats["last_commit"] - stats["first_commit"]).days
        commits_per_day = stats["total_commits"] / max(project_age, 1)

        print(f"\n{COLORS['title']}=== Repository Insights ==={COLORS['reset']}")

        # Project Timeline
        print(f"\n{COLORS['title']}Timeline:{COLORS['reset']}")
        print(
            f"First commit: {COLORS['date']}{stats['first_commit'].strftime('%Y-%m-%d')}{COLORS['reset']}"
        )
        print(
            f"Latest commit: {COLORS['date']}{stats['last_commit'].strftime('%Y-%m-%d')}{COLORS['reset']}"
        )
        print(f"Project age: {COLORS['number']}{project_age} days{COLORS['reset']}")
        print(
            f"Average commits per day: {COLORS['number']}{commits_per_day:.1f}{COLORS['reset']}"
        )

        # Commit Streaks
        streaks = calculate_streaks(commit_data)
        print(f"\n{COLORS['title']}Streaks:{COLORS['reset']}")
        print(
            f"Current streak: {COLORS['number']}{streaks['current_streak']} days{COLORS['reset']}"
        )
        print(
            f"Longest streak: {COLORS['number']}{streaks['longest_streak']} days{COLORS['reset']}"
            + (
                f" ({COLORS['date']}{streaks['longest_streak_start']} → {streaks['longest_streak_end']}{COLORS['reset']})"
                if streaks["longest_streak_start"]
                else ""
            )
        )

        # Activity Patterns
        print(f"\n{COLORS['title']}Activity Patterns:{COLORS['reset']}")
        print(
            f"Most active hour: {COLORS['number']}{stats['peak_hour'][0]:02d}:00{COLORS['reset']} ({stats['peak_hour'][1]} commits)"
        )
        print(
            f"Most active day: {COLORS['number']}{stats['peak_weekday'][0]}{COLORS['reset']} ({stats['peak_weekday'][1]} commits)"
        )

        # Detailed Activity Charts
        render_activity_chart(stats["weekdays"], "Commits by Day of Week")
        render_activity_chart(
            {f"{hour:02d}:00": count for hour, count in stats["hours"].items()},
            "Commits by Hour",
        )

        # Commit Types Distribution
        print(f"\n{COLORS['title']}Commit Types:{COLORS['reset']}")
        for type_name, count in stats["commit_types"].items():
            percentage = (count / stats["total_commits"]) * 100
            bar = "█" * int(percentage / 2)
            print(
                f"{type_name.capitalize().ljust(15)} {COLORS['number']}{count:4d}{COLORS['reset']} {COLORS['bar']}{bar}{COLORS['reset']} ({percentage:.1f}%)"
            )

        # Top Contributors
        if len(stats["authors"]) > 1:
            print(f"\n{COLORS['title']}Top Contributors:{COLORS['reset']}")
            for i, (author, commits) in enumerate(
                list(stats["authors"].items())[:5], 1
            ):
                print(
                    f"{i}. {author}: {COLORS['number']}{commits}{COLORS['reset']} commits"
                )

    except subprocess.CalledProcessError:
        print(
            f"{COLORS['alert']}Error: Could not fetch repository statistics{COLORS['reset']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enhanced Git commit activity visualization", add_help=False
    )
    parser.add_argument(
        "-p",
        "--period",
        choices=["day", "month", "year"],
        default="day",
        help="Group commits by period",
    )
    parser.add_argument("-a", "--author", help="Filter commits by author")
    parser.add_argument(
        "-s", "--since", help="Show commits more recent than a specific date"
    )
    parser.add_argument("-u", "--until", help="Show commits older than a specific date")
    parser.add_argument(
        "-d", "--directory", help="Analyze commits in a specific directory"
    )
    parser.add_argument(
        "-m", "--max-commits", type=int, help="Limit the number of commits to display"
    )
    parser.add_argument(
        "-o",
        "--output",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "-i",
        "--insights",
        action="store_true",
        help="Show detailed repository insights",
    )
    parser.add_argument(
        "-c",
        "--churn",
        action="store_true",
        help="Show most frequently changed files (hotspots)",
    )
    parser.add_argument(
        "-v",
        "--velocity",
        action="store_true",
        help="Show code velocity (lines added/removed per period)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="Show version number",
    )
    parser.add_argument(
        "-h", "--help", action="store_true", help="Show this help message"
    )

    args = parser.parse_args()

    if args.version:
        from git_count import __version__
        print(f"git-count {__version__}")
        return

    if args.help:
        parser.print_help()
        return

    grouped_commits, commit_data = get_git_logs(
        period=args.period,
        author=args.author,
        since=args.since,
        until=args.until,
        path=args.directory,
        max_commits=args.max_commits,
    )

    if not commit_data:
        print(
            f"{COLORS['alert']}No commits found matching the specified criteria{COLORS['reset']}"
        )
        return

    if args.output == "json":
        output = {
            "grouped_commits": grouped_commits,
            "commit_data": [
                {
                    "hash": c["hash"],
                    "date": c["date"].isoformat(),
                    "author": c["author"],
                    "message": c["message"],
                }
                for c in commit_data
            ],
        }
        print(json.dumps(output, indent=2))
    elif args.output == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["Date", "Hash", "Author", "Message"])
        for commit in commit_data:
            writer.writerow([
                commit["date"].isoformat(),
                commit["hash"],
                commit["author"],
                commit["message"],
            ])
    else:
        render_bars(grouped_commits)
        if args.insights:
            print_repository_insights(commit_data)
        if args.churn:
            churn_data = get_file_churn(
                author=args.author,
                since=args.since,
                until=args.until,
                path=args.directory,
            )
            render_file_churn(churn_data)
        if args.velocity:
            velocity_data = get_velocity(
                period=args.period,
                author=args.author,
                since=args.since,
                until=args.until,
                path=args.directory,
            )
            render_velocity(velocity_data)


if __name__ == "__main__":
    main()
