import os
from typing import Generator

import pytest
from neo4j import Driver, GraphDatabase
from yarl import URL

username = os.environ.get("NEO4J_MIGRATIONS_USER", "neo4j")
password = os.environ.get("NEO4J_MIGRATIONS_PASS", "neo4j")
host = os.environ.get("NEO4J_MIGRATIONS_HOST", "localhost")
port = int(os.environ.get("NEO4J_MIGRATIONS_PORT", 7687))
scheme = os.environ.get("NEO4J_MIGRATIONS_SCHEME", "bolt")


def can_connect_to_neo4j() -> bool:
    try:
        with GraphDatabase.driver(
            str(URL.build(scheme=scheme, host=host, port=port)),
            auth=(username, password),
            connection_acquisition_timeout=5,
        ) as driver:
            driver.verify_connectivity()
        return True
    except Exception:
        return False


@pytest.fixture
def neo4j_driver() -> Generator[Driver, None, None]:
    with GraphDatabase.driver(
        str(URL.build(scheme=scheme, host=host, port=port)),
        auth=(username, password),
    ) as driver:
        yield driver
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            constraints = session.run("SHOW CONSTRAINTS YIELD name")
            for record in constraints:
                session.run(f"DROP CONSTRAINT {record[0]}")
