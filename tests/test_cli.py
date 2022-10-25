from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from neo4j_python_migrations.analyzer import (
    AnalyzingResult,
    InvalidVersion,
    InvalidVersionStatus,
)
from neo4j_python_migrations.cli import cli
from neo4j_python_migrations.migration import Migration

runner = CliRunner()


@patch("neo4j.GraphDatabase.driver")
def test_analyze_when_there_are_pending_migrations(driver: MagicMock) -> None:
    with patch("neo4j_python_migrations.executor.Executor.analyze") as executor_mock:
        executor_mock.return_value = AnalyzingResult(
            pending_migrations=[
                Migration(version="0001", description="", type="CYPHER"),
            ],
        )
        result = runner.invoke(cli, ["--path", ".", "--password", "test", "analyze"])

    assert result.exit_code == 0


@patch("neo4j.GraphDatabase.driver")
def test_analyze_when_there_are_no_pending_migrations(driver: MagicMock) -> None:
    with patch("neo4j_python_migrations.executor.Executor.analyze") as executor_mock:
        executor_mock.return_value = AnalyzingResult()
        result = runner.invoke(cli, ["--path", ".", "--password", "test", "analyze"])
    assert result.exit_code == 0


@patch("neo4j.GraphDatabase.driver")
def test_analyze_when_there_are_invalid_versions(driver: MagicMock) -> None:
    with patch("neo4j_python_migrations.executor.Executor.analyze") as executor_mock:
        executor_mock.return_value = AnalyzingResult(
            invalid_versions=[
                InvalidVersion("0001", InvalidVersionStatus.MISSED_LOCALLY),
            ],
        )
        result = runner.invoke(cli, ["--path", ".", "--password", "test", "analyze"])

    assert result.exit_code != 0


@patch("neo4j.GraphDatabase.driver")
def test_migrate(driver: MagicMock) -> None:
    with patch("neo4j_python_migrations.executor.Executor.migrate") as executor_mock:
        result = runner.invoke(cli, ["--path", ".", "--password", "test", "migrate"])

        assert result.exit_code == 0
        executor_mock.assert_called()
