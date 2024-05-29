import enum
from itertools import chain
from typing import List, Optional

from attr import define, field
from packaging.version import Version

from neo4j_python_migrations.migration import Migration


class InvalidVersionStatus(enum.Enum):
    """Statuses of versions of invalid migrations."""

    # Migration is detected locally but not applied to the database.
    # It cannot be applied because newer migrations are marked as applied.
    MISSED_REMOTELY = enum.auto()

    # Migration has been applied to the target database
    # and cannot be resolved locally any longer.
    MISSED_LOCALLY = enum.auto()

    # Migration has been changed since
    # it has been applied to the target database.
    DIFFERENT = enum.auto()


@define
class InvalidVersion:
    """
    A class for storing an invalid version.

    Contains the version and its status.
    """

    version: str
    status: InvalidVersionStatus


@define
class AnalyzingResult:
    """A class for storing the analysis result."""

    latest_applied_version: Optional[str] = None
    pending_migrations: List[Migration] = field(factory=lambda: [])  # noqa: WPS522
    invalid_versions: List[InvalidVersion] = field(factory=lambda: [])  # noqa: WPS522


def analyze(  # noqa: WPS210
    local_migrations: List[Migration],
    remote_migrations: List[Migration],
) -> AnalyzingResult:
    """
    Analyze local and remote migrations.

    Finds pending migrations and missed migrations.
    :param local_migrations: sorted local migrations.
    :param remote_migrations: sorted remote migrations.
    :return: analysis result.
    """
    analyzing_result = AnalyzingResult()

    if not remote_migrations:
        analyzing_result.pending_migrations = local_migrations
        return analyzing_result

    analyzing_result.latest_applied_version = remote_migrations[-1].version

    local_migrations_dct = {elem.version: elem for elem in local_migrations}
    remote_migrations_dct = {elem.version: elem for elem in remote_migrations}
    versions = sorted(
        set(chain(local_migrations_dct, remote_migrations_dct)),
        key=Version,
    )
    for version in versions:
        local_migration = local_migrations_dct.get(version)
        remote_migration = remote_migrations_dct.get(version)
        invalid_status = _check_invalid_version_status(
            local_migration,
            remote_migration,
            analyzing_result.latest_applied_version,
        )
        if invalid_status:
            analyzing_result.invalid_versions.append(
                InvalidVersion(version, invalid_status),
            )
            continue

        if local_migration and not remote_migration:
            analyzing_result.pending_migrations.append(local_migration)

    return analyzing_result


def _check_invalid_version_status(
    local_migration: Optional[Migration],
    remote_migration: Optional[Migration],
    latest_applied_version: str,
) -> Optional[InvalidVersionStatus]:
    if local_migration and remote_migration:
        if remote_migration != Migration.from_other(local_migration):
            return InvalidVersionStatus.DIFFERENT

    if not local_migration and remote_migration:
        return InvalidVersionStatus.MISSED_LOCALLY

    if local_migration and not remote_migration:
        if local_migration.parsed_version < Version(latest_applied_version):
            return InvalidVersionStatus.MISSED_REMOTELY
    return None
