from datetime import datetime
from pathlib import Path
from typing import Optional

from attr import define
from neo4j import GraphDatabase
from typer import Exit, Option, Typer
from yarl import URL

from neo4j_python_migrations.executor import Executor

cli = Typer()


@define
class State:
    """Storage of common options for commands."""

    username: str
    password: str
    path: Path
    port: int
    host: str
    scheme: str
    project: Optional[str] = None
    database: Optional[str] = None
    schema_database: Optional[str] = None


state: Optional[State] = None


@cli.command(help="Retrieves all pending migrations, verify and applies them.")
def migrate() -> None:  # noqa: D103
    if not state:
        raise Exit(2)

    with GraphDatabase.driver(
        str(URL.build(scheme=state.scheme, host=state.host, port=state.port)),
        auth=(state.username, state.password),
    ) as driver:
        executor = Executor(
            driver=driver,
            migrations_path=Path(state.path),
            project=state.project,
            database=state.database,
            schema_database=state.schema_database,
        )
        executor.migrate(
            on_apply=lambda migration: print(
                f"{datetime.now()} "
                f"Migration V{migration.version} ({migration.description}) APPLIED",
            ),
        )


@cli.command(
    help="Analyze migrations, find pending and missed.",
)
def analyze() -> None:  # noqa: D103
    if not state:
        raise Exit(2)

    with GraphDatabase.driver(
        str(URL.build(scheme=state.scheme, host=state.host, port=state.port)),
        auth=(state.username, state.password),
    ) as driver:
        executor = Executor(
            driver=driver,
            migrations_path=Path(state.path),
            project=state.project,
            database=state.database,
            schema_database=state.schema_database,
        )
        analyzing_result = executor.analyze()

    if analyzing_result.invalid_versions:
        print("The database must be repaired. Invalid versions:")
        for invalid_version in analyzing_result.invalid_versions:
            print(
                f"V{invalid_version.version} "  # noqa: WPS237
                f"Status: {invalid_version.status.name}",
            )
        raise Exit(1)

    print(f"Latest applied version: {analyzing_result.latest_applied_version}")
    if not analyzing_result.pending_migrations:
        print("Database is up-to-date.")
        raise Exit()

    print("Pending migrations:")
    for migration in analyzing_result.pending_migrations:
        print(f"V{migration.version} Source: {migration.source}")


@cli.callback()
def main(  # noqa: WPS211, D103
    username: str = Option(
        "neo4j",
        help="The login of the user connecting to the database.",
        envvar="NEO4J_MIGRATIONS_USER",
    ),
    password: str = Option(
        "neo4j",
        help="The password of the user connecting to the database.",
        envvar="NEO4J_MIGRATIONS_PASS",
    ),
    path: Path = Option(
        ...,
        help="The path to the directory for scanning migration files.",
        envvar="NEO4J_MIGRATIONS_PATH",
    ),
    port: int = Option(
        7687,
        help="Port for connecting to the database",
        envvar="NEO4J_MIGRATIONS_PORT",
    ),
    host: str = Option(
        "127.0.0.1",
        help="Host for connecting to the database",
        envvar="NEO4J_MIGRATIONS_HOST",
    ),
    scheme: str = Option("neo4j", help="Scheme for connecting to the database"),
    project: Optional[str] = Option(
        None,
        help="The name of the project for separating logically independent "
        "migration chains within a single database.",
        envvar="NEO4J_MIGRATIONS_PROJECT",
    ),
    schema_database: Optional[str] = Option(
        None,
        help="The database that should be used for storing "
        "information about migrations (Neo4j EE). "
        "If not specified, then the database "
        "that should be migrated is used.",
        envvar="NEO4J_MIGRATIONS_SCHEMA_DATABASE",
    ),
    database: Optional[str] = Option(
        None,
        help="The database that should be migrated (Neo4j EE)",
        envvar="NEO4J_MIGRATIONS_DATABASE",
    ),
) -> None:
    global state  # noqa: WPS420
    state = State(  # noqa: WPS442
        username=username,
        password=password,
        path=path,
        port=port,
        host=host,
        scheme=scheme,
        project=project,
        database=database,
        schema_database=schema_database,
    )
