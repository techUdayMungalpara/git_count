# git_count

A powerful command-line tool for analyzing and visualizing git repository commit statistics.

## Installation

```bash
pip install git_count
```

## Features

- Visualize git commit activity with ASCII bars
- Group commits by day, month, or year
- Filter commits by author
- Date range filtering
- Directory-specific analysis
- Detailed repository insights
- Multiple output formats (text, JSON, CSV)

## Usage

```bash
# Basic usage
git_count

# Show commits by month
git_count -p month

# Filter by author
git_count -a "uday"

# Show commits since a specific date
git_count -s "2023-01-01"

# Show detailed repository insights
git_count -i

# Output as JSON
git_count -o json
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
- `-h, --help`: Show help message

## License

MIT License
