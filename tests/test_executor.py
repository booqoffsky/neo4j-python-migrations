from typing import Optional
from unittest.mock import MagicMock, Mock, patch

from neo4j import Driver
import pytest

from neo4j_python_migrations.analyzer import (
    AnalyzingResult,
    InvalidVersion,
    InvalidVersionStatus,
)
from neo4j_python_migrations.executor import Executor
from neo4j_python_migrations.migration import CypherMigration


@patch("neo4j_python_migrations.loader.load")
@patch("neo4j_python_migrations.executor.Executor.analyze")
def test_migrate_when_there_are_no_remote_migrations(
    executor_mock: MagicMock,
    loader_mock: MagicMock,
) -> None:
    migration = Mock()
    executor_mock.return_value = AnalyzingResult(pending_migrations=[migration])
    executor = Executor(
        driver=MagicMock(),
        migrations_path=Mock(),
    )
    executor.dao = Mock()
    executor.migrate()

    migration.apply.assert_called()
    executor.dao.create_baseline.assert_called()
    executor.dao.add_migration.assert_called()


@patch("neo4j_python_migrations.loader.load")
@patch("neo4j_python_migrations.executor.Executor.analyze")
def test_migrate_with_on_apply_callback(
    executor_mock: MagicMock,
    loader_mock: MagicMock,
) -> None:
    migration = Mock()
    on_apply = Mock()
    executor_mock.return_value = AnalyzingResult(pending_migrations=[migration])
    executor = Executor(
        driver=MagicMock(),
        migrations_path=Mock(),
    )
    executor.dao = Mock()
    executor.migrate(on_apply=on_apply)

    migration.apply.assert_called()
    executor.dao.create_baseline.assert_called()
    executor.dao.add_migration.assert_called()
    on_apply.assert_called_with(migration)


@patch("neo4j_python_migrations.loader.load")
@patch("neo4j_python_migrations.executor.Executor.analyze")
def test_migrate_when_there_are_remote_migrations(
    executor_mock: MagicMock,
    loader_mock: MagicMock,
) -> None:
    migration = Mock()
    executor_mock.return_value = AnalyzingResult(pending_migrations=[migration])

    executor = Executor(
        driver=MagicMock(),
        migrations_path=Mock(),
    )
    executor.dao = Mock()
    executor.migrate()

    migration.apply.assert_called()
    executor.dao.create_baseline.assert_called()
    executor.dao.add_migration.assert_called()


@patch("neo4j_python_migrations.loader.load")
@patch("neo4j_python_migrations.executor.Executor.analyze")
def test_migrate_when_are_invalid_versions(
    executor_mock: MagicMock,
    loader_mock: MagicMock,
) -> None:

    executor_mock.return_value = AnalyzingResult(
        invalid_versions=[
            InvalidVersion("0001", InvalidVersionStatus.DIFFERENT),
        ],
    )
    executor = Executor(
        driver=MagicMock(),
        migrations_path=Mock(),
    )
    executor.dao = Mock()
    with pytest.raises(ValueError):
        executor.migrate()


@patch("neo4j_python_migrations.loader.load")
@pytest.mark.parametrize(
    "db, schema_db, expected_db",
    [
        (None, None, None),
        ("test", None, "test"),
        ("test1", "test2", "test2"),
        (None, "test2", "test2"),
    ],
)
def test_dao_schema_database(
    loader_mock: MagicMock,
    db: Optional[str],
    schema_db: Optional[str],
    expected_db: Optional[str],
) -> None:
    executor = Executor(
        driver=MagicMock(),
        migrations_path=Mock(),
        database=db,
        schema_database=schema_db,
    )
    assert executor.dao.schema_database == expected_db


@patch("neo4j_python_migrations.loader.load")
def test_dao_errors_cause_rollback(loader_mock: MagicMock, neo4j_driver: Driver) -> None:
    migration = CypherMigration(version="0001", description="123", query="CREATE CONSTRAINT foobar FOR (n:Test) REQUIRE n.id IS UNIQUE;")
    executor = Executor(
        driver=neo4j_driver,
        migrations_path=Mock(),
    )

    def getuser():
        raise Exception("Test exception")
    import sys
    sys.modules['neo4j_python_migrations.dao'].getuser = getuser

    executor.analyze = Mock()
    executor.analyze.return_value = AnalyzingResult(pending_migrations=[migration])
    with pytest.raises(Exception, match="Test exception"):
        executor.migrate()

    with neo4j_driver.session() as session:
        x = session.run("SHOW CONSTRAINTS YIELD name")
        names = [i[0] for i in x]
        assert "foobar" not in names


@patch("neo4j_python_migrations.loader.load")
def test_on_apply_errors_cause_rollback(loader_mock: MagicMock, neo4j_driver: Driver) -> None:
    migration = CypherMigration(version="0001", description="123", query="CREATE CONSTRAINT foobar FOR (n:Test) REQUIRE n.id IS UNIQUE;")
    executor = Executor(
        driver=neo4j_driver,
        migrations_path=Mock(),
    )

    executor.analyze = Mock()
    executor.analyze.return_value = AnalyzingResult(pending_migrations=[migration])
    def on_apply(migration):
        raise Exception("Test exception")

    with pytest.raises(Exception, match="Test exception"):
        executor.migrate(on_apply=on_apply)

    with neo4j_driver.session() as session:
        x = session.run("SHOW CONSTRAINTS YIELD name")
        names = [i[0] for i in x]
        assert "foobar" not in names
