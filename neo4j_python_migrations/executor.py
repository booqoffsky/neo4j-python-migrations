import time
from pathlib import Path
from typing import Callable, Optional

from neo4j import Driver, Transaction

from neo4j_python_migrations import analyzer, loader
from neo4j_python_migrations.dao import MigrationDAO
from neo4j_python_migrations.migration import Migration


class Executor:
    """A class for working with migrations."""

    def __init__(  # noqa: WPS211
        self,
        driver: Driver,
        migrations_path: Path,
        project: Optional[str] = None,
        database: Optional[str] = None,
        schema_database: Optional[str] = None,
    ):
        """
        Initialize the class instance by loading local migrations from the file system.

        :param driver: Neo4j driver.
        :param migrations_path: the path to the directory containing migrations.
        :param project: the name of the project for differentiation migration
                        chains within the same database.
        :param database: the database that should be migrated (Neo4j EE).
        :param schema_database: the database that should be used for storing
                                information about migrations (Neo4j EE).
                                If not specified, then the database
                                that should be migrated is used.
        """
        if database and not schema_database:
            schema_database = database

        self.driver = driver
        self.dao = MigrationDAO(
            driver,
            project=project,
            database=database,
            schema_database=schema_database,
        )
        self.local_migrations = loader.load(migrations_path)
        self.database = database

    def migrate(self, on_apply: Optional[Callable[[Migration], None]] = None) -> None:
        """
        Retrieves all pending migrations, verify and applies them.

        :param on_apply: callback that is called when each migration is applied.
        :raises ValueError: if errors were found during migration verification.
        """
        analyzing_result = self.analyze()
        if analyzing_result.invalid_versions:
            raise ValueError(
                "Errors were found during migration verification. "
                "Run the `analyze` command for more information.",
            )

        if not analyzing_result.latest_applied_version:
            self.dao.create_baseline()
            self.dao.create_constraints()

        for migration in analyzing_result.pending_migrations:
            with self.driver.session(database=self.database) as session:
                with session.begin_transaction() as tx:

                    start_time = time.monotonic()
                    migration.apply(tx)
                    duration = time.monotonic() - start_time

                    self.dao.add_migration(
                        migration,
                        duration,
                        tx
                    )

                    if on_apply:
                        on_apply(migration)

    def analyze(self) -> analyzer.AnalyzingResult:
        """
        Analyze local and remote migrations.

        Finds pending migrations and missed migrations.
        :return: analysis result.
        """
        applied_migrations = self.dao.get_applied_migrations()
        return analyzer.analyze(self.local_migrations, applied_migrations)
