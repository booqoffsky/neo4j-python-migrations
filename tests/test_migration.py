from typing import List
from unittest.mock import MagicMock, Mock, call

import pytest

from neo4j_python_migrations.migration import (
    CypherMigration,
    Migration,
    PythonMigration,
)


def test_apply_python_migration() -> None:
    code = Mock()
    migration = PythonMigration(
        version="0001",
        description="1234",
        code=code,
    )

    session = MagicMock()
    migration.apply(session)

    code.assert_called_with(session)


@pytest.mark.parametrize(
    "query, expected_checksum, expected_statements",
    [
        (
            (
                "MATCH (n) RETURN count(n) AS n;\n"
                "MATCH (n) RETURN count(n) AS n;\n"
                "MATCH (n) RETURN count(n) AS n;\n"
            ),
            "1902097523",
            [
                "MATCH (n) RETURN count(n) AS n",
                "MATCH (n) RETURN count(n) AS n",
                "MATCH (n) RETURN count(n) AS n",
            ],
        ),
        (
            "//some comment\n"
            "  MATCH (n) RETURN n;\n"
            "\n"
            " //some other comment\n"
            " MATCH (n)\n"
            "    RETURN (n);\n"
            ";\n",
            "3156131171",
            [
                "//some comment\n  MATCH (n) RETURN n",
                "//some other comment\n MATCH (n)\n    RETURN (n)",
            ],
        ),
    ],
)
def test_init_cypher_migration(
    query: str,
    expected_checksum: str,
    expected_statements: List[str],
) -> None:
    migration = CypherMigration(
        version="0001",
        description="1234",
        query=query,
    )

    assert migration.checksum == expected_checksum
    assert migration.statements == expected_statements


def test_apply_cypher_migration() -> None:
    migration = CypherMigration(
        version="0001",
        description="1234",
        query="STATEMENT1;STATEMENT2;",
    )

    session = MagicMock()
    migration.apply(session)

    assert call.begin_transaction().__enter__().run("STATEMENT1") in session.mock_calls
    assert call.begin_transaction().__enter__().run("STATEMENT2") in session.mock_calls


def test_migration_from_child() -> None:
    child = PythonMigration(
        version="0001",
        description="initial",
        source="V0001__initial.py",
        code=Mock(),
    )
    parent = Migration.from_other(child)
    assert parent == Migration(
        version="0001",
        description="initial",
        source="V0001__initial.py",
        type="PYTHON",
    )


def test_migration_from_dict() -> None:
    db_properties = {
        "version": "0001",
        "description": "initial",
        "source": "V0001__initial.cypher",
        "type": "CYPHER",
    }
    migration = Migration.from_dict(db_properties)
    assert migration == Migration(
        version="0001",
        description="initial",
        source="V0001__initial.cypher",
        type="CYPHER",
    )


def test_migration_from_other() -> None:
    child_migration = PythonMigration(
        version="0001",
        description="initial",
        source="V0001__initial.py",
        code=Mock(),
    )
    migration = Migration.from_other(child_migration)
    assert migration == Migration(
        version="0001",
        description="initial",
        source="V0001__initial.py",
        type="PYTHON",
    )


def test_exception_if_apply_method_is_not_implemented() -> None:
    migration = Migration(version="0001", description="initial", type="CYPHER")

    with pytest.raises(NotImplementedError):
        migration.apply(Mock())
