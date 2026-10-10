from sqlalchemy import text

import app.db.models
from app.db.base import Base
from app.db.session import engine


def initialize_database():
    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
        connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )

    Base.metadata.create_all(bind=engine)

    print("Database connection successful.")
    print("pgvector extension is enabled.")
    print("Tables are ready:")
    for table_name in sorted(Base.metadata.tables):
        print(f" - {table_name}")


if __name__ == "__main__":
    initialize_database()
