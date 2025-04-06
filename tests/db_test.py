import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from utils.db.crud import PostgreSQLDatabase
from config.project_constants import EnvVars
from config.project_constants import DatetimeFormats

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

def get_correct_datetimes():
    return DatetimeFormats.get_datetime()

def get_correct_datetimes_6m():
    return DatetimeFormats.get_datetime_plus_6_months()

def test_get_correct_datetimes():
    assert isinstance(get_correct_datetimes(), str)
    assert isinstance(get_correct_datetimes_6m(), str)