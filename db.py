import os
import psycopg2

print("DATABASE_URL =", os.environ.get("DATABASE_URL"))

def get_db():
    database_url = os.environ.get("Database_URL")
    
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")

    return psycopg2.connect(database_url)      
