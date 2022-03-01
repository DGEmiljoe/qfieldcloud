import logging
import os
from time import sleep, time

import psycopg2
import redis

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


def wait_for_redis():
    logger.info("Waiting for redis...")
    start_time = time()
    while time() - start_time < TIMEOUT:
        logger.info("Waiting for redis...")
        try:
            r = redis.Redis(
                host="redis", password=os.environ.get("REDIS_PASSWORD"), db=0
            )
            if not r.ping():
                raise Exception
            logger.info("Redis is ready! ✨ 💅")
            return True
        except Exception as e:
            logger.info("Redis isn't ready.\n%s" % e)
        sleep(INTERVAL)

    return False


wait_for_redis()
