from sqlalchemy import text

from database.session import engine

try:
    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT current_database(), current_user")
        )

        print("SQLAlchemy connection successful!")
        print(result.fetchone())

except Exception as error:
    print("SQLAlchemy connection failed:")
    print(error)

finally:
    engine.dispose()