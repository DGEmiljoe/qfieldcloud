import logging
import os
from time import sleep, time

import psycopg2

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

TIMEOUT = 30
INTERVAL = 2


def wait_for_postgres():
    logger.info("Waiting for postgres...")
    config = {
        "dbname": os.environ.get("SQL_DATABASE"),
        "user": os.environ.get("SQL_USER"),
        "password": os.environ.get("SQL_PASSWORD"),
        "host": os.environ.get("SQL_HOST"),
        "port": os.environ.get("SQL_PORT"),
        "sslmode": os.environ.get("SQL_SSLMODE"),
    }
    start_time = time()
    while time() - start_time < TIMEOUT:
        try:
            conn = psycopg2.connect(**config)
            logger.info("Postgres is ready! ✨ 💅")
            conn.close()
            return True
        except psycopg2.OperationalError as e:
            logger.info(
                f"Postgres isn't ready.\n{e}\n Waiting for {INTERVAL} second(s)..."
            )
            sleep(INTERVAL)
    logger.error(f"We could not connect to Postgres within {TIMEOUT} seconds.")

    return False


wait_for_postgres()
