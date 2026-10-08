import pyodbc
import urllib
from sqlalchemy import create_engine, text
import pandas as pd
from flask_login import UserMixin, LoginManager
from app.config import Config

login_manager = LoginManager()

def get_connection():
    """Get raw database connection"""
    db_params = (
        f"DRIVER={Config.DB_DRIVER};"
        f"SERVER={Config.DB_SERVER};"
        f"DATABASE={Config.DB_NAME};"
        f"UID={Config.DB_USER};"
        f"PWD={Config.DB_PASSWORD}"
    )
    return pyodbc.connect(db_params)

def get_engine():
    """Get SQLAlchemy engine"""
    db_params = (
        f"DRIVER={Config.DB_DRIVER};"
        f"SERVER={Config.DB_SERVER};"
        f"DATABASE={Config.DB_NAME};"
        f"UID={Config.DB_USER};"
        f"PWD={Config.DB_PASSWORD}"
    )
    quoted = urllib.parse.quote_plus(db_params)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quoted}")

def run_sql_query(sql_query: str) -> pd.DataFrame:
    """Execute SQL query and return DataFrame"""
    try:
        engine = get_engine()
        df = pd.read_sql(text(sql_query), engine)
        return df
    except Exception as e:
        raise Exception(f"SQL Query Error: {e}")

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

def is_connected() -> bool:
    """Check if DB connection is alive"""
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False
    
@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT id, userName FROM [user] WHERE id = ?"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return User(user[0], user[1])
        return None
    except Exception:
        return None