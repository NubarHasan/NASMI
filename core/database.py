from db.database import Database as Database


def get_db() -> Database:
    return Database()
