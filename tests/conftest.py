import os
from typing import Generator

import pytest
from neo4j import Driver, GraphDatabase
from yarl import URL

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
