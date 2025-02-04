import argparse
import configparser
import json
import os
import subprocess
from collections import defaultdict
from datetime import datetime

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
    period="day", author=None, since=None, until=None, path=None, max_commits=None
):
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
        print(f"Executing command: {' '.join(cmd)}")
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


def get_commit_details(commit_data):
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


def render_bars(commits, bar_char="▀", max_width=None):
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
        max_width = os.get_terminal_size().columns - 20
    bar_unit = max_width / max_commits

    for date in sorted(commits.keys(), reverse=True):
        count = commits[date]
        bar_width = int(count * bar_unit)
        bar = bar_char * bar_width
        count_str = str(count).rjust(4)
        print(
            f"{COLORS['date']}{date}{COLORS['reset']}  {COLORS['number']}{count_str}{COLORS['reset']}  {COLORS['bar']}{bar}{COLORS['reset']}"
        )


def render_activity_chart(data, title, max_width=40, bar_char="█"):
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


def print_repository_insights(commit_data):
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


def main():
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
        "-h", "--help", action="store_true", help="Show this help message"
    )

    args = parser.parse_args()

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
        print("Date,Hash,Author,Message")
        for commit in commit_data:
            print(
                f"{commit['date'].isoformat()},{commit['hash']},{commit['author']},{commit['message']}"
            )
    else:
        render_bars(grouped_commits)
        if args.insights:
            print_repository_insights(commit_data)


if __name__ == "__main__":
    main()
