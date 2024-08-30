import os
from pathlib import Path

import duckdb

import app
from app.collection import props


def create_index(collection_path: str):
    """
    Creates a duckDb index for the collection at the save path.
    Args:
        collection_path: The collection path

    Returns:
        True if the collection was indexed, false or ValueError otherwise
    """

    # Create a connection to the db file
    db_path = Path(collection_path)
    # Create a temporary collection first
    temp_db = f"{str(_get_db_file(db_path))}.temp"
    # Perform Operation
    conn = duckdb.connect(temp_db, read_only=False)
    try:
        db_data = db_path / "*.json"
        insert_stmt = (f"CREATE OR REPLACE TABLE {props.DB_INDEX_NAME} AS "
                       f"SELECT * FROM read_json('{db_data}', format='array', records=auto, filename=true)")
        # If this collection exists, there are already indexes on it. We first drop those
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


def query_index(collection_path: str, query: str, path: str):
    """
    Queries the collection at the supplied path with the query
    Args:
        collection_path: The path to the collection
        query: The query to run on the collection
        path: The path within this collection to restrict the search to

    Returns:
        The result of the query

    """
    db_file = _get_db_file(Path(collection_path))
    conn = duckdb.connect(str(db_file), read_only=True)
    # https://duckdb.org/docs/api/python/relational_api
    # https://duckdb.org/docs/api/python/relational_api#sql-queries
    # https://duckdb.org/docs/api/c/replacement_scans.html
    try:
        """
        The collection stores a field called `filename` which represents the json file from where each record was indexed.
        So, given a list of query paths, we first map these to the keys that would represent the filename of the json 
        file that stores data about the path in the collection
        """
        app.logger.debug(f"Starting query execution for {path}")

        # First create a dataset of results that are for the selected paths
        collection = conn.sql(f"select * from {props.DB_INDEX_NAME} where "
                              f"filename = \'{path}\'")
        # Then layer the user supplied query over that. The query will run against the `collection` relation that was
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


def _get_db_file(collection_path: Path) -> Path:
    return collection_path / props.DB_INDEX_FILE

# query_index("/mnt/dev/testing/Medialib/test-db/", "select * from v_collection where SourceFile ilike '%cara%'",
#             ['/mnt/dev/testing/Medialib/test-db/mnt__dev__testing__media.json',
#              '/mnt/dev/testing/Medialib/test-db/mnt__downloads__Downloads__Taking Cara Babies.json'])


create_index("/mnt/dev/testing/Medialib/threaded-scan/")
