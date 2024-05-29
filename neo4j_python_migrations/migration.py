import binascii
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from attr import asdict, define, field
from neo4j import Session, Transaction
from packaging.version import Version


class MigrationType(str, Enum):  # noqa: WPS600
    """The type of migration to store in the database."""

    PYTHON = "PYTHON"
    CYPHER = "CYPHER"


@define(kw_only=True, order=False)
class Migration:
    """The base class for all migrations."""

    version: str
    parsed_version: Version = field(init=False)
    description: str
    type: str
    source: Optional[str] = None
    checksum: Optional[str] = None

    @classmethod
    def from_dict(cls, properties: Dict[str, Any]) -> "Migration":
        """
        Get a class instance from a dictionary.

        :param properties: the dictionary.
        :return: class instance.
        """
        return Migration(
            version=properties["version"],
            description=properties["description"],
            type=properties["type"],
            source=properties.get("source"),
            checksum=properties.get("checksum"),
        )

    @classmethod
    def from_other(cls, other: Any) -> "Migration":
        """
        Get a class instance of a base class from a child.

        :param other: the child.
        :return: class instance.
        """
        return cls.from_dict(asdict(other))

    def apply(self, session: Session) -> None:
        """
        Apply migration to the database.

        :param session: neo4j session.
        :raises NotImplementedError: if not implemented.
        """
        raise NotImplementedError()

    def __attrs_post_init__(self) -> None:
        self.parsed_version = Version(self.version)  # noqa: WPS601

    def __lt__(self, other: Any) -> bool:
        return self.parsed_version < other.parsed_version


@define
class PythonMigration(Migration):
    """Migration based on a python code."""

    code: Callable[[Session], None]
    type: str = field(default=MigrationType.PYTHON, init=False)

    def apply(self, session: Session) -> None:  # noqa: D102
        self.code(session)


@define
class CypherMigration(Migration):
    """Migration based on a cypher script."""

    query: str = field(repr=False)
    type: str = field(default=MigrationType.CYPHER, init=False)
    statements: List[str] = field(init=False, repr=False)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        self.statements = list(  # noqa: WPS601
            filter(
                lambda statement: statement,
                [statement.strip() for statement in self.query.split(";")[:-1]],
            ),
        )

        checksum = None
        for st in self.statements:
            binary_statement = st.encode()
            checksum = (
                binascii.crc32(binary_statement, checksum)  # type: ignore
                if checksum
                else binascii.crc32(binary_statement)
            )

        self.checksum = str(checksum)

    def apply(self, tx: Transaction) -> None:  # noqa: D102
        for statement in self.statements:
            tx.run(statement)
