import psycopg2
import streamlit as st

# Get connection info from Streamlit secrets
db_url = st.secrets["DB_URL"]

# Connect to Neon PostgreSQL
conn = psycopg2.connect(db_url)
cursor = conn.cursor()

# Create tables with password as BYTEA for storing hashed binary data
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    amount REAL,
    category TEXT,
    date TEXT,
    description TEXT
)
""")

conn.commit()

def insert_user(username, password):
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        raise  # or return a custom error message
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def get_user_by_username(username):
    cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
    return cursor.fetchone()

def insert_expense(user_id, amount, category, date, description):
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (%s, %s, %s, %s, %s)",
        (user_id, amount, category, date, description)
    )
    conn.commit()

def get_expenses_by_user(user_id):
    cursor.execute("SELECT * FROM expenses WHERE user_id = %s", (user_id,))
    return cursor.fetchall()

def get_all_users():
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()
