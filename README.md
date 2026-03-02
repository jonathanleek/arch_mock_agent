# Astro Mock Infrastructure Agent

A CLI tool that manages mock infrastructure for local Airflow development with the Astro CLI. Describe the external services your DAGs need in plain English, and the agent writes the correct `docker-compose.override.yml` and `airflow_settings.yaml` for you. When you no longer need a service, ask the agent to remove it and it will clean up the Docker service, Airflow connection, orphaned volumes, and optionally unused provider packages.

## The Problem

When developing DAGs locally with `astro dev start`, your pipelines often depend on external infrastructure — an S3 bucket, a Postgres warehouse, a Redis cache, etc. Getting that running locally means:

- Adding services to `docker-compose.override.yml` with the right images, ports, environment variables, and networking
- Adding matching Airflow connections to `airflow_settings.yaml` with the correct hostnames and ports
- Making sure nothing conflicts with Airflow's own Postgres (5432), webserver (8080), or Redis (6379)

This tool handles all of that. You say what you need, it writes the config. When you're done with a service, tell the agent to remove it and it cleans everything up.

## Prerequisites

- **Python 3.10+**
- **An Anthropic API key** — This tool uses the [Anthropic API](https://docs.anthropic.com/en/docs/initial-setup) to interpret your requests. You'll need an API key, which you can create at [console.anthropic.com](https://console.anthropic.com/). Set it as an environment variable:
  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  ```
- **An existing Astro project** — initialized with `astro dev init`

## Installation

Install with `pipx` (recommended) or `pip`:

```bash
# From a local clone
pipx install .

# Or directly from GitHub
pipx install git+https://github.com/<owner>/arch-mock-agent.git
```

For development:

```bash
git clone <repo-url> astro-mock-agent
cd astro-mock-agent
pip install -e .
```

## Quick Start

From inside your Astro project directory:

```bash
# One-shot: describe what you need and the agent writes the config
astro-mock "I need an S3 bucket and a Postgres database"

# Remove a service you no longer need
astro-mock "Remove the Postgres service"

# Preview what would change without writing any files
astro-mock --dry-run "Add Redis and MongoDB"

# Interactive mode: have a conversation, add and remove services incrementally
astro-mock
```

If your Astro project is in a different directory than your shell's current directory:

```bash
astro-mock --project-dir /path/to/my-astro-project "I need S3"
```

## What It Does

Given a request like `"I need S3 and Postgres"`, the agent:

1. Reads your existing `docker-compose.override.yml` and `airflow_settings.yaml` (if any)
2. Adds a **LocalStack** container for S3 and a **Postgres** container to `docker-compose.override.yml`
3. Adds matching Airflow connections (`aws_default`, `mock_postgres_default`) to `airflow_settings.yaml`
4. Installs required Airflow provider packages in `requirements.txt`
5. Puts every service on the `airflow` network so your DAGs can reach them
6. Picks host ports that don't collide with Airflow's own services
7. Generates a test DAG (`dags/test_connections.py`) that verifies each connection is reachable

When you ask to **remove** a service (e.g. `"Remove mock_postgres"`), the agent:

1. Removes the Docker service from `docker-compose.override.yml`
2. Removes the matching Airflow connection from `airflow_settings.yaml`
3. Cleans up orphaned named volumes
4. Optionally removes provider packages no longer needed by any remaining connection
5. Regenerates the test DAG to reflect the remaining services

After running the agent, restart your local environment to pick up the changes:

```bash
astro dev restart
```

Your DAGs can then use the connection IDs the agent created (it will tell you what they are).

## Supported Services (34)

You can refer to services by name or common aliases. For example, "S3", "SQS", and "aws" all resolve to a single LocalStack container; "cloudant" resolves to CouchDB; "presto" resolves to Trino.

### Relational Databases

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Postgres | `postgres:15` | 5433 | `postgres` | postgresql, pg |
| MySQL | `mysql:8.0` | 3307 | `mysql` | mariadb |
| SQL Server | `mcr.microsoft.com/mssql/server:2022-latest` | 1433 | `mssql` | sqlserver |
| Oracle XE | `gvenzl/oracle-xe:21-slim` | 1521 | `oracle` | oracledb |
| Vertica CE | `vertica/vertica-ce:24.3.0-0` | 5434 | `vertica` | — |

### NoSQL / Document Databases

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| MongoDB | `mongo:7` | 27017 | `mongo` | — |
| CouchDB | `couchdb:3` | 5984 | `cloudant` | cloudant |
| ArangoDB | `arangodb:3.11` | 8529 | `arangodb` | arango |
| Cassandra | `cassandra:4.1` | 9042 | `cassandra` | — |
| YDB | `ydbplatform/local-ydb:latest` | 2136 | `ydb` | — |

### Graph Databases

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Neo4j | `neo4j:5` | 7687 | `neo4j` | — |
| Gremlin Server | `tinkerpop/gremlin-server:3.7.3` | 8182 | `gremlin` | tinkerpop |

### Vector Databases

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Qdrant | `qdrant/qdrant:latest` | 6333 | `qdrant` | — |
| Weaviate | `cr.weaviate.io/semitechnologies/weaviate:1.28.2` | 8083 | `weaviate` | — |
| pgvector | `pgvector/pgvector:pg17` | 5435 | `postgres` | vector_db |

### Search & Analytics

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Elasticsearch | `elasticsearch:8.12.0` | 9200 | `elasticsearch` | es, elastic |
| OpenSearch | `opensearchproject/opensearch:2` | 9201 | `opensearch` | — |
| Trino | `trinodb/trino:latest` | 8081 | `trino` | presto |
| Apache Drill | `apache/drill:1.21.2` | 8047 | `drill` | — |
| Apache Pinot | `apachepinot/pinot:1.2.0` | 8099 | `pinot` | — |
| InfluxDB | `influxdb:2` | 8086 | `influxdb` | influx |

### Caches & Key-Value Stores

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Redis | `redis:7-alpine` | 6380 | `redis` | — |

### Messaging & Streaming

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Apache Kafka | `apache/kafka:3.9` | 9092 | `kafka` | — |

### Cloud Service Emulators

| Service | Docker Image | Host Port | Conn Type | What it mocks |
|---|---|---|---|---|
| LocalStack | `localstack/localstack:latest` | 4566 | `aws` | S3, SQS, SNS, DynamoDB, Lambda, Kinesis, Step Functions, Secrets Manager, and more |
| Azurite | `mcr.microsoft.com/azure-storage/azurite:latest` | 10000 | `wasb` | Azure Blob Storage, Queue Storage, Table Storage |
| fake-gcs-server | `fsouza/fake-gcs-server:latest` | 4443 | `google_cloud_platform` | Google Cloud Storage |
| MinIO | `minio/minio:latest` | 9000 | `aws` | S3-compatible object storage |

### Secrets Management

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| HashiCorp Vault | `hashicorp/vault:1.18` | 8200 | `vault` | hashicorp |

### File Transfer & Remote Access

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| SFTP | `atmoz/sftp` | 2222 | `sftp` | ftp |
| SSH | `linuxserver/openssh-server:latest` | 2223 | `ssh` | openssh |
| Samba | `dperson/samba:latest` | 445 | `samba` | smb, cifs |

### Email

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Mailpit | `axllent/mailpit:latest` | 1025 | `smtp` | smtp, email, mail |

Mailpit captures all outbound email and provides a web UI at port 8025 for inspection.

### CI/CD

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Jenkins | `jenkins/jenkins:lts` | 8082 | `jenkins` | — |

### Compute Engines

| Service | Docker Image | Host Port | Conn Type | Aliases |
|---|---|---|---|---|
| Apache Spark | `bitnami/spark:3.5` | 7077 | `spark` | spark_master |

Runs a Spark master node. For a full cluster, you'd add worker containers separately.

## CLI Reference

```
usage: astro-mock [-h] [--project-dir PROJECT_DIR] [--dry-run] [--model MODEL] [request]
```

| Argument | Description |
|---|---|
| `request` | Natural-language description of what you need. Omit to start interactive mode. |
| `--project-dir` | Path to your Astro project (default: current directory). |
| `--dry-run` | Show what would be written without modifying any files. |
| `--model` | Anthropic model to use (default: `claude-sonnet-4-5-20250929`). |

## How It Works Under the Hood

The agent uses the Anthropic API to interpret your request, then calls a fixed set of internal tools to read and write your config files. It cannot run arbitrary commands or modify anything outside of `docker-compose.override.yml` and `airflow_settings.yaml`.

The tools it has access to:

| Tool | Purpose |
|---|---|
| `list_existing_services` | Reads current config files to see what's already set up |
| `get_service_catalog` | Looks up service types in the built-in catalog |
| `read_current_config` | Reads raw YAML of either config file |
| `add_docker_services` | Generates Docker service definitions and merges them into `docker-compose.override.yml` |
| `add_airflow_connections` | Generates Airflow connections and merges them into `airflow_settings.yaml` |
| `generate_test_dag` | Creates a test DAG that verifies every configured connection |
| `remove_mock_services` | Removes Docker services, Airflow connections, orphaned volumes, and optionally unused providers |

## Safety

- **Backups** — Every time a config file is written, the previous version is saved as a `.bak` file alongside it (e.g. `docker-compose.override.yml.bak`).
- **Dry run** — Use `--dry-run` to preview changes (additions or removals) before committing to anything.
- **Safe removal** — When removing services, orphaned volumes are cleaned up automatically. Provider packages are only removed when explicitly requested (`cleanup_providers`) and the tool cross-checks that no remaining connection still needs the provider.
- **Sandboxed** — The agent can only read and write `docker-compose.override.yml`, `airflow_settings.yaml`, `requirements.txt`, and the test DAG. It cannot execute shell commands or access anything else on your system.

## Examples

**Add multiple services at once:**

```bash
astro-mock "I need Postgres for my warehouse, S3 for file storage, and Redis for caching"
```

**Add to an existing setup (services are merged, not replaced):**

```bash
astro-mock "I need S3 and Postgres"
# ...later...
astro-mock "Now add Redis"
# Redis is added alongside the existing S3 and Postgres config
```

**Remove a service you no longer need:**

```bash
astro-mock "Remove mock_postgres"
# Removes the Docker service, Airflow connection, and orphaned volumes

astro-mock "Remove mock_postgres and clean up its provider package"
# Also removes apache-airflow-providers-postgres from requirements.txt if no other service needs it
```

**Interactive session:**

```
$ astro-mock
> I need a Postgres database and an S3 bucket

  Added mock_postgres (postgres:15) — host port 5433 -> container port 5432
  Added mock_localstack (localstack/localstack:latest) — host port 4566 -> container port 4566
  Connections: mock_postgres_default, aws_default

> Actually, add an SFTP server too

  Added mock_sftp (atmoz/sftp) — host port 2222 -> container port 22
  Connection: mock_sftp_default

> Remove mock_postgres

  Removed mock_postgres service, connection mock_postgres_default, and volume pg_data.

> quit
```

**Preview before writing:**

```bash
astro-mock --dry-run "I need Elasticsearch"
```

## Port Conflicts

The agent knows which ports Airflow reserves and avoids them:

| Port | Used By |
|---|---|
| 5432 | Airflow metadata database (Postgres) |
| 8080 | Airflow webserver |
| 6379 | Airflow triggerer (Redis) |
| 8793 | Airflow worker log server |
| 5555 | Flower (Celery monitor) |

If a service's default port is already taken (by Airflow or by another mock service), the agent automatically increments to the next available port.

## Networking

All mock services are placed on the `airflow` network — the same Docker network that the Astro CLI uses. This means:

- Your DAGs reach mock services by **Docker service name** (e.g. `mock_postgres`), not `localhost`
- Airflow connections use the **container-internal port** (e.g. `5432` for Postgres), not the host-mapped port
- No extra network configuration needed on your part

## Troubleshooting

**"ANTHROPIC_API_KEY not set"** — Export your API key before running the tool. See [Prerequisites](#prerequisites).

**Config not taking effect after running the agent** — Run `astro dev restart` to reload the Docker Compose override and Airflow settings.

**Port already in use** — If another process on your host is using a port the agent picked, stop that process or re-run the agent — it will auto-increment to the next available port.

**Want to remove a service** — Ask the agent to remove it (e.g. `"Remove mock_postgres"`). It will clean up the Docker service, Airflow connection, and orphaned volumes in one step. To fully revert to a previous state, check the `.bak` files created alongside your config.
