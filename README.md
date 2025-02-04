# git_count

A Git commit activity visualization tool with detailed repository insights.

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
