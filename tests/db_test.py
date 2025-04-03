import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from utils.db.crud import PostgreSQLDatabase
from config.constants import EnvVars

env = EnvVars()
db_password = env.get_var("DB_PASSWORD")

db = PostgreSQLDatabase(
    user="juanml",
    dbname="churnml",
    password=db_password,
    host="localhost",
    port="5432"
)

def connect_db():
    return db.connect_db()

def test_db_connection():
    assert connect_db() == True