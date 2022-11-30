import os
from typing import Generator, Optional

import pytest
from neo4j import Driver, GraphDatabase
from yarl import URL

from neo4j_python_migrations.dao import MigrationDAO
from neo4j_python_migrations.migration import Migration, MigrationType

username = os.environ["NEO4J_MIGRATIONS_USER"]
password = os.environ["NEO4J_MIGRATIONS_PASS"]
host = os.environ["NEO4J_MIGRATIONS_HOST"]
port = int(os.environ["NEO4J_MIGRATIONS_PORT"])
scheme = os.environ["NEO4J_MIGRATIONS_SCHEME"]


@pytest.fixture
def neo4j_driver() -> Generator[Driver, None, None]:
    with GraphDatabase.driver(
        str(URL.build(scheme=scheme, host=host, port=port)),
        auth=(username, password),
    ) as driver:
        yield driver
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")


def test_create_baseline(neo4j_driver: Driver) -> None:
    dao = MigrationDAO(neo4j_driver)

    dao.create_baseline()
    with neo4j_driver.session() as session:
        query_result = session.run(
            "MATCH (m:__Neo4jMigration {version: 'BASELINE'}) RETURN m",
        )
        assert query_result.single()


def test_no_duplicate_baselines(neo4j_driver: Driver) -> None:
    dao = MigrationDAO(neo4j_driver)

    dao.create_baseline()
    dao.create_baseline()

    with neo4j_driver.session() as session:
        query_result = session.run(
            "MATCH (m:__Neo4jMigration {version: 'BASELINE'}) RETURN m",
        )
        assert len(list(query_result)) == 1


def test_user_property(neo4j_driver: Driver) -> None:
    dao = MigrationDAO(neo4j_driver)

    assert dao.user == username


def test_baselines_are_different_for_different_projects(neo4j_driver: Driver) -> None:
    projects = ["project1", "project2"]
    for project in projects:
        dao = MigrationDAO(neo4j_driver, project=project)
        dao.create_baseline()

    with neo4j_driver.session() as session:
        for project in projects:
            query_result = session.run(
                """
                MATCH (m:__Neo4jMigration {
                    version: 'BASELINE',
                    project: $project
                }
                ) RETURN m
                """,
                project=project,
            )
        assert len(list(query_result)) == 1


def test_baselines_are_different_for_different_databases(neo4j_driver: Driver) -> None:
    databases = ["db1", "db2"]
    for db in databases:
        dao = MigrationDAO(neo4j_driver, database=db)
        dao.create_baseline()

    with neo4j_driver.session() as session:
        for db in databases:
            query_result = session.run(
                """
                MATCH (m:__Neo4jMigration {
                    version: 'BASELINE',
                    migrationTarget: $project
                }
                ) RETURN m
                """,
                project=db,
            )
        assert len(list(query_result)) == 1


def test_get_migrations_if_there_are_no_applied_migrations(
    neo4j_driver: Driver,
) -> None:
    dao = MigrationDAO(neo4j_driver)
    assert not dao.get_applied_migrations()


def test_add_and_get_migrations(neo4j_driver: Driver) -> None:
    dao = MigrationDAO(neo4j_driver)
    dao.create_baseline()
    migrations = [
        Migration(version="0001", description="123", type=MigrationType.CYPHER),
        Migration(version="0002", description="te st", type=MigrationType.PYTHON),
    ]

    dao.add_migration(migrations[0], duration=0.1)
    dao.add_migration(migrations[1], duration=0.2)
    applied_migrations = dao.get_applied_migrations()

    assert applied_migrations == migrations


def test_add_and_get_migrations_with_different_project(neo4j_driver: Driver) -> None:
    dao1 = MigrationDAO(neo4j_driver, project="project1")
    dao2 = MigrationDAO(neo4j_driver, project="project2")
    dao1.create_baseline()
    dao2.create_baseline()
    migration = Migration(version="0001", description="123", type=MigrationType.CYPHER)

    dao2.add_migration(migration, duration=0.1)

    assert not dao1.get_applied_migrations()
    assert dao2.get_applied_migrations()


def test_add_and_get_migrations_with_different_databases(neo4j_driver: Driver) -> None:
    dao1 = MigrationDAO(neo4j_driver, database="db1")
    dao2 = MigrationDAO(neo4j_driver, database="db2")
    dao1.create_baseline()
    dao2.create_baseline()
    migration = Migration(version="0001", description="123", type=MigrationType.CYPHER)

    dao2.add_migration(migration, duration=0.1)

    assert not dao1.get_applied_migrations()
    assert dao2.get_applied_migrations()


def test_create_duplicate_constraints(neo4j_driver: Driver) -> None:
    dao = MigrationDAO(neo4j_driver)
    dao.create_constraints()
    dao.create_constraints()


@pytest.mark.parametrize(
    "db, schema_db, expected_db",
    [
        (None, None, None),
        ("test", "test", None),
        ("test1", "test2", "test1"),
    ],
)
def test_database_attr(
    neo4j_driver: Driver,
    db: Optional[str],
    schema_db: Optional[str],
    expected_db: Optional[str],
) -> None:
    dao = MigrationDAO(neo4j_driver, database=db, schema_database=schema_db)
    assert dao.database == expected_db
