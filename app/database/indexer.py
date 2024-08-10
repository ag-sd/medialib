from pathlib import Path

import duckdb

import app
from app.database import props


def create_index(database_path: str):
    """
    Creates a duckDb index for the database at the save path.
    Args:
        database_path: The database path

    Returns:
        True if the database was indexed, false or ValueError otherwise
    """

    # Create a connection to the db file
    db_path = Path(database_path)
    conn = _get_connection(db_path, is_read_only=False)
    try:
        db_data = db_path / "*.json"
        insert_stmt = (f"CREATE OR REPLACE TABLE {props.DB_INDEX_NAME} AS "
                       f"SELECT * FROM read_json('{db_data}', format='array', records=true, filename=true)")
        # If this database exists, there are already indexes on it. We first drop those
        conn.execute("DROP INDEX IF EXISTS filename_idx;")
        conn.execute(insert_stmt)
        # Create new indexes
        conn.execute(f"CREATE INDEX filename_idx on {props.DB_INDEX_NAME}(filename)")
        conn.commit()
    except Exception as e:
        app.logger.exception(e)
        return False
    finally:
        conn.close()

    return True


def query_index(database_path: str, query: str, path_keys: list):
    """
    Queries the database at the supplied path with the query
    Args:
        database_path: The path to the database
        query: The query to run on the database
        path_keys: The Paths within this database to restrict the search to

    Returns:
        The result of the query

    """
    db_path = Path(database_path)
    conn = _get_connection(db_path, is_read_only=True)
    # https://duckdb.org/docs/api/python/relational_api
    # https://duckdb.org/docs/api/python/relational_api#sql-queries
    # https://duckdb.org/docs/api/c/replacement_scans.html
    try:
        """
        The database stores a field called `filename` which represents the json file from where each record was indexed.
        So, given a list of query paths, we first map these to the keys that would represent the filename of the json 
        file that stores data about the path in the database
        """

        """
        TODO
        Loop over each path and create a relation for the path. Apply the query to that path only
        Collect results and send back as a list of {path: results}, sql.columns
        This is more conformant with the current way paths are handled in the database
        """

        app.logger.debug("Starting query execution")
        # First create a dataset of results that are for the selected paths
        database = conn.sql(f"select * from {props.DB_INDEX_NAME} where "
                            f"filename in ({(', '.join('\'' + item + '\'' for item in path_keys))})")
        # Then layer the user supplied query over that. The query will run against the `database` relation that was
        # just created.
        sql = conn.sql(query)

        # Zip the results up into a JSON like data object
        results = []
        for entry in sql.fetchall():
            results.append(dict(zip(sql.columns, entry)))

        app.logger.debug("Completing query execution")
        # Return results
        return results, sql.columns
    finally:
        conn.close()


def _get_connection(database_path: Path, is_read_only=True):
    db_path = Path(database_path)
    db_file = db_path / props.DB_INDEX_FILE
    return duckdb.connect(str(db_file), read_only=is_read_only)


# query_index("/mnt/dev/testing/Medialib/test-db/", "select * from v_database where SourceFile ilike '%cara%'",
#             ['/mnt/dev/testing/Medialib/test-db/mnt__dev__testing__media.json',
#              '/mnt/dev/testing/Medialib/test-db/mnt__downloads__Downloads__Taking Cara Babies.json'])
