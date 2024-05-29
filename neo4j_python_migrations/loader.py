import re
from importlib.util import module_from_spec, spec_from_file_location
from itertools import chain
from pathlib import Path
from typing import List

from neo4j_python_migrations.migration import (
    CypherMigration,
    Migration,
    PythonMigration,
)

_VERSION_PATTERN = re.compile(
    r"V(\d+(?:_\d+)*|\d+(?:\.\d+)*)__([\w ]+)(?:\.(\w+))?",
)


def load(path: Path) -> List[Migration]:  # noqa: WPS210
    """
    Load local migrations that are stored at the specified path.

    :param path: the path to migrations.
    :raises ValueError: if there are files with the same version.
    :return: sorted list of migrations.
    """
    migrations: dict[str, Migration] = {}
    loaders = {
        "py": _load_python_migration,
        "cypher": _load_cypher_migration,
    }
    for migration_file in chain(path.glob("*.py"), path.glob("*.cypher")):
        match = _VERSION_PATTERN.match(migration_file.name)

        if not match:
            continue

        version = _prepare_version(match.groups()[0])
        description = _prepare_description(match.groups()[1])
        extension = match.groups()[2]

        if version in migrations:
            raise ValueError(
                "Duplicate migration found when loading local migrations: "
                f"{version}",
            )

        migrations[version] = loaders[extension](
            version=version,
            description=description,
            migration_file=migration_file,
        )

    return sorted(migrations.values())


def _prepare_version(version: str) -> str:
    return version.replace("_", ".")


def _prepare_description(description: str) -> str:
    return description.replace("_", " ").strip()


def _load_python_migration(
    version: str,
    description: str,
    migration_file: Path,
) -> PythonMigration:
    spec = spec_from_file_location(migration_file.stem, migration_file)
    module = module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore
    return PythonMigration(
        version=version,
        description=description,
        code=module.up,
        source=migration_file.name,
    )


def _load_cypher_migration(
    version: str,
    description: str,
    migration_file: Path,
) -> CypherMigration:
    return CypherMigration(
        version=version,
        description=description,
        query=migration_file.read_text(),
        source=migration_file.name,
    )
