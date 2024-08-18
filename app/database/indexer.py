import os
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
    # Create a temporary database first
    temp_db = f"{str(_get_db_file(db_path))}.temp"
    # Perform Operation
    conn = duckdb.connect(temp_db, read_only=False)
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

    # Rename the file
    os.rename(temp_db, _get_db_file(db_path))

    return True


def query_index(database_path: str, query: str, path: str):
    """
    Queries the database at the supplied path with the query
    Args:
        database_path: The path to the database
        query: The query to run on the database
        path: The path within this database to restrict the search to

    Returns:
        The result of the query

    """
    db_file = _get_db_file(Path(database_path))
    conn = duckdb.connect(str(db_file), read_only=True)
    # https://duckdb.org/docs/api/python/relational_api
    # https://duckdb.org/docs/api/python/relational_api#sql-queries
    # https://duckdb.org/docs/api/c/replacement_scans.html
    try:
        """
        The database stores a field called `filename` which represents the json file from where each record was indexed.
        So, given a list of query paths, we first map these to the keys that would represent the filename of the json 
        file that stores data about the path in the database
        """
        app.logger.debug(f"Starting query execution for {path}")

        # First create a dataset of results that are for the selected paths
        database = conn.sql(f"select * from {props.DB_INDEX_NAME} where "
                            f"filename = \'{path}\'")
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


def _get_db_file(database_path: Path) -> Path:
    return database_path / props.DB_INDEX_FILE

# query_index("/mnt/dev/testing/Medialib/test-db/", "select * from v_database where SourceFile ilike '%cara%'",
#             ['/mnt/dev/testing/Medialib/test-db/mnt__dev__testing__media.json',
#              '/mnt/dev/testing/Medialib/test-db/mnt__downloads__Downloads__Taking Cara Babies.json'])
