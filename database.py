import psycopg2
import streamlit as st

# Get connection info from Streamlit secrets
db_url = st.secrets["DB_URL"]

# Create tables only once using a temp connection
def initialize_db():
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cursor:
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

initialize_db()  # Run table creation at import


# Function to insert a new user
def insert_user(username, password):
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s)",
                    (username, password)
                )
            conn.commit()
    except psycopg2.IntegrityError:
        raise ValueError("Username is already taken!")
    except Exception as e:
        raise e


# Function to fetch user by username
def get_user_by_username(username):
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, password FROM users WHERE username = %s", (username,)
                )
                return cursor.fetchone()
    except Exception as e:
        print("Database error:", e)
        return None


# Function to insert a new expense
def insert_expense(user_id, amount, category, date, description):
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, amount, category, date, description)
                )
            conn.commit()
    except Exception as e:
        raise e


# Function to get expenses by user
def get_expenses_by_user(user_id):
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM expenses WHERE user_id = %s", (user_id,))
                return cursor.fetchall()
    except Exception as e:
        print("Error fetching expenses:", e)
        return []


# Function to get all users
def get_all_users():
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users")
                return cursor.fetchall()
    except Exception as e:
        print("Error fetching users:", e)
        return []
