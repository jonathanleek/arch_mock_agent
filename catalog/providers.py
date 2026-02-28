"""Mapping from Airflow conn_type to the pip provider package needed."""

from __future__ import annotations

# Maps each conn_type used in SERVICE_CATALOG to its pip package name.
# None means the conn_type is built-in or has no dedicated provider.
# Multiple catalog entries can share the same conn_type (e.g. postgres + pgvector
# both use "postgres", localstack + minio both use "aws"), which is why this
# mapping lives here rather than per-service in the catalog.

CONN_TYPE_TO_PROVIDER: dict[str, str | None] = {
    "postgres": "apache-airflow-providers-postgres",
    "mysql": "apache-airflow-providers-mysql",
    "mssql": "apache-airflow-providers-microsoft-mssql",
    "oracle": "apache-airflow-providers-oracle",
    "vertica": "apache-airflow-providers-vertica",
    "mongo": "apache-airflow-providers-mongo",
    "cloudant": None,
    "arangodb": "apache-airflow-providers-arangodb",
    "cassandra": "apache-airflow-providers-apache-cassandra",
    "ydb": "apache-airflow-providers-ydb",
    "neo4j": "apache-airflow-providers-neo4j",
    "gremlin": None,
    "qdrant": "apache-airflow-providers-qdrant",
    "weaviate": "apache-airflow-providers-weaviate",
    "elasticsearch": "apache-airflow-providers-elasticsearch",
    "opensearch": "apache-airflow-providers-opensearch",
    "trino": "apache-airflow-providers-trino",
    "drill": "apache-airflow-providers-apache-drill",
    "pinot": "apache-airflow-providers-apache-pinot",
    "influxdb": "apache-airflow-providers-influxdb",
    "redis": "apache-airflow-providers-redis",
    "kafka": "apache-airflow-providers-apache-kafka",
    "aws": "apache-airflow-providers-amazon",
    "wasb": "apache-airflow-providers-microsoft-azure",
    "google_cloud_platform": "apache-airflow-providers-google",
    "vault": "apache-airflow-providers-hashicorp",
    "sftp": "apache-airflow-providers-sftp",
    "ssh": "apache-airflow-providers-ssh",
    "samba": "apache-airflow-providers-samba",
    "smtp": None,
    "jenkins": "apache-airflow-providers-jenkins",
    "spark": "apache-airflow-providers-apache-spark",
}


def get_provider_packages(conn_types: list[str]) -> list[str]:
    """Return deduplicated provider package names for the given conn_types.

    Filters out ``None`` (built-in / no-provider) entries and preserves
    insertion order.
    """
    seen: set[str] = set()
    packages: list[str] = []
    for ct in conn_types:
        pkg = CONN_TYPE_TO_PROVIDER.get(ct)
        if pkg is not None and pkg not in seen:
            seen.add(pkg)
            packages.append(pkg)
    return packages
