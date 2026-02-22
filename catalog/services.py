"""Catalog of mock infrastructure services and their Docker / Airflow config."""

from __future__ import annotations

from typing import Any

# Each entry maps a service *type* keyword to everything needed to generate
# a docker-compose service definition and a matching Airflow connection.
#
# Fields:
#   image          – Docker image to use
#   default_port   – preferred host port (will be bumped if taken)
#   container_port – port the service listens on *inside* the container
#   environment    – env vars for the container
#   volumes        – named volumes (if any)
#   command        – optional command override
#   conn_type      – Airflow connection type
#   conn_schema    – default database / schema name
#   conn_login     – default username
#   conn_password  – default password
#   conn_extra     – dict merged into Airflow connection 'extra' JSON
#   aliases        – alternative names users might type

SERVICE_CATALOG: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Relational Databases
    # -------------------------------------------------------------------------
    "postgres": {
        "image": "postgres:15",
        "default_port": 5433,
        "container_port": 5432,
        "environment": {
            "POSTGRES_USER": "mock_user",
            "POSTGRES_PASSWORD": "mock_password",
            "POSTGRES_DB": "mock_db",
        },
        "volumes": {"mock_postgres_data": "/var/lib/postgresql/data"},
        "conn_type": "postgres",
        "conn_schema": "mock_db",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["postgresql", "pg"],
    },
    "mysql": {
        "image": "mysql:8.0",
        "default_port": 3307,
        "container_port": 3306,
        "environment": {
            "MYSQL_ROOT_PASSWORD": "mock_root",
            "MYSQL_USER": "mock_user",
            "MYSQL_PASSWORD": "mock_password",
            "MYSQL_DATABASE": "mock_db",
        },
        "volumes": {"mock_mysql_data": "/var/lib/mysql"},
        "conn_type": "mysql",
        "conn_schema": "mock_db",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["mariadb"],
    },
    "mssql": {
        "image": "mcr.microsoft.com/mssql/server:2022-latest",
        "default_port": 1433,
        "container_port": 1433,
        "environment": {
            "ACCEPT_EULA": "Y",
            "MSSQL_SA_PASSWORD": "MockPass1!",
            "MSSQL_PID": "Developer",
        },
        "volumes": {},
        "conn_type": "mssql",
        "conn_schema": "master",
        "conn_login": "sa",
        "conn_password": "MockPass1!",
        "conn_extra": {},
        "aliases": ["sqlserver", "sql_server", "microsoft_sql"],
    },
    "oracle": {
        "image": "gvenzl/oracle-xe:21-slim",
        "default_port": 1521,
        "container_port": 1521,
        "environment": {
            "ORACLE_PASSWORD": "mock_password",
            "APP_USER": "mock_user",
            "APP_USER_PASSWORD": "mock_password",
        },
        "volumes": {"mock_oracle_data": "/opt/oracle/oradata"},
        "conn_type": "oracle",
        "conn_schema": "XEPDB1",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["oracle_xe", "oracledb"],
    },
    "vertica": {
        "image": "vertica/vertica-ce:24.3.0-0",
        "default_port": 5434,
        "container_port": 5433,
        "environment": {
            "APP_DB_USER": "mock_user",
            "APP_DB_PASSWORD": "mock_password",
            "TZ": "UTC",
        },
        "volumes": {"mock_vertica_data": "/data"},
        "conn_type": "vertica",
        "conn_schema": "docker",
        "conn_login": "dbadmin",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["vertica_ce"],
    },
    # -------------------------------------------------------------------------
    # NoSQL / Document Databases
    # -------------------------------------------------------------------------
    "mongodb": {
        "image": "mongo:7",
        "default_port": 27017,
        "container_port": 27017,
        "environment": {
            "MONGO_INITDB_ROOT_USERNAME": "mock_user",
            "MONGO_INITDB_ROOT_PASSWORD": "mock_password",
        },
        "volumes": {"mock_mongo_data": "/data/db"},
        "conn_type": "mongo",
        "conn_schema": "mock_db",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["mongo"],
    },
    "couchdb": {
        "image": "couchdb:3",
        "default_port": 5984,
        "container_port": 5984,
        "environment": {
            "COUCHDB_USER": "mock_user",
            "COUCHDB_PASSWORD": "mock_password",
        },
        "volumes": {"mock_couchdb_data": "/opt/couchdb/data"},
        "conn_type": "cloudant",
        "conn_schema": "",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["cloudant"],
    },
    "arangodb": {
        "image": "arangodb:3.11",
        "default_port": 8529,
        "container_port": 8529,
        "environment": {
            "ARANGO_ROOT_PASSWORD": "mock_password",
        },
        "volumes": {"mock_arango_data": "/var/lib/arangodb3"},
        "conn_type": "arangodb",
        "conn_schema": "_system",
        "conn_login": "root",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["arango"],
    },
    "cassandra": {
        "image": "cassandra:4.1",
        "default_port": 9042,
        "container_port": 9042,
        "environment": {
            "CASSANDRA_CLUSTER_NAME": "MockCluster",
            "MAX_HEAP_SIZE": "512M",
            "HEAP_NEWSIZE": "128M",
        },
        "volumes": {"mock_cassandra_data": "/var/lib/cassandra"},
        "conn_type": "cassandra",
        "conn_schema": "",
        "conn_login": "cassandra",
        "conn_password": "cassandra",
        "conn_extra": {},
        "aliases": ["apache_cassandra"],
    },
    "ydb": {
        "image": "ydbplatform/local-ydb:latest",
        "default_port": 2136,
        "container_port": 2136,
        "environment": {
            "GRPC_PORT": "2136",
            "YDB_USE_IN_MEMORY_PDISKS": "true",
        },
        "volumes": {},
        "conn_type": "ydb",
        "conn_schema": "/local",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["yandex_db"],
    },
    # -------------------------------------------------------------------------
    # Graph Databases
    # -------------------------------------------------------------------------
    "neo4j": {
        "image": "neo4j:5",
        "default_port": 7687,
        "container_port": 7687,
        "environment": {
            "NEO4J_AUTH": "neo4j/mock_password",
        },
        "volumes": {"mock_neo4j_data": "/data"},
        "conn_type": "neo4j",
        "conn_schema": "",
        "conn_login": "neo4j",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["neo"],
    },
    "gremlin": {
        "image": "tinkerpop/gremlin-server:3.7.3",
        "default_port": 8182,
        "container_port": 8182,
        "environment": {},
        "volumes": {},
        "conn_type": "gremlin",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["tinkerpop", "gremlin_server", "apache_tinkerpop"],
    },
    # -------------------------------------------------------------------------
    # Vector Databases
    # -------------------------------------------------------------------------
    "qdrant": {
        "image": "qdrant/qdrant:latest",
        "default_port": 6333,
        "container_port": 6333,
        "environment": {},
        "volumes": {"mock_qdrant_data": "/qdrant/storage"},
        "conn_type": "qdrant",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": [],
    },
    "weaviate": {
        "image": "cr.weaviate.io/semitechnologies/weaviate:1.28.2",
        "default_port": 8083,
        "container_port": 8080,
        "environment": {
            "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED": "true",
            "PERSISTENCE_DATA_PATH": "/var/lib/weaviate",
            "QUERY_DEFAULTS_LIMIT": "25",
            "CLUSTER_HOSTNAME": "node1",
        },
        "volumes": {"mock_weaviate_data": "/var/lib/weaviate"},
        "conn_type": "weaviate",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": [],
    },
    "pgvector": {
        "image": "pgvector/pgvector:pg17",
        "default_port": 5435,
        "container_port": 5432,
        "environment": {
            "POSTGRES_USER": "mock_user",
            "POSTGRES_PASSWORD": "mock_password",
            "POSTGRES_DB": "mock_vector_db",
        },
        "volumes": {"mock_pgvector_data": "/var/lib/postgresql/data"},
        "conn_type": "postgres",
        "conn_schema": "mock_vector_db",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["pgvector_db", "vector_db"],
    },
    # -------------------------------------------------------------------------
    # Search & Analytics Engines
    # -------------------------------------------------------------------------
    "elasticsearch": {
        "image": "docker.elastic.co/elasticsearch/elasticsearch:8.12.0",
        "default_port": 9200,
        "container_port": 9200,
        "environment": {
            "discovery.type": "single-node",
            "xpack.security.enabled": "false",
            "ES_JAVA_OPTS": "-Xms512m -Xmx512m",
        },
        "volumes": {"mock_es_data": "/usr/share/elasticsearch/data"},
        "conn_type": "elasticsearch",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["es", "elastic"],
    },
    "opensearch": {
        "image": "opensearchproject/opensearch:2",
        "default_port": 9201,
        "container_port": 9200,
        "environment": {
            "discovery.type": "single-node",
            "DISABLE_SECURITY_PLUGIN": "true",
            "OPENSEARCH_JAVA_OPTS": "-Xms512m -Xmx512m",
        },
        "volumes": {"mock_opensearch_data": "/usr/share/opensearch/data"},
        "conn_type": "opensearch",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["open_search"],
    },
    "trino": {
        "image": "trinodb/trino:latest",
        "default_port": 8081,
        "container_port": 8080,
        "environment": {},
        "volumes": {},
        "conn_type": "trino",
        "conn_schema": "tpch",
        "conn_login": "mock_user",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["trinodb", "presto"],
    },
    "drill": {
        "image": "apache/drill:1.21.2",
        "default_port": 8047,
        "container_port": 8047,
        "environment": {},
        "volumes": {},
        "conn_type": "drill",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["apache_drill"],
    },
    "pinot": {
        "image": "apachepinot/pinot:1.2.0",
        "default_port": 8099,
        "container_port": 8099,
        "command": "QuickStart -type batch",
        "environment": {
            "JAVA_OPTS": "-Xms512m -Xmx1g",
        },
        "volumes": {},
        "conn_type": "pinot",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["apache_pinot"],
    },
    "influxdb": {
        "image": "influxdb:2",
        "default_port": 8086,
        "container_port": 8086,
        "environment": {
            "DOCKER_INFLUXDB_INIT_MODE": "setup",
            "DOCKER_INFLUXDB_INIT_USERNAME": "mock_user",
            "DOCKER_INFLUXDB_INIT_PASSWORD": "mock_password",
            "DOCKER_INFLUXDB_INIT_ORG": "mock_org",
            "DOCKER_INFLUXDB_INIT_BUCKET": "mock_bucket",
            "DOCKER_INFLUXDB_INIT_ADMIN_TOKEN": "mock_token",
        },
        "volumes": {"mock_influxdb_data": "/var/lib/influxdb2"},
        "conn_type": "influxdb",
        "conn_schema": "",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {
            "token": "mock_token",
            "org_name": "mock_org",
        },
        "aliases": ["influx"],
    },
    # -------------------------------------------------------------------------
    # Caches & Key-Value Stores
    # -------------------------------------------------------------------------
    "redis": {
        "image": "redis:7-alpine",
        "default_port": 6380,
        "container_port": 6379,
        "environment": {},
        "volumes": {},
        "conn_type": "redis",
        "conn_schema": "0",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": [],
    },
    # -------------------------------------------------------------------------
    # Messaging & Streaming
    # -------------------------------------------------------------------------
    "kafka": {
        "image": "apache/kafka:3.9",
        "default_port": 9092,
        "container_port": 9092,
        "environment": {
            "KAFKA_NODE_ID": "1",
            "KAFKA_PROCESS_ROLES": "broker,controller",
            "KAFKA_LISTENERS": "PLAINTEXT://:9092,CONTROLLER://:9093",
            "KAFKA_CONTROLLER_QUORUM_VOTERS": "1@localhost:9093",
            "KAFKA_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
            "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
            "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": "1",
            "CLUSTER_ID": "mock-kafka-cluster-00001",
        },
        "volumes": {},
        "conn_type": "kafka",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {
            "bootstrap.servers": "{service_name}:{container_port}",
        },
        "aliases": ["apache_kafka"],
    },
    # -------------------------------------------------------------------------
    # Cloud Service Emulators
    # -------------------------------------------------------------------------
    "localstack": {
        "image": "localstack/localstack:latest",
        "default_port": 4566,
        "container_port": 4566,
        "environment": {
            "SERVICES": "s3,sqs,sns,secretsmanager,lambda,dynamodb,kinesis,stepfunctions,sts,iam,logs,events",
            "DEBUG": "0",
        },
        "volumes": {"mock_localstack_data": "/var/lib/localstack"},
        "conn_type": "aws",
        "conn_schema": "",
        "conn_login": "test",
        "conn_password": "test",
        "conn_extra": {
            "region_name": "us-east-1",
            "endpoint_url": "http://{service_name}:{container_port}",
        },
        "aliases": [
            "aws", "s3", "sqs", "sns", "dynamodb", "secretsmanager",
            "lambda", "kinesis", "stepfunctions", "sts", "iam",
            "cloudwatch", "eventbridge",
        ],
    },
    "azurite": {
        "image": "mcr.microsoft.com/azure-storage/azurite:latest",
        "default_port": 10000,
        "container_port": 10000,
        "environment": {},
        "volumes": {"mock_azurite_data": "/data"},
        "conn_type": "wasb",
        "conn_schema": "",
        "conn_login": "devstoreaccount1",
        "conn_password": "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
        "conn_extra": {
            "connection_string": (
                "DefaultEndpointsProtocol=http;"
                "AccountName=devstoreaccount1;"
                "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
                "BlobEndpoint=http://{service_name}:10000/devstoreaccount1;"
                "QueueEndpoint=http://{service_name}:10001/devstoreaccount1;"
                "TableEndpoint=http://{service_name}:10002/devstoreaccount1;"
            ),
        },
        "aliases": [
            "azure_blob", "azure_storage", "wasb", "azure",
            "blob_storage", "azure_queue", "azure_table",
        ],
    },
    "fake_gcs": {
        "image": "fsouza/fake-gcs-server:latest",
        "default_port": 4443,
        "container_port": 4443,
        "command": "-scheme http -port 4443 -external-url http://{service_name}:4443",
        "environment": {},
        "volumes": {"mock_gcs_data": "/data"},
        "conn_type": "google_cloud_platform",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {
            "project": "mock-project",
            "num_retries": 0,
        },
        "aliases": ["gcs", "google_cloud_storage", "gcp_storage"],
    },
    "minio": {
        "image": "minio/minio:latest",
        "default_port": 9000,
        "container_port": 9000,
        "environment": {
            "MINIO_ROOT_USER": "minioadmin",
            "MINIO_ROOT_PASSWORD": "minioadmin",
        },
        "volumes": {"mock_minio_data": "/data"},
        "command": "server /data --console-address ':9001'",
        "conn_type": "aws",
        "conn_schema": "",
        "conn_login": "minioadmin",
        "conn_password": "minioadmin",
        "conn_extra": {
            "region_name": "us-east-1",
            "endpoint_url": "http://{service_name}:{container_port}",
        },
        "aliases": ["minio_s3"],
    },
    # -------------------------------------------------------------------------
    # Secret Management
    # -------------------------------------------------------------------------
    "vault": {
        "image": "hashicorp/vault:1.18",
        "default_port": 8200,
        "container_port": 8200,
        "command": "server -dev",
        "environment": {
            "VAULT_DEV_ROOT_TOKEN_ID": "mock_root_token",
            "VAULT_DEV_LISTEN_ADDRESS": "0.0.0.0:8200",
            "SKIP_SETCAP": "1",
        },
        "volumes": {},
        "conn_type": "vault",
        "conn_schema": "secret",
        "conn_login": "",
        "conn_password": "mock_root_token",
        "conn_extra": {
            "auth_type": "token",
        },
        "aliases": ["hashicorp_vault", "hashicorp"],
    },
    # -------------------------------------------------------------------------
    # Time-Series Databases
    # -------------------------------------------------------------------------
    # (influxdb is above in the Search & Analytics section)
    # -------------------------------------------------------------------------
    # File Transfer & Remote Access
    # -------------------------------------------------------------------------
    "sftp": {
        "image": "atmoz/sftp",
        "default_port": 2222,
        "container_port": 22,
        "environment": {},
        "command": "mock_user:mock_password:::upload",
        "volumes": {},
        "conn_type": "sftp",
        "conn_schema": "",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["ftp"],
    },
    "ssh": {
        "image": "linuxserver/openssh-server:latest",
        "default_port": 2223,
        "container_port": 2222,
        "environment": {
            "PUID": "1000",
            "PGID": "1000",
            "TZ": "UTC",
            "PASSWORD_ACCESS": "true",
            "USER_PASSWORD": "mock_password",
            "USER_NAME": "mock_user",
        },
        "volumes": {},
        "conn_type": "ssh",
        "conn_schema": "",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["openssh"],
    },
    "samba": {
        "image": "dperson/samba:latest",
        "default_port": 445,
        "container_port": 445,
        "command": '-u "mock_user;mock_password" -s "share;/share;no;no;no;mock_user"',
        "environment": {},
        "volumes": {"mock_samba_data": "/share"},
        "conn_type": "samba",
        "conn_schema": "share",
        "conn_login": "mock_user",
        "conn_password": "mock_password",
        "conn_extra": {},
        "aliases": ["smb", "cifs"],
    },
    # -------------------------------------------------------------------------
    # Email
    # -------------------------------------------------------------------------
    "mailpit": {
        "image": "axllent/mailpit:latest",
        "default_port": 1025,
        "container_port": 1025,
        "environment": {
            "MP_SMTP_AUTH_ACCEPT_ANY": "true",
        },
        "volumes": {},
        "conn_type": "smtp",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["smtp", "email", "mail"],
    },
    # -------------------------------------------------------------------------
    # CI/CD
    # -------------------------------------------------------------------------
    "jenkins": {
        "image": "jenkins/jenkins:lts",
        "default_port": 8082,
        "container_port": 8080,
        "environment": {
            "JAVA_OPTS": "-Xmx512m",
        },
        "volumes": {"mock_jenkins_data": "/var/jenkins_home"},
        "conn_type": "jenkins",
        "conn_schema": "",
        "conn_login": "admin",
        "conn_password": "admin",
        "conn_extra": {},
        "aliases": [],
    },
    # -------------------------------------------------------------------------
    # Compute / Processing Engines
    # -------------------------------------------------------------------------
    "spark": {
        "image": "bitnami/spark:3.5",
        "default_port": 7077,
        "container_port": 7077,
        "environment": {
            "SPARK_MODE": "master",
        },
        "volumes": {},
        "conn_type": "spark",
        "conn_schema": "",
        "conn_login": "",
        "conn_password": "",
        "conn_extra": {},
        "aliases": ["apache_spark", "spark_master"],
    },
}


def find_service(query: str) -> list[tuple[str, dict[str, Any]]]:
    """Return catalog entries matching *query* (case-insensitive).

    Matches against service key and aliases.
    """
    q = query.strip().lower()
    results: list[tuple[str, dict[str, Any]]] = []
    for key, spec in SERVICE_CATALOG.items():
        names = [key] + spec.get("aliases", [])
        if any(q in name for name in names):
            results.append((key, spec))
    return results
