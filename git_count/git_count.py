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

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

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

# Emoji mappings for emoji mode
EMOJIS = {
    "fire": "🔥",
    "rocket": "🚀",
    "star": "⭐",
    "chart_up": "📈",
    "chart_down": "📉",
    "trophy": "🏆",
    "calendar": "📅",
    "warning": "⚠️",
    "check": "✅",
    "sparkles": "✨",
    "tada": "🎉",
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


def render_velocity(velocity: Dict[str, Dict[str, int]], use_emoji: bool = False) -> None:
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

    title_prefix = f"{EMOJIS['rocket']} " if use_emoji else ""
    trend = EMOJIS['chart_up'] if net >= 0 else EMOJIS['chart_down']
    trend_emoji = f" {trend}" if use_emoji else ""

    print(f"\n{COLORS['title']}{title_prefix}Code Velocity (lines changed){COLORS['reset']}")
    print(
        f"Total: {COLORS['number']}+{total_added}{COLORS['reset']} / "
        f"{COLORS['alert']}-{total_removed}{COLORS['reset']} / "
        f"net {COLORS['number']}{'+' if net >= 0 else ''}{net}{COLORS['reset']}{trend_emoji}"
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


def render_file_churn(churn_data: List[Tuple[str, int]], use_emoji: bool = False) -> None:
    """Render a chart of most frequently changed files."""
    if not churn_data:
        print(f"{COLORS['alert']}No file change data found{COLORS['reset']}")
        return

    max_changes = churn_data[0][1]
    max_width = 30

    title_prefix = f"{EMOJIS['fire']} " if use_emoji else ""
    print(f"\n{COLORS['title']}{title_prefix}Most Frequently Changed Files (hotspots){COLORS['reset']}")
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
    commits: Dict[str, int], bar_char: str = "▀", max_width: Optional[int] = None, use_emoji: bool = False
) -> None:
    """Render ASCII bars for commit counts."""
    if not commits:
        print(f"{COLORS['alert']}No commits found{COLORS['reset']}")
        return

    total_commits = sum(commits.values())
    unique_days = len(commits)

    title_prefix = f"{EMOJIS['chart_up']} " if use_emoji else ""
    print(
        f"\n{COLORS['title']}{title_prefix}Activity Summary ({total_commits} commits over {unique_days} days){COLORS['reset']}"
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
    data: Dict[Any, int], title: str, max_width: int = 40, bar_char: str = "█", use_emoji: bool = False
) -> None:
    """Render a horizontal bar chart for activity data."""
    if not data:
        return

    title_prefix = f"{EMOJIS['chart_up']} " if use_emoji else ""
    print(f"\n{COLORS['title']}{title_prefix}{title}:{COLORS['reset']}")
    max_value = max(data.values())
    max_label_length = max(len(str(k)) for k in data.keys())

    for key, value in data.items():
        bar_width = int((value / max_value) * max_width)
        bar = bar_char * bar_width
        label = str(key).ljust(max_label_length)
        print(
            f"{label} {COLORS['number']}{str(value).rjust(4)}{COLORS['reset']} {COLORS['bar']}{bar}{COLORS['reset']}"
        )


def render_sparkline(values: List[int]) -> str:
    """Render a sparkline using unicode block characters."""
    if not values:
        return ""

    spark_chars = "▁▂▃▄▅▆▇█"
    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:
        return spark_chars[0] * len(values)

    sparkline = ""
    for val in values:
        normalized = (val - min_val) / (max_val - min_val)
        index = min(int(normalized * (len(spark_chars) - 1)), len(spark_chars) - 1)
        sparkline += spark_chars[index]

    return sparkline


def render_boxplot(values: List[int], title: str = "Distribution", use_emoji: bool = False) -> None:
    """Render a box plot showing statistical distribution."""
    if not values:
        print(f"{COLORS['alert']}No data for box plot{COLORS['reset']}")
        return

    sorted_values = sorted(values)
    n = len(sorted_values)

    # Calculate quartiles
    q1_idx = n // 4
    q2_idx = n // 2
    q3_idx = (3 * n) // 4

    min_val = sorted_values[0]
    q1 = sorted_values[q1_idx]
    median = sorted_values[q2_idx]
    q3 = sorted_values[q3_idx]
    max_val = sorted_values[-1]

    # Calculate IQR and outliers
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers = [v for v in sorted_values if v < lower_fence or v > upper_fence]

    title_prefix = f"{EMOJIS['chart_up']} " if use_emoji else ""
    print(f"\n{COLORS['title']}{title_prefix}{title}:{COLORS['reset']}")
    print(f"Min: {COLORS['number']}{min_val}{COLORS['reset']}, "
          f"Q1: {COLORS['number']}{q1}{COLORS['reset']}, "
          f"Median: {COLORS['number']}{median}{COLORS['reset']}, "
          f"Q3: {COLORS['number']}{q3}{COLORS['reset']}, "
          f"Max: {COLORS['number']}{max_val}{COLORS['reset']}")

    if outliers:
        outlier_marker = f" {EMOJIS['warning']}" if use_emoji else " •"
        print(f"Outliers: {COLORS['alert']}{len(outliers)}{outlier_marker}{COLORS['reset']}")

    # Visual representation
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80

    chart_width = min(terminal_width - 20, 60)
    value_range = max_val - min_val if max_val > min_val else 1

    def scale(val):
        return int(((val - min_val) / value_range) * chart_width)

    min_pos = 0
    q1_pos = scale(q1)
    med_pos = scale(median)
    q3_pos = scale(q3)
    max_pos = scale(max_val)

    # Draw the box plot
    line = [" "] * (chart_width + 1)

    # Whiskers
    for i in range(min_pos, q1_pos):
        line[i] = "─"
    for i in range(q3_pos + 1, max_pos + 1):
        line[i] = "─"

    # Box
    for i in range(q1_pos, q3_pos + 1):
        line[i] = "█"

    # Median line
    line[med_pos] = "│"

    # Markers
    line[min_pos] = "├"
    line[max_pos] = "┤"

    print(f"  {COLORS['bar']}{''.join(line)}{COLORS['reset']}")


def render_violinplot(data: Dict[str, int], title: str = "Distribution", use_emoji: bool = False) -> None:
    """Render a violin plot showing density distribution."""
    if not data:
        print(f"{COLORS['alert']}No data for violin plot{COLORS['reset']}")
        return

    title_prefix = f"{EMOJIS['chart_up']} " if use_emoji else ""
    print(f"\n{COLORS['title']}{title_prefix}{title}:{COLORS['reset']}")

    max_value = max(data.values())
    max_width = 20
    density_chars = " ░▒▓█"

    for key, value in data.items():
        width = int((value / max_value) * max_width)
        # Create symmetric violin shape
        left_width = width // 2
        right_width = width - left_width

        # Use density characters based on value
        density_index = min(int((value / max_value) * (len(density_chars) - 1)), len(density_chars) - 1)
        char = density_chars[density_index]

        left_side = char * left_width
        right_side = char * right_width

        label = str(key).rjust(12)
        print(
            f"{label} │{left_side.rjust(max_width // 2)}{right_side.ljust(max_width // 2)}│ "
            f"{COLORS['number']}{value}{COLORS['reset']}"
        )


def render_contribution_heatmap(commit_data: List[Dict[str, Any]], use_emoji: bool = False) -> None:
    """Render a GitHub-style contribution heatmap."""
    if not commit_data:
        print(f"{COLORS['alert']}No commit data for heatmap{COLORS['reset']}")
        return

    # Get last 365 days
    today = datetime.now().date()
    start_date = today - timedelta(days=364)

    # Count commits per day
    daily_commits: Dict[str, int] = defaultdict(int)
    for commit in commit_data:
        commit_date = commit["date"].date()
        if start_date <= commit_date <= today:
            daily_commits[commit_date.isoformat()] = daily_commits.get(commit_date.isoformat(), 0) + 1

    # Create intensity map
    intensity_chars = ["·", "░", "▒", "▓", "█"]

    def get_intensity(count: int) -> str:
        if count == 0:
            return intensity_chars[0]
        elif count <= 3:
            return intensity_chars[1]
        elif count <= 7:
            return intensity_chars[2]
        elif count <= 15:
            return intensity_chars[3]
        else:
            return intensity_chars[4]

    def get_color(count: int) -> str:
        if count == 0:
            return "\033[0;37m"  # Gray
        elif count <= 3:
            return "\033[0;32m"  # Green
        elif count <= 7:
            return "\033[0;33m"  # Yellow
        elif count <= 15:
            return "\033[0;31m"  # Red
        else:
            return "\033[1;31m"  # Bright red

    title_prefix = f"{EMOJIS['calendar']} " if use_emoji else ""
    print(f"\n{COLORS['title']}{title_prefix}Contribution Heatmap (Last 365 Days){COLORS['reset']}")

    # Calculate weeks
    weeks = []
    current_date = start_date
    week = [None] * 7
    day_of_week = current_date.weekday()

    while current_date <= today:
        week[day_of_week] = current_date

        if day_of_week == 6:  # Sunday
            weeks.append(week)
            week = [None] * 7

        current_date += timedelta(days=1)
        day_of_week = (day_of_week + 1) % 7

    if any(week):
        weeks.append(week)

    # Month labels
    month_labels = ["   "]
    current_month = None
    for week in weeks:
        week_month = None
        for day in week:
            if day:
                week_month = day.strftime("%b")
                break
        if week_month and week_month != current_month:
            month_labels.append(week_month.ljust(2))
            current_month = week_month
        else:
            month_labels.append("  ")

    print("".join(month_labels[:min(len(month_labels), 53)]))

    # Render heatmap
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day_idx in range(7):
        row = [weekday_labels[day_idx]]
        for week in weeks[:52]:  # Limit to 52 weeks
            if week[day_idx]:
                date_str = week[day_idx].isoformat()
                count = daily_commits.get(date_str, 0)
                char = get_intensity(count)
                color = get_color(count)
                row.append(f"{color}{char}{COLORS['reset']}")
            else:
                row.append(" ")
        print(" ".join(row))

    # Legend
    legend = f"\n{intensity_chars[0]} 0   {intensity_chars[1]} 1-3   {intensity_chars[2]} 4-7   {intensity_chars[3]} 8-15   {intensity_chars[4]} 16+"
    print(legend)


def send_notification(title: str, message: str) -> None:
    """Send a desktop notification if plyer is available."""
    if not HAS_PLYER:
        return

    try:
        notification.notify(
            title=title,
            message=message,
            app_name="git-count",
            timeout=5,
        )
    except Exception:
        # Silently fail if notifications aren't supported
        pass


def generate_svg_chart(commits: Dict[str, int], chart_type: str = "commits", title: str = "Git Activity") -> str:
    """Generate SVG chart for commit data."""
    if not commits:
        return ""

    # SVG dimensions
    width = 800
    height = 400
    margin = 50
    chart_width = width - 2 * margin
    chart_height = height - 2 * margin

    # Calculate scales
    max_commits = max(commits.values())
    sorted_dates = sorted(commits.keys())
    num_bars = len(sorted_dates)
    bar_width = chart_width / num_bars if num_bars > 0 else 1

    # Start SVG
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<style>',
        '  .bar { fill: #4CAF50; }',
        '  .bar:hover { fill: #45a049; }',
        '  .axis { stroke: #333; stroke-width: 2; }',
        '  .label { font-family: Arial, sans-serif; font-size: 12px; fill: #333; }',
        '  .title { font-family: Arial, sans-serif; font-size: 18px; font-weight: bold; fill: #333; }',
        '</style>',
        f'<text x="{width/2}" y="25" text-anchor="middle" class="title">{title}</text>',
        # Y-axis
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" class="axis"/>',
        # X-axis
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" class="axis"/>',
    ]

    # Draw bars
    for i, date in enumerate(sorted_dates):
        count = commits[date]
        bar_height = (count / max_commits) * chart_height if max_commits > 0 else 0
        x = margin + i * bar_width
        y = height - margin - bar_height

        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{max(bar_width - 2, 1)}" height="{bar_height}" class="bar">'
            f'<title>{date}: {count} commits</title></rect>'
        )

    # Add some x-axis labels (every nth date to avoid crowding)
    label_interval = max(num_bars // 10, 1)
    for i, date in enumerate(sorted_dates):
        if i % label_interval == 0:
            x = margin + i * bar_width
            # Rotate label for better fit
            svg_parts.append(
                f'<text x="{x}" y="{height-margin+15}" class="label" transform="rotate(45 {x} {height-margin+15})">{date}</text>'
            )

    # Y-axis labels
    for i in range(5):
        y = height - margin - (i * chart_height / 4)
        value = int((i * max_commits / 4))
        svg_parts.append(
            f'<text x="{margin-10}" y="{y}" text-anchor="end" class="label">{value}</text>'
        )

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def print_repository_insights(commit_data: List[Dict[str, Any]], use_emoji: bool = False, show_sparkline: bool = False, show_boxplot: bool = False, show_violinplot: bool = False) -> None:
    """Print detailed repository insights."""
    try:
        stats = get_commit_details(commit_data)
        project_age = (stats["last_commit"] - stats["first_commit"]).days
        commits_per_day = stats["total_commits"] / max(project_age, 1)

        header_emoji = f"{EMOJIS['sparkles']} " if use_emoji else ""
        print(f"\n{COLORS['title']}{header_emoji}=== Repository Insights ==={COLORS['reset']}")

        # Project Timeline
        timeline_emoji = f"{EMOJIS['calendar']} " if use_emoji else ""
        print(f"\n{COLORS['title']}{timeline_emoji}Timeline:{COLORS['reset']}")
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
        streak_emoji = f"{EMOJIS['fire']} " if use_emoji else ""
        print(f"\n{COLORS['title']}{streak_emoji}Streaks:{COLORS['reset']}")
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

        # Sparkline for last 30 days if requested
        if show_sparkline:
            # Get last 30 days of commits
            today = datetime.now().date()
            last_30_days = [(today - timedelta(days=i)) for i in range(29, -1, -1)]
            daily_counts = []
            commit_dates_set = defaultdict(int)
            for commit in commit_data:
                commit_dates_set[commit["date"].date()] += 1

            for day in last_30_days:
                daily_counts.append(commit_dates_set.get(day, 0))

            sparkline = render_sparkline(daily_counts)
            trend_emoji = f"{EMOJIS['chart_up']} " if use_emoji else ""
            print(f"{trend_emoji}Last 30 days trend: {COLORS['bar']}{sparkline}{COLORS['reset']}")

        # Activity Patterns
        activity_emoji = f"{EMOJIS['rocket']} " if use_emoji else ""
        print(f"\n{COLORS['title']}{activity_emoji}Activity Patterns:{COLORS['reset']}")
        print(
            f"Most active hour: {COLORS['number']}{stats['peak_hour'][0]:02d}:00{COLORS['reset']} ({stats['peak_hour'][1]} commits)"
        )
        print(
            f"Most active day: {COLORS['number']}{stats['peak_weekday'][0]}{COLORS['reset']} ({stats['peak_weekday'][1]} commits)"
        )

        # Detailed Activity Charts
        render_activity_chart(stats["weekdays"], "Commits by Day of Week", use_emoji=use_emoji)

        if show_violinplot:
            render_violinplot(
                {f"{hour:02d}:00": count for hour, count in stats["hours"].items()},
                "Commits by Hour",
                use_emoji=use_emoji
            )
        else:
            render_activity_chart(
                {f"{hour:02d}:00": count for hour, count in stats["hours"].items()},
                "Commits by Hour",
                use_emoji=use_emoji
            )

        # Commit size distribution boxplot if requested
        if show_boxplot:
            # Get commit sizes (number of commits per day)
            daily_commit_counts = defaultdict(int)
            for commit in commit_data:
                date_key = commit["date"].date().isoformat()
                daily_commit_counts[date_key] += 1
            if daily_commit_counts:
                render_boxplot(list(daily_commit_counts.values()), "Daily Commit Distribution", use_emoji=use_emoji)

        # Commit Types Distribution
        types_emoji = f"{EMOJIS['check']} " if use_emoji else ""
        print(f"\n{COLORS['title']}{types_emoji}Commit Types:{COLORS['reset']}")
        for type_name, count in stats["commit_types"].items():
            percentage = (count / stats["total_commits"]) * 100
            bar = "█" * int(percentage / 2)
            print(
                f"{type_name.capitalize().ljust(15)} {COLORS['number']}{count:4d}{COLORS['reset']} {COLORS['bar']}{bar}{COLORS['reset']} ({percentage:.1f}%)"
            )

        # Top Contributors
        if len(stats["authors"]) > 1:
            contributors_emoji = f"{EMOJIS['star']} " if use_emoji else ""
            print(f"\n{COLORS['title']}{contributors_emoji}Top Contributors:{COLORS['reset']}")
            for i, (author, commits) in enumerate(
                list(stats["authors"].items())[:5], 1
            ):
                trophy = f" {EMOJIS['trophy']}" if use_emoji and i == 1 else ""
                print(
                    f"{i}. {author}: {COLORS['number']}{commits}{COLORS['reset']} commits{trophy}"
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
        choices=["text", "json", "csv", "svg"],
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
        "-H",
        "--heatmap",
        action="store_true",
        help="Show GitHub-style contribution heatmap",
    )
    parser.add_argument(
        "-e",
        "--emoji",
        action="store_true",
        help="Enable emoji mode for visual indicators",
    )
    parser.add_argument(
        "-n",
        "--notify",
        action="store_true",
        help="Send desktop notifications for milestones",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Disable progress bars",
    )
    parser.add_argument(
        "--sparkline",
        action="store_true",
        help="Show sparkline trends in insights",
    )
    parser.add_argument(
        "--boxplot",
        action="store_true",
        help="Show box plot for commit distribution",
    )
    parser.add_argument(
        "--violinplot",
        action="store_true",
        help="Show violin plot for hourly/daily patterns",
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

    # Check for milestones and send notifications
    if args.notify:
        total_commits = len(commit_data)
        milestones = [100, 500, 1000, 5000, 10000]
        for milestone in milestones:
            if total_commits >= milestone and total_commits < milestone + 10:
                send_notification(
                    f"{EMOJIS['tada']} Milestone Reached!",
                    f"Repository hit {milestone} commits!"
                )

        # Check for streak records
        streaks = calculate_streaks(commit_data)
        if streaks["current_streak"] >= 30:
            send_notification(
                f"{EMOJIS['fire']} Amazing Streak!",
                f"Current streak: {streaks['current_streak']} days!"
            )

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
    elif args.output == "svg":
        # Generate SVG charts
        svg_content = generate_svg_chart(grouped_commits, "commits", "Git Commit Activity")
        if svg_content:
            filename = "git-count-commits.svg"
            with open(filename, 'w') as f:
                f.write(svg_content)
            success_msg = f"{EMOJIS['check']} " if args.emoji else ""
            print(f"{success_msg}SVG chart saved to: {COLORS['number']}{filename}{COLORS['reset']}")

        # Generate heatmap SVG if requested
        if args.heatmap:
            # For now, heatmap only available in text mode
            print(f"{COLORS['alert']}Note: Heatmap SVG generation coming soon. Use text mode for now.{COLORS['reset']}")
    else:
        render_bars(grouped_commits, use_emoji=args.emoji)
        if args.heatmap:
            render_contribution_heatmap(commit_data, use_emoji=args.emoji)
        if args.insights:
            print_repository_insights(
                commit_data,
                use_emoji=args.emoji,
                show_sparkline=args.sparkline,
                show_boxplot=args.boxplot,
                show_violinplot=args.violinplot
            )
        if args.churn:
            churn_data = get_file_churn(
                author=args.author,
                since=args.since,
                until=args.until,
                path=args.directory,
            )
            render_file_churn(churn_data, use_emoji=args.emoji)
        if args.velocity:
            velocity_data = get_velocity(
                period=args.period,
                author=args.author,
                since=args.since,
                until=args.until,
                path=args.directory,
            )
            render_velocity(velocity_data, use_emoji=args.emoji)


if __name__ == "__main__":
    main()
