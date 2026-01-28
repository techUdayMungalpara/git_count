import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from git_count.git_count import (
    calculate_streaks,
    get_commit_details,
    get_file_churn,
    get_git_logs,
    get_velocity,
    render_activity_chart,
    render_bars,
    render_file_churn,
    render_velocity,
)


# --- Helpers ---

def make_commit(date, hash="abc1234", author="Alice", message="fix something"):
    return {"hash": hash, "date": date, "author": author, "message": message}


def make_commit_data(dates, **kwargs):
    return [make_commit(d, **kwargs) for d in dates]


# --- calculate_streaks ---

class TestCalculateStreaks:
    def test_empty_input(self):
        result = calculate_streaks([])
        assert result["current_streak"] == 0
        assert result["longest_streak"] == 0

    def test_single_commit(self):
        today = datetime.now()
        data = make_commit_data([today])
        result = calculate_streaks(data)
        assert result["longest_streak"] == 1
        assert result["current_streak"] >= 0  # depends on time of day

    def test_consecutive_days(self):
        today = datetime.now()
        dates = [today - timedelta(days=i) for i in range(5)]
        data = make_commit_data(dates)
        result = calculate_streaks(data)
        assert result["longest_streak"] == 5
        assert result["current_streak"] == 5

    def test_gap_breaks_streak(self):
        today = datetime.now()
        # 3 days, gap, 2 days
        dates = [
            today,
            today - timedelta(days=1),
            today - timedelta(days=2),
            today - timedelta(days=10),
            today - timedelta(days=11),
        ]
        data = make_commit_data(dates)
        result = calculate_streaks(data)
        assert result["longest_streak"] == 3
        assert result["current_streak"] == 3

    def test_longest_streak_in_past(self):
        today = datetime.now()
        # Current: 1 day (today only)
        # Past: 5 consecutive days, 20 days ago
        dates = [today]
        for i in range(20, 25):
            dates.append(today - timedelta(days=i))
        data = make_commit_data(dates)
        result = calculate_streaks(data)
        assert result["longest_streak"] == 5

    def test_multiple_commits_same_day(self):
        today = datetime.now()
        dates = [today, today, today - timedelta(days=1), today - timedelta(days=1)]
        data = make_commit_data(dates)
        result = calculate_streaks(data)
        assert result["longest_streak"] == 2


# --- get_commit_details ---

class TestGetCommitDetails:
    def test_basic_stats(self):
        dates = [
            datetime(2024, 6, 10, 14, 30),
            datetime(2024, 6, 11, 9, 0),
            datetime(2024, 6, 12, 14, 0),
        ]
        data = [
            make_commit(dates[0], author="Alice", message="fix bug"),
            make_commit(dates[1], author="Bob", message="add feature"),
            make_commit(dates[2], author="Alice", message="refactor code"),
        ]
        result = get_commit_details(data)

        assert result["total_commits"] == 3
        assert result["first_commit"] == dates[0]
        assert result["last_commit"] == dates[2]
        assert result["authors"]["Alice"] == 2
        assert result["authors"]["Bob"] == 1

    def test_commit_type_classification(self):
        base = datetime(2024, 1, 1, 12, 0)
        data = [
            make_commit(base, message="fix login bug"),
            make_commit(base, message="bug in parser"),
            make_commit(base, message="feat: new dashboard"),
            make_commit(base, message="add search"),
            make_commit(base, message="docs update"),
            make_commit(base, message="readme changes"),
            make_commit(base, message="refactor auth module"),
            make_commit(base, message="style cleanup"),
            make_commit(base, message="clean unused imports"),
            make_commit(base, message="test login flow"),
            make_commit(base, message="bump version"),
        ]
        result = get_commit_details(data)
        types = result["commit_types"]

        assert types["fixes"] == 2
        assert types["features"] == 2
        assert types["documentation"] == 2
        assert types["refactoring"] == 3
        assert types["tests"] == 1
        assert types["other"] == 1

    def test_peak_hour(self):
        data = [
            make_commit(datetime(2024, 1, 1, 10, 0)),
            make_commit(datetime(2024, 1, 2, 10, 30)),
            make_commit(datetime(2024, 1, 3, 15, 0)),
        ]
        result = get_commit_details(data)
        assert result["peak_hour"][0] == 10
        assert result["peak_hour"][1] == 2

    def test_weekday_distribution(self):
        # Monday = 0
        data = [
            make_commit(datetime(2024, 1, 1, 12, 0)),   # Monday
            make_commit(datetime(2024, 1, 8, 12, 0)),   # Monday
            make_commit(datetime(2024, 1, 2, 12, 0)),   # Tuesday
        ]
        result = get_commit_details(data)
        assert result["weekdays"]["Monday"] == 2
        assert result["weekdays"]["Tuesday"] == 1


# --- get_git_logs ---

class TestGetGitLogs:
    @patch("git_count.git_count.subprocess.run")
    def test_basic_log_parsing(self, mock_run):
        # First call: git rev-parse (repo check)
        # Second call: git log
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(
                stdout="2024-06-10T14:30:00+00:00|abc1234|Alice|fix bug\n"
                       "2024-06-10T15:00:00+00:00|def5678|Bob|add feature\n",
                returncode=0,
            ),
        ]

        grouped, data = get_git_logs(period="day")
        assert len(data) == 2
        assert "2024-06-10" in grouped
        assert grouped["2024-06-10"] == 2

    @patch("git_count.git_count.subprocess.run")
    def test_monthly_grouping(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(
                stdout="2024-06-10T14:30:00+00:00|abc1234|Alice|fix\n"
                       "2024-07-10T14:30:00+00:00|def5678|Bob|add\n",
                returncode=0,
            ),
        ]

        grouped, data = get_git_logs(period="month")
        assert "2024-06" in grouped
        assert "2024-07" in grouped

    @patch("git_count.git_count.subprocess.run")
    def test_not_a_git_repo(self, mock_run):
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(128, "git")

        grouped, data = get_git_logs()
        assert grouped == {}
        assert data == []

    @patch("git_count.git_count.subprocess.run")
    def test_empty_output(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(stdout="", returncode=0),
        ]

        grouped, data = get_git_logs()
        assert grouped == {}
        assert data == []

    @patch("git_count.git_count.subprocess.run")
    def test_max_commits(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(
                stdout="2024-06-10T14:30:00+00:00|a|Alice|msg1\n"
                       "2024-06-11T14:30:00+00:00|b|Alice|msg2\n"
                       "2024-06-12T14:30:00+00:00|c|Alice|msg3\n",
                returncode=0,
            ),
        ]

        grouped, data = get_git_logs(max_commits=2)
        assert len(data) == 2


# --- get_file_churn ---

class TestGetFileChurn:
    @patch("git_count.git_count.subprocess.run")
    def test_basic_churn(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="src/main.py\nsrc/main.py\nsrc/utils.py\nsrc/main.py\n",
            returncode=0,
        )
        result = get_file_churn()
        assert result[0] == ("src/main.py", 3)
        assert result[1] == ("src/utils.py", 1)

    @patch("git_count.git_count.subprocess.run")
    def test_top_n_limit(self, mock_run):
        lines = "\n".join([f"file{i}.py" for i in range(20)])
        mock_run.return_value = MagicMock(stdout=lines, returncode=0)
        result = get_file_churn(top_n=5)
        assert len(result) == 5

    @patch("git_count.git_count.subprocess.run")
    def test_error_returns_empty(self, mock_run):
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, "git")
        result = get_file_churn()
        assert result == []


# --- get_velocity ---

class TestGetVelocity:
    @patch("git_count.git_count.subprocess.run")
    def test_basic_velocity(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=(
                "2024-06-10T14:30:00+00:00\n"
                "10\t5\tsrc/main.py\n"
                "3\t1\tsrc/utils.py\n"
                "2024-06-11T14:30:00+00:00\n"
                "20\t10\tsrc/main.py\n"
            ),
            returncode=0,
        )
        result = get_velocity(period="day")
        assert result["2024-06-10"]["added"] == 13
        assert result["2024-06-10"]["removed"] == 6
        assert result["2024-06-11"]["added"] == 20
        assert result["2024-06-11"]["removed"] == 10

    @patch("git_count.git_count.subprocess.run")
    def test_monthly_grouping(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=(
                "2024-06-10T14:30:00+00:00\n"
                "10\t5\tsrc/main.py\n"
                "2024-06-20T14:30:00+00:00\n"
                "5\t2\tsrc/main.py\n"
            ),
            returncode=0,
        )
        result = get_velocity(period="month")
        assert "2024-06" in result
        assert result["2024-06"]["added"] == 15
        assert result["2024-06"]["removed"] == 7

    @patch("git_count.git_count.subprocess.run")
    def test_binary_files_skipped(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=(
                "2024-06-10T14:30:00+00:00\n"
                "-\t-\timage.png\n"
                "10\t5\tsrc/main.py\n"
            ),
            returncode=0,
        )
        result = get_velocity(period="day")
        assert result["2024-06-10"]["added"] == 10
        assert result["2024-06-10"]["removed"] == 5


# --- render functions (verify they don't crash) ---

class TestRenderFunctions:
    def test_render_bars_empty(self, capsys):
        render_bars({})
        captured = capsys.readouterr()
        assert "No commits found" in captured.out

    def test_render_bars_basic(self, capsys):
        render_bars({"2024-06-10": 5, "2024-06-11": 3}, max_width=40)
        captured = capsys.readouterr()
        assert "2024-06-10" in captured.out
        assert "2024-06-11" in captured.out

    def test_render_activity_chart(self, capsys):
        render_activity_chart({"Monday": 10, "Tuesday": 5}, "Test Chart")
        captured = capsys.readouterr()
        assert "Test Chart" in captured.out
        assert "Monday" in captured.out

    def test_render_activity_chart_empty(self, capsys):
        render_activity_chart({}, "Empty Chart")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_render_file_churn(self, capsys):
        render_file_churn([("src/main.py", 10), ("src/utils.py", 5)])
        captured = capsys.readouterr()
        assert "src/main.py" in captured.out
        assert "hotspots" in captured.out

    def test_render_file_churn_empty(self, capsys):
        render_file_churn([])
        captured = capsys.readouterr()
        assert "No file change data found" in captured.out

    def test_render_velocity(self, capsys):
        render_velocity({"2024-06-10": {"added": 100, "removed": 50}})
        captured = capsys.readouterr()
        assert "Code Velocity" in captured.out
        assert "+100" in captured.out

    def test_render_velocity_empty(self, capsys):
        render_velocity({})
        captured = capsys.readouterr()
        assert "No velocity data found" in captured.out

    def test_render_file_churn_long_paths(self, capsys):
        long_path = "a" * 60 + "/file.py"
        render_file_churn([(long_path, 5)])
        captured = capsys.readouterr()
        assert "..." in captured.out


# --- main CLI ---

class TestMainCLI:
    @patch("git_count.git_count.get_git_logs")
    def test_json_output(self, mock_logs, capsys):
        mock_logs.return_value = (
            {"2024-06-10": 1},
            [make_commit(datetime(2024, 6, 10, 14, 0))],
        )
        with patch("sys.argv", ["git-count", "-o", "json"]):
            from git_count.git_count import main
            main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "grouped_commits" in data
        assert "commit_data" in data

    @patch("git_count.git_count.get_git_logs")
    def test_csv_output(self, mock_logs, capsys):
        mock_logs.return_value = (
            {"2024-06-10": 1},
            [make_commit(datetime(2024, 6, 10, 14, 0))],
        )
        with patch("sys.argv", ["git-count", "-o", "csv"]):
            from git_count.git_count import main
            main()
        captured = capsys.readouterr()
        assert "Date,Hash,Author,Message" in captured.out

    @patch("git_count.git_count.get_git_logs")
    def test_csv_escapes_commas(self, mock_logs, capsys):
        mock_logs.return_value = (
            {"2024-06-10": 1},
            [make_commit(datetime(2024, 6, 10, 14, 0), message="fix: foo, bar, baz")],
        )
        with patch("sys.argv", ["git-count", "-o", "csv"]):
            from git_count.git_count import main
            main()
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 2  # header + 1 row
        # csv module should quote the message containing commas
        assert '"fix: foo, bar, baz"' in lines[1]

    def test_version_flag(self, capsys):
        with patch("sys.argv", ["git-count", "-V"]):
            from git_count.git_count import main
            main()
        captured = capsys.readouterr()
        assert "git-count" in captured.out
        assert "0.3.0" in captured.out

    @patch("git_count.git_count.get_git_logs")
    def test_no_commits_message(self, mock_logs, capsys):
        mock_logs.return_value = ({}, [])
        with patch("sys.argv", ["git-count"]):
            from git_count.git_count import main
            main()
        captured = capsys.readouterr()
        assert "No commits found" in captured.out
