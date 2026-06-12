import random
import streamlit as st
from db_helpers import get_db_connection

FREE_DAILY_LIMIT = 10

def check_query_limit(user_id: int) -> tuple:
    """
    Checks if a user is within their daily query limit.
    Returns (is_allowed, limit_number, used_today).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, subscription_status, queries_used_today FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False, 0, 0
        
    role, sub_status, used_today = row['role'], row['subscription_status'], row['queries_used_today']
    
    # Admins and Premium users have unlimited queries
    if role == 'Admin' or sub_status == 'premium':
        return True, -1, used_today
        
    # Free users have a strict daily limit
    if used_today >= FREE_DAILY_LIMIT:
        return False, FREE_DAILY_LIMIT, used_today
        
    return True, FREE_DAILY_LIMIT, used_today

def increment_query_count(user_id: int, current_used: int) -> bool:
    """Increments the query usage counter for a user in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        from datetime import date
        today_str = date.today().isoformat()
        cursor.execute(
            "UPDATE users SET queries_used_today = ?, last_query_date = ? WHERE id = ?",
            (current_used + 1, today_str, user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error incrementing queries: {e}")
        return False
    finally:
        conn.close()

def upgrade_to_premium(user_id: int) -> tuple:
    """Upgrades user to Premium tier and generates a mock invoice."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if already premium
        cursor.execute("SELECT subscription_status FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row['subscription_status'] == 'premium':
            conn.close()
            return False, "Already on Premium Plan.", None
            
        inv_no = f"INV-PREM-{random.randint(100000, 999999)}"
        amount = 19.99
        
        # Update user plan
        cursor.execute("UPDATE users SET subscription_status = 'premium' WHERE id = ?", (user_id,))
        
        # Save subscription log
        cursor.execute(
            "INSERT INTO subscriptions (user_id, plan_name, amount_paid, invoice_number) VALUES (?, 'Premium Plan', ?, ?)",
            (user_id, amount, inv_no)
        )
        
        conn.commit()
        return True, "Successfully upgraded to Premium Plan!", inv_no
    except Exception as e:
        return False, f"Failed to upgrade: {str(e)}", None
    finally:
        conn.close()

def get_user_invoices(user_id: int) -> list:
    """Retrieves all invoices for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def render_billing_checkout_ui(user: dict):
    """Renders a payment simulation checkout form in Streamlit."""
    st.markdown("### Upgrade to Premium Plan")
    st.markdown("""
    🚀 **Unlock full learning capabilities:**
    - **Unlimited queries** to AI chat & document tutors.
    - **Multi-document support** (upload multiple files simultaneously).
    - **Coding playground** execution features.
    - **Advanced LLMs** like Gemini 1.5 Pro.
    - **PDF certificate reports** for mock interview preparation.
    """)
    
    st.markdown('<div class="payment-card">', unsafe_allow_html=True)
    st.info("💳 Premium Subscription Plan: **$19.99 / Month**")
    
    col1, col2 = st.columns(2)
    with col1:
        card_name = st.text_input("Name on Card", placeholder="John Doe")
        card_num = st.text_input("Card Number", placeholder="1234 5678 1234 5678", max_chars=19)
    with col2:
        card_exp = st.text_input("Expiry Date", placeholder="MM/YY", max_chars=5)
        card_cvc = st.text_input("CVC", type="password", placeholder="123", max_chars=3)
        
    pay_btn = st.button("Complete Payment", use_container_width=True)
    
    if pay_btn:
        # Standard validation checks
        import re
        clean_card = re.sub(r'\s+', '', card_num)
        
        if not card_name or not card_num or not card_exp or not card_cvc:
            st.error("All billing fields are required.")
        elif not clean_card.isdigit() or len(clean_card) < 13:
            st.error("Please enter a valid credit card number.")
        elif not re.match(r'^(0[1-9]|1[0-2])\/?([0-9]{2})$', card_exp):
            st.error("Please enter a valid expiry date (MM/YY).")
        elif not card_cvc.isdigit() or len(card_cvc) != 3:
            st.error("Please enter a valid 3-digit CVC.")
        else:
            with st.spinner("Processing transaction..."):
                import time
                time.sleep(1.5)
                success, msg, inv_no = upgrade_to_premium(user['id'])
                if success:
                    st.success(f"Payment successful! Invoice: {inv_no}")
                    # Update local user state
                    user['subscription_status'] = 'premium'
                    st.session_state.user = user
                    time.sleep(1.0)
                    st.rerun()
                else:
                    st.error(msg)
    st.markdown('</div>', unsafe_allow_html=True)
