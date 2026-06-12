import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def get_db_connection():
    """Returns a SQLite connection. check_same_thread=False is needed for Streamlit's threading model."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates all tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users and Authentication (Task 1 & Task 9)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('Student', 'Admin')) DEFAULT 'Student',
        subscription_status TEXT CHECK(subscription_status IN ('free', 'premium')) DEFAULT 'free',
        queries_used_today INTEGER DEFAULT 0,
        last_query_date TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Chat History Management (Task 2)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        model TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        sender TEXT CHECK(sender IN ('user', 'ai')) NOT NULL,
        content TEXT NOT NULL,
        latency_ms INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    )
    """)
    
    # 3. PDF Knowledge Assistant (Task 3 & Task 4)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        size_bytes INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        chunk_text TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
    )
    """)
    
    # 4. Mock Interview Preparation (Task 6)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic TEXT NOT NULL,
        score INTEGER NOT NULL,
        feedback_json TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    # 5. Saved Code Snippets (Task 5)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS code_snippets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        language TEXT NOT NULL,
        code TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    # 6. Subscriptions & Billing (Task 9)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_name TEXT NOT NULL,
        amount_paid REAL NOT NULL,
        invoice_number TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    # Seed default models database if empty
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        provider TEXT NOT NULL,
        latency_multiplier REAL DEFAULT 1.0,
        is_custom INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Check if models are empty, if so, insert defaults
    cursor.execute("SELECT COUNT(*) FROM models")
    if cursor.fetchone()[0] == 0:
        models = [
            ("Gemini 1.5 Flash", "Google", 1.0, 0),
            ("Gemini 1.5 Pro", "Google", 2.2, 0),
            ("GPT-4o (Mock)", "OpenAI", 1.5, 0),
            ("Claude 3.5 Sonnet (Mock)", "Anthropic", 1.8, 0)
        ]
        cursor.executemany("INSERT INTO models (name, provider, latency_multiplier, is_custom) VALUES (?, ?, ?, ?)", models)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
