
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """
    Establish and return a PostgreSQL database connection.
    """

    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


if __name__ == "__main__":

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute("SELECT version();")
                version = cursor.fetchone()

                print("PostgreSQL connection successful!")
                print(version[0])

    except psycopg.Error as error:
        print("Database connection failed:")
        print(error)
