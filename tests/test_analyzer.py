from neo4j_python_migrations.analyzer import (
    AnalyzingResult,
    InvalidVersion,
    InvalidVersionStatus,
    analyze,
)
from neo4j_python_migrations.migration import Migration, MigrationType


def test_pending_migrations() -> None:
    local_migrations = [
        Migration(version="0001", description="123", type=MigrationType.PYTHON),
    ]
    remote_migrations: list[Migration] = []

    assert analyze(local_migrations, remote_migrations) == AnalyzingResult(
        pending_migrations=local_migrations,
    )


def test_pending_migrations_when_there_are_applied() -> None:
    local_migrations = [
        Migration(version="0001", description="123", type=MigrationType.PYTHON),
        Migration(version="0002", description="123", type=MigrationType.PYTHON),
    ]
    remote_migrations = [
        Migration(version="0001", description="123", type=MigrationType.PYTHON),
    ]

    assert analyze(local_migrations, remote_migrations) == AnalyzingResult(
        pending_migrations=[local_migrations[1]],
        latest_applied_version="0001",
    )


def test_ok_when_all_migrations_are_applied() -> None:
    local_migrations = [
        Migration(version="0001", description="123", type=MigrationType.PYTHON),
    ]
    remote_migrations = [
        Migration(version="0001", description="123", type=MigrationType.PYTHON),
    ]

    assert analyze(local_migrations, remote_migrations) == AnalyzingResult(
        latest_applied_version="0001",
    )


def test_ok_when_there_are_no_migrations() -> None:
    local_migrations: list[Migration] = []
    remote_migrations: list[Migration] = []

    assert analyze(local_migrations, remote_migrations) == AnalyzingResult()


def test_remote_migrations_missed_locally() -> None:
    local_migrations = [
        Migration(version="0002", description="123", type=MigrationType.PYTHON),
    ]
    remote_migrations = [
        Migration(version="0001", description="123", type=MigrationType.PYTHON),
        Migration(version="0002", description="123", type=MigrationType.PYTHON),
    ]

    assert analyze(local_migrations, remote_migrations) == AnalyzingResult(
        invalid_versions=[
            InvalidVersion("0001", InvalidVersionStatus.MISSED_LOCALLY),
        ],
        latest_applied_version="0002",
    )


def test_local_migrations_missed_remotely() -> None:
    local_migrations = [
        Migration(version="0001", description="123", type=MigrationType.PYTHON),
        Migration(version="0002", description="123", type=MigrationType.PYTHON),
    ]
    remote_migrations = [
        Migration(version="0002", description="123", type=MigrationType.PYTHON),
    ]

    assert analyze(local_migrations, remote_migrations) == AnalyzingResult(
        invalid_versions=[
            InvalidVersion("0001", InvalidVersionStatus.MISSED_REMOTELY),
        ],
        latest_applied_version="0002",
    )


def test_migrations_are_different() -> None:
    local_migrations = [
        Migration(version="0001", description="desc1", type=MigrationType.PYTHON),
    ]
    remote_migrations = [
        Migration(version="0001", description="desc2", type=MigrationType.PYTHON),
    ]

    assert analyze(local_migrations, remote_migrations) == AnalyzingResult(
        invalid_versions=[
            InvalidVersion("0001", InvalidVersionStatus.DIFFERENT),
        ],
        latest_applied_version="0001",
    )
