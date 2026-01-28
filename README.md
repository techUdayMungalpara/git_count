# git_count

A powerful Git commit activity visualization tool with detailed repository insights and beautiful ASCII charts.

[![PyPI Downloads](https://static.pepy.tech/badge/git-count)](https://pepy.tech/projects/git-count)
![Python Version](https://img.shields.io/pypi/pyversions/git-count)

## Installation

```bash
pip install git-count
```

## Features

- Visualize git commit activity with ASCII bars
- Group commits by day, month, or year
- Filter commits by author
- Date range filtering
- Directory-specific analysis
- Detailed repository insights
- Commit streak tracking (current and longest streaks)
- File churn analysis (identify hotspot files)
- Code velocity metrics (lines added/removed per period)
- Multiple output formats (text, JSON, CSV)

## Usage

```bash
# Basic usage
git-count

# Show commits by month
git-count -p month

# Filter by author
git-count -a "uday"

# Show commits since a specific date
git-count -s "2023-01-01"

# Show detailed repository insights
git-count -i

# Output as JSON
git-count -o json

# Show most frequently changed files
git-count -c

# Show code velocity (lines added/removed)
git-count -v

# Show velocity by month
git-count -v -p month
```

## Options

- `-p, --period`: Group commits by period (day/month/year)
- `-a, --author`: Filter commits by author
- `-s, --since`: Show commits more recent than a specific date
- `-u, --until`: Show commits older than a specific date
- `-d, --directory`: Analyze commits in a specific directory
- `-m, --max-commits`: Limit the number of commits to display
- `-o, --output`: Output format (text/json/csv)
- `-i, --insights`: Show detailed repository insights
- `-c, --churn`: Show most frequently changed files (hotspots)
- `-v, --velocity`: Show code velocity (lines added/removed per period)
- `-V, --version`: Show version number
- `-h, --help`: Show help message

## Advanced Examples

```bash
# Combine multiple filters
git-count -a "uday" -s "2024-01-01" -p month -i

# Export data for further analysis
git-count -o json > commits.json
git-count -o csv > commits.csv

# Analyze specific directory changes
git-count -d src/ -p month

# Get insights for team productivity
git-count -i -s "2025-01-01"

# Find hotspot files changed by a specific author
git-count -c -a "uday" -s "2024-01-01"

# Full analysis: insights + churn + velocity
git-count -i -c -v -p month
```

## Customization

You can customize colors by creating a `~/.gitbarsrc` configuration file:

```ini
[colors]
reset = \033[0m
title = \033[1;36m
date = \033[0;32m
number = \033[0;33m
bar = \033[0;34m
alert = \033[0;31m
```

## What You'll See

The insights mode (`-i`) shows:

- Project timeline and age
- Average commits per day
- Current and longest commit streaks
- Most active hours and days
- Commit types distribution (features, fixes, docs, etc.)
- Top contributors
- Activity patterns with visual charts

The churn mode (`-c`) shows:

- Most frequently changed files ranked by number of commits
- Visual bar chart of file change frequency

The velocity mode (`-v`) shows:

- Lines added/removed per period with color-coded bars
- Total lines added, removed, and net change

## Requirements

- Python 3.8+
- Git must be installed and repository must be a valid Git repository

## License

MIT License
