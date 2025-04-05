import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class PostgreSQLDatabase:
    def __init__(self, user="postgres", dbname="meudb", password="senha", host="localhost", port="5432"):
        self.user = user
        self.dbname = dbname
        self.password = password
        self.host = host
        self.port = port
        self.connection = None
        self.cursor = None
    
    def create_db(self):
        """
        Creates the database if it does not exist
        """
        conn = psycopg2.connect(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (self.dbname,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.dbname)))
            logging.info(f"Database '{self.dbname}' successfully created!")
        else:
            logging.error(f"Database '{self.dbname}' already exists.")
            
        cursor.close()
        conn.close()
    
    def connect_db(self):
        """
        Establishes connection to the database
        """
        try:
            self.connection = psycopg2.connect(
                user=self.user,
                dbname=self.dbname,
                password=self.password,
                host=self.host,
                port=self.port
            )
            self.cursor = self.connection.cursor()
            logging.info("Connection established successfully!")
            return True
        except Exception as e:
            logging.error(f"Error: {e}")
            return False
    
    def create_table(self, table_name, cols):
        """
        Creates a table in the database

        Args:
        table_name (str): Table name
        columns (str): Column definition in SQL format
        """
        try:
            self.cursor.execute(
                sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                    sql.Identifier(table_name),
                    sql.SQL(cols)
                )
            )
            self.connection.commit()
            logging.info(f"Table '{table_name}' created/verified successfully!")
        except Exception as e:
            logging.error(f"Error: {e}")
    
    def insert(self, table_name, data):
        """
        Inserts data into a table

        Args:
        table_name (str): Table name
        data (dict): Dictionary with the data to be inserted
        """
        colunas = list(data.keys())
        valores = list(data.values())
        placeholders = ', '.join(['%s'] * len(valores))
        
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(map(sql.Identifier, colunas)),
            sql.SQL(placeholders)
        )
        
        try:
            self.cursor.execute(query, valores)
            self.connection.commit()
            logging.info("Data inserted!")
        except Exception as e:
            logging.error(f"Insert Error: {e}")
    
    def read(self, table_name, cols="*", condition=None):
        """
        Query data from a table

        Args:
        table (str): Table name
        columns (str): Columns to be returned (default "*")
        condition (str): WHERE condition (optional)

        Returns:
        list: List with the query results
        """
        if isinstance(cols, list):
            colunas_sql = sql.SQL(', ').join(map(sql.Identifier, cols))
        else:
            colunas_sql = sql.SQL(cols)
            
        if condition:
            query = sql.SQL("SELECT {} FROM {} WHERE {}").format(
                colunas_sql,
                sql.Identifier(table_name),
                sql.SQL(condition)
            )
        else:
            query = sql.SQL("SELECT {} FROM {}").format(
                colunas_sql,
                sql.Identifier(table_name)
            )
            
        try:
            self.cursor.execute(query)
            logging.info("Query executed:\n")
            return self.cursor.fetchall()
        except Exception as e:
            logging.error(f"Error: {e}")
            return []
    
    def update_table(self, table_name, data, condition):
        """
        Updates data in a table

        Args:
        table (str): Table name
        data (dict): Dictionary with data to be updated
        condition (str): WHERE condition for update
        """
        set_items = []
        values = []
        
        for col, value in data.items():
            set_items.append(sql.SQL("{} = %s").format(sql.Identifier(col)))
            values.append(value)
            
        query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(set_items),
            sql.SQL(condition)
        )
        
        try:
            self.cursor.execute(query, values)
            self.connection.commit()
            logging.info(f"Updated: {self.cursor.rowcount} affected rows.")
        except Exception as e:
            logging.error(f"Error updating data: {e}")
    
    def delete(self, table_name, condition):
        """
        Deletes data from a table

        Args:
        table (str): Table name
        condition (str): WHERE condition for deletion
        """
        query = sql.SQL("DELETE FROM {} WHERE {}").format(
            sql.Identifier(table_name),
            sql.SQL(condition)
        )
        
        try:
            self.cursor.execute(query)
            self.connection.commit()
            logging.info(f"Deleted: {self.cursor.rowcount} affected rows.")
        except Exception as e:
            logging.error(f"Error deleting data: {e}")
    
    def close_db(self):
        """
        Close connection
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logging.info("Connection Closed.")

if __name__ == "__main__":
    PostgreSQLDatabase()