"""ClickHouse database connection and client wrapper."""

import os
from typing import List, Dict, Any, Optional

_CLICKHOUSE_IMPORT_ERROR: Optional[ModuleNotFoundError]

try:
    from clickhouse_driver import Client
except ModuleNotFoundError as import_error:  # pragma: no cover - import guard
    Client = None  # type: ignore[assignment]
    _CLICKHOUSE_IMPORT_ERROR = import_error
else:  # pragma: no cover - import guard
    _CLICKHOUSE_IMPORT_ERROR = None
from contextlib import contextmanager
import structlog

logger = structlog.get_logger()


class ClickHouseClient:
    """
    ClickHouse client wrapper for analytics queries.

    Handles connection pooling, query execution, and error handling.
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        """Initialize ClickHouse client with environment variables or provided params."""
        self.host = host or os.getenv("CLICKHOUSE_HOST", "localhost")
        self.port = port or int(os.getenv("CLICKHOUSE_PORT", "9000"))
        self.user = user or os.getenv("CLICKHOUSE_USER", "default")
        self.password = password or os.getenv("CLICKHOUSE_PASSWORD", "")
        self.database = database or os.getenv("CLICKHOUSE_DATABASE", "crewai_analytics")

        self._client = None

    def connect(self) -> Client:
        """Establish connection to ClickHouse."""
        if Client is None:
            raise ModuleNotFoundError(
                "clickhouse_driver is required to use ClickHouse integrations. "
                "Install the optional dependency or disable ClickHouse features."
            ) from _CLICKHOUSE_IMPORT_ERROR

        if self._client is None:
            try:
                self._client = Client(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    settings={'use_numpy': False}
                )
                logger.info(
                    "clickhouse_connected",
                    host=self.host,
                    port=self.port,
                    database=self.database
                )
            except Exception as e:
                logger.error("clickhouse_connection_failed", error=str(e))
                raise

        return self._client

    def disconnect(self):
        """Close ClickHouse connection."""
        if self._client:
            self._client.disconnect()
            self._client = None
            logger.info("clickhouse_disconnected")

    @contextmanager
    def get_client(self):
        """Context manager for ClickHouse client."""
        client = self.connect()
        try:
            yield client
        finally:
            # Don't disconnect in context manager - keep connection alive
            pass

    def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        with_column_types: bool = False
    ) -> List[Any]:
        """
        Execute a query and return results.

        Args:
            query: SQL query to execute
            params: Query parameters (optional)
            with_column_types: Return column types along with data

        Returns:
            Query results as list of tuples
        """
        with self.get_client() as client:
            try:
                result = client.execute(
                    query,
                    params=params or {},
                    with_column_types=with_column_types
                )
                return result
            except Exception as e:
                logger.error(
                    "clickhouse_query_failed",
                    query=query[:100],
                    error=str(e)
                )
                raise

    def insert(
        self,
        table: str,
        data: List[Dict[str, Any]],
        column_names: Optional[List[str]] = None
    ) -> int:
        """
        Insert data into ClickHouse table.

        Args:
            table: Table name
            data: List of dictionaries with data to insert
            column_names: Optional list of column names

        Returns:
            Number of rows inserted
        """
        if not data:
            return 0

        with self.get_client() as client:
            try:
                if column_names is None:
                    column_names = list(data[0].keys())

                # Convert list of dicts to list of tuples
                values = [
                    tuple(row.get(col) for col in column_names)
                    for row in data
                ]

                query = f"INSERT INTO {table} ({', '.join(column_names)}) VALUES"

                client.execute(query, values)

                logger.info(
                    "clickhouse_insert_success",
                    table=table,
                    rows_inserted=len(data)
                )

                return len(data)

            except Exception as e:
                logger.error(
                    "clickhouse_insert_failed",
                    table=table,
                    error=str(e)
                )
                raise

    def query_df(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        Execute query and return results as DataFrame (if pandas is available).

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            pandas DataFrame or list of tuples
        """
        try:
            import pandas as pd

            with self.get_client() as client:
                result, columns = client.execute(
                    query,
                    params=params or {},
                    with_column_types=True
                )

                column_names = [col[0] for col in columns]
                return pd.DataFrame(result, columns=column_names)

        except ImportError:
            # Pandas not available, return raw results
            logger.warning("pandas_not_available_returning_raw_results")
            return self.execute(query, params, with_column_types=True)

    def ping(self) -> bool:
        """Check if ClickHouse is reachable."""
        try:
            with self.get_client() as client:
                result = client.execute("SELECT 1")
                return result[0][0] == 1
        except Exception as e:
            logger.error("clickhouse_ping_failed", error=str(e))
            return False


# Singleton instance
_clickhouse_client: Optional[ClickHouseClient] = None


def get_clickhouse_client() -> ClickHouseClient:
    """Get singleton ClickHouse client instance."""
    global _clickhouse_client
    if _clickhouse_client is None:
        _clickhouse_client = ClickHouseClient()
    return _clickhouse_client


def get_clickhouse():
    """Dependency for FastAPI endpoints."""
    return get_clickhouse_client()
