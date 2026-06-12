import bcrypt
import re
import streamlit as st
from db_helpers import get_db_connection

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def register_user(username: str, email: str, password: str, role: str = "Student") -> tuple:
    """Registers a new user in the database. Returns (success_bool, message)."""
    # Validation
    if not username or not email or not password:
        return False, "All fields are required."
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
        
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "Invalid email address."
        
    if role not in ["Student", "Admin"]:
        return False, "Invalid role selected."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if username or email exists
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            return False, "Username or Email already exists."
            
        # Hash password
        pwd_hash = hash_password(password)
        
        # Insert user
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, subscription_status) VALUES (?, ?, ?, ?, 'free')",
            (username, email, pwd_hash, role)
        )
        user_id = cursor.lastrowid
        
        # Create an initial mock invoice for Free subscription
        import random
        inv_no = f"INV-FREE-{random.randint(100000, 999999)}"
        cursor.execute(
            "INSERT INTO subscriptions (user_id, plan_name, amount_paid, invoice_number) VALUES (?, 'Free Plan', 0.0, ?)",
            (user_id, inv_no)
        )
        
        conn.commit()
        return True, "Registration successful! You can now log in."
    except Exception as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

def authenticate_user(username_or_email: str, password: str) -> tuple:
    """Authenticates user credentials. Returns (user_dict, message) or (None, message)."""
    if not username_or_email or not password:
        return None, "Please enter both credentials."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Search by username or email
        cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?", 
            (username_or_email, username_or_email)
        )
        row = cursor.fetchone()
        
        if not row:
            return None, "Invalid username/email or password."
            
        user = dict(row)
        
        if verify_password(password, user['password_hash']):
            # Auth success, clean password hash from response
            del user['password_hash']
            return user, "Success"
        else:
            return None, "Invalid username/email or password."
    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        conn.close()

def update_user_queries(user_id: int, queries_used: int) -> bool:
    """Updates the count of queries used by a user today."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET queries_used_today = ? WHERE id = ?", (queries_used, user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def reset_daily_queries_if_new_day(user: dict) -> dict:
    """Resets daily queries count to 0 if the current date is different from the database last query date."""
    from datetime import date
    today_str = date.today().isoformat()
    
    if user['last_query_date'] != today_str:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET queries_used_today = 0, last_query_date = ? WHERE id = ?",
                (today_str, user['id'])
            )
            conn.commit()
            user['queries_used_today'] = 0
            user['last_query_date'] = today_str
        except Exception as e:
            print(f"Error resetting queries: {e}")
        finally:
            conn.close()
    return user

def render_login_register_ui():
    """Renders the login / register form interface inside the main page."""
    st.markdown("<h1 style='text-align: center; color: #6366f1;'>AI Learning Assistant Platform</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #a1a1aa;'>Welcome! Please log in or register to access the platform.</p>", unsafe_allow_html=True)
    
    # Render in a clean center column card
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["Login", "Register"])
        
        with tab_login:
            login_username = st.text_input("Username or Email", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_btn = st.button("Log In", use_container_width=True)
            
            if login_btn:
                user, msg = authenticate_user(login_username, login_password)
                if user:
                    # Successfully authenticated
                    user = reset_daily_queries_if_new_day(user)
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.success("Welcome back, {}!".format(user['username']))
                    st.rerun()
                else:
                    st.error(msg)
                    
        with tab_register:
            reg_username = st.text_input("Username", key="reg_username")
            reg_email = st.text_input("Email Address", key="reg_email")
            reg_password = st.text_input("Password (min. 6 characters)", type="password", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            # Select role
            reg_role = st.selectbox("Role", ["Student", "Admin"], index=0, key="reg_role")
            
            reg_btn = st.button("Register Account", use_container_width=True)
            
            if reg_btn:
                if reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    success, msg = register_user(reg_username, reg_email, reg_password, reg_role)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)
