import sqlite3
import bcrypt

# Connect to database (or create it if it doesn't exist)
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Create expenses table
cursor.execute("""            
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    category TEXT,
    date TEXT,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

conn.commit()

def insert_user(username, password):
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
    conn.commit()


def get_user_by_username(username):
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    return cursor.fetchone()

def insert_expense(userId,amount,category,date,description):
    cursor.execute("INSERT INTO expenses (user_id,amount,category,date,description) VALUES (?, ?, ?, ?, ?)", (userId,amount,category,date,description))
    conn.commit()

def get_expenses_by_user(user_id):
    cursor.execute("SELECT * FROM expenses WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def get_all_users():
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()
