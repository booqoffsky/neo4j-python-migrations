![python version](https://img.shields.io/pypi/pyversions/neo4j-python-migrations?style=for-the-badge) 
[![version](https://img.shields.io/pypi/v/neo4j-python-migrations?style=for-the-badge)](https://pypi.org/project/neo4j-python-migrations/)
![Codecov](https://img.shields.io/codecov/c/github/booqoffsky/neo4j-python-migrations?style=for-the-badge&token=CP9ZKK430Z)

# neo4j-python-migrations

> It is a database migration tool for [Neo4j](http://neo4j.com) written in Python
> that allows to apply not only Cypher migrations, but also arbitrary Python-based migrations.
> 
> This tool is inspired by [Michael Simons tool for Java](https://github.com/michael-simons/neo4j-migrations)
> and works directly on [neo4j-python-driver](https://github.com/neo4j/neo4j-python-driver).

# Features
- Python migration support makes it possible to do any things in your migration that Python allows you to do.
- Cypher-based migrations support.
- It can be used either via the command line or directly in your code.
- Multi-database support for Neo4j Enterprise Edition users.
- The ability to separate logically independent migration chains within a single database (see the `project` option).
May be useful for Neo4j Community Edition users.

# Installation
From PyPi:

`pip3 install neo4j-python-migrations`

# Usage
## Creating migrations
### Naming Convention
Each migration will be a Cypher or Python file following the format `V<sem_ver>__<migration_name>.ext`.

Make sure to follow the naming convention as stated in 
[Michael's tool documentation](https://michael-simons.github.io/neo4j-migrations/current/#concepts_naming-conventions)
(except that .py files are allowed).

### Cypher
Just create a Cypher file with your custom script, for example `./migrations/V0001__initial.cypher`:
```
CREATE CONSTRAINT UniqueAuthor IF NOT EXISTS FOR (a:AUTHOR) REQUIRE a.uuid IS UNIQUE;
CREATE INDEX author_uuid_index IF NOT EXISTS FOR (a:AUTHOR) ON (a.uuid);
```
This script will be executed within a single transaction.
Therefore, if you need both DDL and DML commands, split them into different files.

### Python
Python-based migrations should have a special format, for example `./migrations/V0002__drop_index.py`:
```
from neo4j import Transaction


# This function must be present
def up(tx: Transaction):
    tx.run("DROP CONSTRAINT UniqueAuthor")
```

## Applying migrations
### CLI
You can apply migrations or verify the status of migrations using the command line interface:
```
Usage: python -m neo4j_python_migrations [OPTIONS] COMMAND [ARGS]...

Options:
  --username TEXT                 The login of the user connecting to the
                                  database.  [env var: NEO4J_MIGRATIONS_USER;
                                  default: neo4j]
  --password TEXT                 The password of the user connecting to the
                                  database.  [env var: NEO4J_MIGRATIONS_PASS;
                                  default: neo4j]
  --path PATH                     The path to the directory for scanning
                                  migration files.  [env var:
                                  NEO4J_MIGRATIONS_PATH; required]
  --port INTEGER                  Port for connecting to the database  [env
                                  var: NEO4J_MIGRATIONS_PORT; default: 7687]
  --host TEXT                     Host for connecting to the database  [env
                                  var: NEO4J_MIGRATIONS_HOST; default:
                                  127.0.0.1]
  --scheme TEXT                   Scheme for connecting to the database
                                  [default: neo4j]
  --project TEXT                  The name of the project for separating
                                  logically independent migration chains
                                  within a single database.  [env var:
                                  NEO4J_MIGRATIONS_PROJECT]
  --schema-database TEXT          The database that should be used for storing
                                  information about migrations (Neo4j EE). If
                                  not specified, then the database that should
                                  be migrated is used.  [env var:
                                  NEO4J_MIGRATIONS_SCHEMA_DATABASE]
  --database TEXT                 The database that should be migrated (Neo4j
                                  EE)  [env var: NEO4J_MIGRATIONS_DATABASE]
  --install-completion [bash|zsh|fish|powershell|pwsh]
                                  Install completion for the specified shell.
  --show-completion [bash|zsh|fish|powershell|pwsh]
                                  Show completion for the specified shell, to
                                  copy it or customize the installation.
  --help                          Show this message and exit.

Commands:
  analyze  Analyze migrations, find pending and missed.
  migrate  Retrieves all pending migrations, verify and applies them.
```

So, to apply migrations, just run the command:

`python3 -m neo4j_python_migrations --username neo4j --password test --path ./migrations migrate`

_Note: it is more secure to store the password in the environment variable NEO4J_MIGRATIONS_PASS._

### Python Code
You can apply migrations directly into your application:

```
from pathlib import Path

from neo4j import GraphDatabase

from neo4j_python_migrations.executor import Executor

with GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "test")) as driver:
    executor = Executor(driver, migrations_path=Path("./migrations"))
    executor.migrate()
```
Available methods: `migrate`, `analyze`. 

# How migrations are tracked
Information about the applied migrations is stored in the database using the schema
described in [Michael's README](https://michael-simons.github.io/neo4j-migrations/current/#concepts_chain).

Supported migration types: СYPHER, PYTHON. Other types of migrations, such as JAVA, are not supported.

Note: the `project` option are incompatible with this schema. 
When using the option, each migration nodes will have an additional property named `project`.


