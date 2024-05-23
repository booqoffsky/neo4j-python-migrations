from functools import cached_property
from getpass import getuser
from typing import List, Optional

from neo4j import Driver

from neo4j_python_migrations.migration import Migration


class MigrationDAO:
    """DAO for working with the migration schema."""

    def __init__(
        self,
        driver: Driver,
        project: Optional[str] = None,
        database: Optional[str] = None,
        schema_database: Optional[str] = None,
    ):
        self.driver = driver
        self.project = project
        self.schema_database = schema_database
        self.database = None if database == schema_database else database
        self.baseline = "BASELINE"

    @cached_property
    def user(self) -> str | None:
        """
        The name of the user connected to the database.

        :returns: the name.
        """
        with self.driver.session(database=self.schema_database) as session:
            query_result = session.run("SHOW CURRENT USER")
            return query_result.single().value("user") if query_result.single() else None

    def create_baseline(self) -> None:
        """Create a base node if it doesn't already exist."""
        with self.driver.session(database=self.schema_database) as session:
            query_params = {
                "version": self.baseline,
                "project": self.project,
                "migration_target": self.database,
            }
            query_result = session.run(
                """
                MATCH (m:__Neo4jMigration {version: $version})
                WHERE
                    coalesce(m.project,'<default>')
                        = coalesce($project,'<default>')
                    AND coalesce(m.migrationTarget,'<default>')
                        = coalesce($migration_target,'<default>')
                RETURN m
                """,
                query_params,
            )
            if query_result.single():
                return

            session.run(
                """
                CREATE (:__Neo4jMigration {
                    version: $version,
                    project: $project,
                    migrationTarget: $migration_target
                })
                """,
                query_params,
            )

    def create_constraints(self) -> None:
        """
        Create constraints in the database.

        This is useful for maintaining the integrity of the migration schema.
        """
        with self.driver.session(database=self.schema_database) as session:
            session.run(
                """
                CREATE CONSTRAINT unique_version___Neo4jMigration
                IF NOT EXISTS FOR (m:__Neo4jMigration)
                REQUIRE (m.version, m.project, m.migrationTarget) IS UNIQUE
                """,
            )

    def add_migration(
        self,
        migration: Migration,
        duration: float,
    ) -> None:
        """
        Add a migration record.

        :param migration: applied migration.
        :param duration: duration of migration execution (seconds).
        """
        with self.driver.session(database=self.schema_database) as session:
            session.run(
                """
                MATCH (m1:__Neo4jMigration)
                WHERE
                    coalesce(m1.project,'<default>')
                        = coalesce($project,'<default>')
                    AND coalesce(m1.migrationTarget,'<default>')
                        = coalesce($migration_target,'<default>')
                    AND NOT (m1)-[:MIGRATED_TO]->(:__Neo4jMigration)
                WITH m1
                CREATE (m2:__Neo4jMigration {
                        version: $version_to,
                        description: $description,
                        type: $type,
                        source: $source,
                        project: $project,
                        migrationTarget: $migration_target,
                        checksum: $checksum
                    }
                )
                MERGE (m1)-[link:MIGRATED_TO]->(m2)
                SET
                    link.at = datetime(),
                    link.in = duration({seconds: $duration}),
                    link.by = $migrated_by,
                    link.connectedAs = $connected_as
                """,
                version_to=migration.version,
                description=migration.description,
                source=migration.source,
                type=migration.type,
                checksum=migration.checksum,
                duration=duration,
                project=self.project,
                migration_target=self.database,
                migrated_by=getuser(),
                connected_as=self.user,
            )

    def get_applied_migrations(self) -> List[Migration]:
        """
        Get an ordered list of applied migrations to the database.

        The Baseline is ignored.
        :return: sorted list of migrations.
        """
        with self.driver.session(database=self.schema_database) as session:
            query_result = session.run(
                """
                MATCH (:__Neo4jMigration{
                        version: $baseline
                })-[:MIGRATED_TO*]->(m:__Neo4jMigration)
                WHERE
                    coalesce(m.project,'<default>')
                        = coalesce($project,'<default>')
                    AND coalesce(m.migrationTarget,'<default>')
                        = coalesce($migration_target,'<default>')
                RETURN m
                ORDER BY m.version
                """,
                baseline=self.baseline,
                project=self.project,
                migration_target=self.database,
            )
            return [Migration.from_dict(row.data()["m"]) for row in query_result]
