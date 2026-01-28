# git_count

A powerful Git commit activity visualization tool with detailed repository insights, beautiful ASCII charts, and advanced visualizations.

[![PyPI Downloads](https://static.pepy.tech/badge/git-count)](https://pepy.tech/projects/git-count)
![Python Version](https://img.shields.io/pypi/pyversions/git-count)

## Installation

```bash
pip install git-count
```

## Features

### Core Features
- Visualize git commit activity with ASCII bars
- Group commits by day, month, or year
- Filter commits by author
- Date range filtering
- Directory-specific analysis
- Detailed repository insights
- Commit streak tracking (current and longest streaks)
- File churn analysis (identify hotspot files)
- Code velocity metrics (lines added/removed per period)
- Multiple output formats (text, JSON, CSV, SVG)

### Advanced Visualizations
- **GitHub-style Contribution Heatmap** - 365-day calendar view of commit activity
- **Sparklines** - Compact trend visualization for commit patterns
- **Box Plots** - Statistical distribution of commit activity
- **Violin Plots** - Density visualization for hourly/daily patterns
- **SVG Export** - Publication-ready vector graphics
- **Emoji Mode** - Visual indicators for enhanced readability
- **Desktop Notifications** - Milestone alerts for achievements
- **Progress Bars** - Real-time feedback for large repository analysis

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

### Basic Options
- `-p, --period`: Group commits by period (day/month/year)
- `-a, --author`: Filter commits by author
- `-s, --since`: Show commits more recent than a specific date
- `-u, --until`: Show commits older than a specific date
- `-d, --directory`: Analyze commits in a specific directory
- `-m, --max-commits`: Limit the number of commits to display
- `-o, --output`: Output format (text/json/csv/svg)

### Analysis Options
- `-i, --insights`: Show detailed repository insights
- `-c, --churn`: Show most frequently changed files (hotspots)
- `-v, --velocity`: Show code velocity (lines added/removed per period)
- `-H, --heatmap`: Show GitHub-style contribution heatmap

### Visualization Options
- `-e, --emoji`: Enable emoji mode for visual indicators
- `--sparkline`: Show sparkline trends in insights
- `--boxplot`: Show box plot for commit distribution
- `--violinplot`: Show violin plot for hourly/daily patterns

### Utility Options
- `-n, --notify`: Send desktop notifications for milestones
- `-q, --quiet`: Disable progress bars
- `-V, --version`: Show version number
- `-h, --help`: Show help message

## Advanced Examples

```bash
# Show GitHub-style contribution heatmap
git-count -H

# Enable emoji mode for better visuals
git-count -i -e

# Full analysis with advanced visualizations
git-count -i -c -v --sparkline --boxplot --violinplot -e

# Show heatmap with emoji mode
git-count -H -e

# Export to SVG for presentations
git-count -o svg

# Get desktop notifications for milestones
git-count -i -n

# Combine multiple filters with visualizations
git-count -a "uday" -s "2024-01-01" -p month -i --sparkline -e

# Export data for further analysis
git-count -o json > commits.json
git-count -o csv > commits.csv

# Analyze specific directory changes
git-count -d src/ -p month -H

# Get insights for team productivity with emoji mode
git-count -i -s "2025-01-01" -e

# Find hotspot files changed by a specific author
git-count -c -a "uday" -s "2024-01-01" -e

# Full analysis: insights + churn + velocity + heatmap
git-count -i -c -v -H -p month -e
```

## Customization

You can customize colors and emoji settings by creating a `~/.gitbarsrc` configuration file:

```ini
[colors]
reset = \033[0m
title = \033[1;36m
date = \033[0;32m
number = \033[0;33m
bar = \033[0;34m
alert = \033[0;31m

[emoji]
enabled = true
```

## What You'll See

### Insights Mode (`-i`)
- Project timeline and age
- Average commits per day
- Current and longest commit streaks
- Most active hours and days
- Commit types distribution (features, fixes, docs, etc.)
- Top contributors
- Activity patterns with visual charts
- **NEW:** Sparkline trends (`--sparkline`)
- **NEW:** Box plot distribution (`--boxplot`)
- **NEW:** Violin plot patterns (`--violinplot`)

### Contribution Heatmap (`-H`)
- GitHub-style 365-day calendar view
- Color-coded intensity levels (gray to red)
- Weekly and monthly patterns
- Visual commit frequency distribution

### Churn Mode (`-c`)
- Most frequently changed files ranked by number of commits
- Visual bar chart of file change frequency
- Identifies code hotspots

### Velocity Mode (`-v`)
- Lines added/removed per period with color-coded bars
- Total lines added, removed, and net change
- Trend indicators with emoji mode

### Emoji Mode (`-e`)
- 🔥 Hot files and streak indicators
- 🚀 Velocity and activity metrics
- ⭐ Top contributors with 🏆 trophy for #1
- 📈 Trending up, 📉 trending down indicators
- ✨ Enhanced visual experience

### SVG Export (`-o svg`)
- Publication-ready vector graphics
- Responsive and scalable charts
- Professional color schemes
- Embeddable in documentation

### Desktop Notifications (`-n`)
- 🎉 Milestone alerts (100, 500, 1000+ commits)
- 🔥 Streak achievements (30+ days)
- Non-intrusive notifications

## Requirements

- Python 3.8+
- Git must be installed and repository must be a valid Git repository

## License

MIT License
