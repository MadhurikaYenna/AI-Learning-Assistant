import streamlit as st
import os
import json
import uuid
from datetime import date

# Import helpers
from db_helpers import init_db, get_db_connection
from auth_helpers import render_login_register_ui, update_user_queries
from models_helpers import get_available_models, generate_llm_response, add_custom_model
from rag_helpers import add_document, delete_document, get_user_documents, query_rag
from playground_helpers import run_code_safely, explain_code_error, save_code_snippet, get_code_snippets, delete_code_snippet
from interview_helpers import generate_interview_questions, evaluate_interview_answers, save_interview, get_user_interviews, generate_pdf_report
from voice_helpers import render_voice_assistant
from subscription_helpers import check_query_limit, increment_query_count, get_user_invoices, render_billing_checkout_ui
from analytics_helpers import render_admin_analytics_dashboard

# 1. Initialize Streamlit & Database
st.set_page_config(
    page_title="AI Learning Assistant Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database tables
init_db()

# 2. Inject Premium CSS Styles (Dark Theme, Glassmorphism, Rounded Panels)
custom_css = """
<style>
    /* Dark Theme Core Styles */
    .stApp {
        background-color: #0b0f19;
        color: #e4e4e7;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Header styling */
    .app-header {
        background: linear-gradient(90deg, #1e1b4b 0%, #311042 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
    }
    
    /* Glassmorphism card wrappers */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(16px);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
    }
    
    /* Login panel wrapper */
    .login-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(16px);
        border-radius: 16px;
        padding: 30px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 5px;
    }
    
    .badge-free {
        background-color: rgba(156, 163, 175, 0.2);
        color: #d1d5db;
        border: 1px solid rgba(156, 163, 175, 0.3);
    }
    
    .badge-premium {
        background-color: rgba(139, 92, 246, 0.2);
        color: #c084fc;
        border: 1px solid rgba(139, 92, 246, 0.4);
    }
    
    .badge-admin {
        background-color: rgba(239, 68, 68, 0.2);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0f172a;
    }
    ::-webkit-scrollbar-thumb {
        background: #334155;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #475569;
    }
    
    /* Chat bubbles */
    .chat-bubble {
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 12px;
        line-height: 1.5;
        max-width: 85%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
    }
    
    .chat-user {
        background-color: #312e81;
        border: 1px solid #4338ca;
        color: #ffffff;
        margin-left: auto;
    }
    
    .chat-ai {
        background-color: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.06);
        color: #e2e8f0;
        margin-right: auto;
    }
    
    .chat-meta {
        font-size: 0.72rem;
        color: #94a3b8;
        margin-top: 5px;
        display: flex;
        justify-content: space-between;
    }
    
    /* Console Terminal output styling */
    .terminal-console {
        background-color: #030712;
        color: #10b981;
        font-family: 'Courier New', Courier, monospace;
        padding: 15px;
        border-radius: 6px;
        border: 1px solid #1f2937;
        max-height: 300px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
    
    .terminal-console-error {
        color: #ef4444;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 3. Handle Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_conversation_id" not in st.session_state:
    st.session_state.selected_conversation_id = None
if "voice_input" not in st.session_state:
    st.session_state.voice_input = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# 4. Routing - Render login page if not authenticated
if not st.session_state.logged_in:
    render_login_register_ui()
    st.stop()

# Load user details
user = st.session_state.user

# 5. Header Component (Display User Info & Logout Button)
st.markdown(f"""
<div class="app-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin: 0; color: #a5b4fc; font-weight: 700;">🤖 AI Learning Assistant</h2>
            <span style="font-size: 0.85rem; color: #94a3b8;">Capstone Learning Ecosystem</span>
        </div>
        <div style="text-align: right; display: flex; align-items: center; gap: 15px;">
            <div style="line-height: 1.3;">
                <span style="font-size: 0.9rem; font-weight: 600; color: #e2e8f0;">{user['username']}</span><br>
                <span class="badge {'badge-admin' if user['role'] == 'Admin' else ('badge-premium' if user['subscription_status'] == 'premium' else 'badge-free')}">
                    {user['role']} | {user['subscription_status'].upper()}
                </span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar configurations
st.sidebar.markdown("### ⚙️ System Settings")
# Allow user to input custom Gemini API Key
api_key_input = st.sidebar.text_input("Google Gemini API Key", type="password", value=st.session_state.api_key)
if api_key_input != st.session_state.api_key:
    st.session_state.api_key = api_key_input
    
if not st.session_state.api_key:
    st.sidebar.warning("Running in **Mock Mode**. Provide a Gemini API Key to enable real LLM inference & RAG.")
else:
    st.sidebar.success("Gemini API Key loaded!")

# Models List
available_models = get_available_models()
model_names = [m['name'] for m in available_models]

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧭 Navigation")

# Sidebar navigation selection
nav_options = [
    "🏠 Dashboard & Info",
    "💬 AI Tutor Chat",
    "📚 PDF Knowledge Tutor",
    "💻 Code Playground",
    "🎯 Interview Prep Coach",
    "💳 Upgrades & Billing"
]

# Add Admin Dashboard option if user is an Admin
if user['role'] == 'Admin':
    nav_options.append("🔑 Administrator Panel")

selection = st.sidebar.radio("Go to:", nav_options)

# Add logout button at bottom of sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🔓 Sign Out", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.selected_conversation_id = None
    st.success("Successfully logged out.")
    st.rerun()

# ----------------- Navigation Views -----------------

# VIEW 1: STUDENT DASHBOARD
if selection == "🏠 Dashboard & Info":
    st.markdown("### Student Learning Dashboard")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### Welcome, {}!".format(user['username']))
        st.markdown("""
        Use the sidebar navigation to access all the platform features:
        - **AI Tutor Chat:** Ask questions, discuss technical topics, and utilize voice controls.
        - **PDF Knowledge Tutor:** Upload study guides, technical documentation, and perform localized search.
        - **Code Playground:** Code, debug, and run programs in JavaScript, Python, or Java safely.
        - **Interview Prep Coach:** Run a structured mock interview session and download a detailed score certificate PDF.
        """)
        
        # User details card
        st.markdown("---")
        st.markdown("**Your Profile Summary:**")
        st.markdown(f"- **Email Address:** {user['email']}")
        st.markdown(f"- **Role Privilege:** {user['role']}")
        st.markdown(f"- **Active Subscription Plan:** {user['subscription_status'].capitalize()} Tier")
        st.markdown(f"- **Registration Timestamp:** {user['created_at']}")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### Query Usage Stats")
        
        # Query usage logic
        allowed, limit, used = check_query_limit(user['id'])
        if limit == -1:
            st.success("∞ Unlimited queries active (Premium Tier)")
        else:
            pct = used / limit
            st.progress(pct)
            st.markdown(f"**Daily Limit:** {used} / {limit} queries used today")
            if used >= limit:
                st.error("⚠️ Limit reached! Upgrade to Premium in the billing tab for unlimited access.")
            else:
                st.info(f"You have {limit - used} queries left for today.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Documents quick count
        docs = get_user_documents(user['id'])
        snippets = get_code_snippets(user['id'])
        interviews = get_user_interviews(user['id'])
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### Resource Counts")
        st.markdown(f"📁 **PDF Documents:** {len(docs)} uploaded")
        st.markdown(f"💾 **Saved Code Snippets:** {len(snippets)} snippets")
        st.markdown(f"🏆 **Completed Interviews:** {len(interviews)} history sessions")
        st.markdown('</div>', unsafe_allow_html=True)


# VIEW 2: AI TUTOR CHAT
elif selection == "💬 AI Tutor Chat":
    st.markdown("### 💬 AI Tutor Chat & Voice Mentor")
    
    # Selected Model Dropdown
    selected_model = st.selectbox("Select AI Assistant Model", model_names, index=0)
    
    # Create sidebar-like interface inside Chat Tab
    chat_col1, chat_col2 = st.columns([1, 3])
    
    # 1. Past Conversations List Sidebar
    with chat_col1:
        st.markdown("#### Previous Chats")
        
        # Create new chat session button
        if st.button("➕ New Chat Session", use_container_width=True):
            conn = get_db_connection()
            cursor = conn.cursor()
            new_id = uuid.uuid4().hex
            cursor.execute(
                "INSERT INTO conversations (id, user_id, title, model) VALUES (?, ?, ?, ?)",
                (new_id, user['id'], "New Conversation", selected_model)
            )
            conn.commit()
            conn.close()
            st.session_state.selected_conversation_id = new_id
            st.rerun()
            
        # Search chats input
        search_query = st.text_input("🔍 Search Chat History", placeholder="Search keywords...")
        
        # Load and render conversations list
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if search_query:
            # Match conversations containing query in titles OR messages
            cursor.execute("""
                SELECT DISTINCT c.* FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = ? AND (c.title LIKE ? OR m.content LIKE ?)
                ORDER BY c.created_at DESC
            """, (user['id'], f"%{search_query}%", f"%{search_query}%"))
        else:
            cursor.execute("SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC", (user['id'],))
            
        convs = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        # Render lists
        st.markdown('<div style="max-height: 400px; overflow-y: auto;">', unsafe_allow_html=True)
        for c in convs:
            col_t, col_d = st.columns([4, 1])
            with col_t:
                active_style = "color: #818cf8; font-weight: 600;" if st.session_state.selected_conversation_id == c['id'] else ""
                if st.button(c['title'][:25] + ("..." if len(c['title']) > 25 else ""), key=f"cbtn_{c['id']}", use_container_width=True):
                    st.session_state.selected_conversation_id = c['id']
                    st.rerun()
            with col_d:
                if st.button("🗑️", key=f"cdel_{c['id']}"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM conversations WHERE id = ?", (c['id'],))
                    conn.commit()
                    conn.close()
                    if st.session_state.selected_conversation_id == c['id']:
                        st.session_state.selected_conversation_id = None
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. Active Chat Screen
    with chat_col2:
        active_id = st.session_state.selected_conversation_id
        
        if not active_id:
            st.info("👈 Select an existing chat session or start a new conversation to begin!")
            st.stop()
            
        # Load conversation info and message list
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (active_id,))
        conv_info = dict(cursor.fetchone())
        
        cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (active_id,))
        messages = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        st.markdown(f"**Chat Session:** `{conv_info['title']}` | **Model:** `{conv_info['model']}`")
        
        # Render message timeline
        st.markdown('<div style="min-height: 350px; max-height: 450px; overflow-y: auto; padding: 10px;">', unsafe_allow_html=True)
        for msg in messages:
            sender_class = "chat-user" if msg['sender'] == 'user' else "chat-ai"
            sender_label = "You" if msg['sender'] == 'user' else f"AI ({conv_info['model']})"
            latency_str = f"{msg['latency_ms']} ms" if msg['sender'] == 'ai' and msg['latency_ms'] > 0 else ""
            
            st.markdown(f"""
            <div class="chat-bubble {sender_class}">
                <strong>{sender_label}</strong><br>
                {msg['content']}
                <div class="chat-meta">
                    <span>{msg['timestamp']}</span>
                    <span>{latency_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Voice Assistant Iframe section
        st.markdown("---")
        last_ai_response = messages[-1]['content'] if (messages and messages[-1]['sender'] == 'ai') else ""
        
        # Render the browser-native iframe for Voice (Speech Recognition / TTS)
        st.markdown("##### 🎙️ Voice Controls")
        render_voice_assistant(speak_text=last_ai_response)
        
        # Audio input response capture
        # Custom HTML sends message via Streamlit value bridge. When updated, we capture it here.
        # Let's bind it using standard components value trigger.
        
        # Standard Text input field
        chat_prompt = st.chat_input("Ask your AI Tutor...")
        
        # If voice transcript is available and different, use it as prompt!
        # Note: In Streamlit, component value returns from the iframe which can be caught via standard return.
        # Let's support both.
        
        if chat_prompt:
            # Check limit
            allowed, limit, used = check_query_limit(user['id'])
            if not allowed:
                st.error("⚠️ Daily query limit reached (10/10). Please upgrade to Premium in the Upgrades tab to get unlimited queries.")
            else:
                with st.spinner("Thinking..."):
                    # Get response
                    api_key = st.session_state.api_key
                    ans, latency = generate_llm_response(chat_prompt, selected_model, api_key)
                    
                    # Save to DB
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Save User message
                    cursor.execute(
                        "INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'user', ?)",
                        (active_id, chat_prompt)
                    )
                    # Save AI message
                    cursor.execute(
                        "INSERT INTO messages (conversation_id, sender, content, latency_ms) VALUES (?, 'ai', ?, ?)",
                        (active_id, ans, latency)
                    )
                    
                    # Update conversation title if default
                    if conv_info['title'] == "New Conversation":
                        title_summary = chat_prompt[:30] + ("..." if len(chat_prompt) > 30 else "")
                        cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (title_summary, active_id))
                        
                    conn.commit()
                    conn.close()
                    
                    # Increment queries count
                    increment_query_count(user['id'], used)
                    st.rerun()


# VIEW 3: PDF KNOWLEDGE TUTOR (RAG)
elif selection == "📚 PDF Knowledge Tutor":
    st.markdown("### 📚 PDF Knowledge Assistant (RAG)")
    
    # Tab Layout
    tab_search, tab_manage = st.tabs(["🔍 Search & Ask Document", "📁 Manage Uploads"])
    
    with tab_manage:
        st.markdown("#### Upload PDF Study Materials")
        
        category = st.selectbox("Document Category", ["Computer Science", "Mathematics", "Aptitude", "Physics", "Chemistry", "General"])
        uploaded_files = st.file_uploader("Upload technical documents (PDF only)", type=["pdf"], accept_multiple_files=True)
        
        if uploaded_files:
            upload_btn = st.button("Extract and Index PDF Chunks", use_container_width=True)
            if upload_btn:
                for uf in uploaded_files:
                    with st.spinner(f"Parsing and indexing {uf.name}..."):
                        success, msg = add_document(user['id'], uf.name, uf.read(), category)
                        if success:
                            st.success(f"{uf.name}: {msg}")
                        else:
                            st.error(f"{uf.name}: {msg}")
                st.rerun()
                
        # List of current user uploads
        st.markdown("---")
        st.markdown("#### Uploaded Technical Library")
        docs = get_user_documents(user['id'])
        
        if not docs:
            st.info("No documents uploaded yet.")
        else:
            for d in docs:
                col_name, col_cat, col_size, col_date, col_act = st.columns([3, 2, 1, 2, 1])
                with col_name:
                    st.markdown(f"📄 **{d['filename']}**")
                with col_cat:
                    st.markdown(f"🏷️ `{d['category']}`")
                with col_size:
                    st.markdown(f"{round(d['size_bytes'] / 1024, 1)} KB")
                with col_date:
                    st.markdown(d['created_at'])
                with col_act:
                    if st.button("Delete 🗑️", key=f"ddel_{d['id']}"):
                        success, msg = delete_document(d['id'], user['id'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    with tab_search:
        st.markdown("#### Ask questions based on your PDFs")
        
        active_model = st.selectbox("Select Model for Answering", model_names, key="rag_model_select")
        query_input = st.text_input("Ask a question about uploaded content:", placeholder="What does the document say about...")
        
        search_btn = st.button("Search PDF Context & Generate Answer", use_container_width=True)
        
        if search_btn and query_input:
            allowed, limit, used = check_query_limit(user['id'])
            if not allowed:
                st.error("⚠️ Daily query limit reached. Please upgrade to Premium to execute document searches.")
            else:
                with st.spinner("Retrieving relevant context and generating response..."):
                    api_key = st.session_state.api_key
                    result = query_rag(user['id'], query_input, active_model, api_key)
                    
                    st.markdown("---")
                    # Display Answer
                    st.markdown("##### 📝 AI Tutor Answer:")
                    st.markdown(result['answer'])
                    
                    # Display stats
                    st.markdown("---")
                    st.markdown(f"**Confidence Score:** `{int(result['confidence'] * 100)}%` | **Response Latency:** `{result['latency_ms']} ms`")
                    
                    # Display source excerpts
                    if result['sources']:
                        st.markdown("##### 📚 Reference Chunks Extracted:")
                        for idx, src in enumerate(result['sources']):
                            with st.expander(f"Source {idx+1}: {src['filename']} (Match: {int(src['similarity']*100)}%)"):
                                st.markdown(f"*{src['excerpt']}*")
                                
                    # Increment queries count
                    increment_query_count(user['id'], used)


# VIEW 4: CODE PLAYGROUND
elif selection == "💻 Code Playground":
    st.markdown("### 💻 AI Coding Playground")
    
    pg_tab1, pg_tab2 = st.tabs(["📝 Code Editor", "💾 Saved Snippets"])
    
    with pg_tab1:
        play_model = st.selectbox("Select Assistant Model for Error Explanation", model_names, key="play_model")
        
        col_ed, col_con = st.columns([3, 2])
        
        with col_ed:
            lang = st.selectbox("Programming Language", ["Python", "JavaScript", "Java"])
            
            # Default code templates
            templates = {
                "Python": """# Write your Python 3.11 code here
def main():
    print("Running Python...")
    numbers = [1, 2, 3, 4, 5]
    squares = [n**2 for n in numbers]
    print(f"Squares list: {squares}")

if __name__ == "__main__":
    main()
""",
                "JavaScript": """// Write your Node.js code here
console.log("Running JavaScript...");
const numbers = [1, 2, 3, 4, 5];
const squares = numbers.map(n => n * n);
console.log("Squares list:", squares);
""",
                "Java": """// Write your Java code here. Include a public class.
public class Playground {
    public static void main(String[] args) {
        System.out.println("Running Java...");
        int[] numbers = {1, 2, 3, 4, 5};
        System.out.print("Squares list: [");
        for (int i = 0; i < numbers.length; i++) {
            System.out.print((numbers[i] * numbers[i]) + (i == numbers.length - 1 ? "" : ", "));
        }
        System.out.println("]");
    }
}
"""
            }
            
            # Store code in state so formatter/saving doesn't clear it
            if "editor_code" not in st.session_state:
                st.session_state.editor_code = templates[lang]
                
            # If language changed, reset template
            if "prev_lang" not in st.session_state or st.session_state.prev_lang != lang:
                st.session_state.editor_code = templates[lang]
                st.session_state.prev_lang = lang
                
            code_input = st.text_area("Source Code", value=st.session_state.editor_code, height=350, key="editor_textarea")
            st.session_state.editor_code = code_input
            
            col_btns = st.columns(3)
            with col_btns[0]:
                run_btn = st.button("🚀 Run Code", use_container_width=True)
            with col_btns[1]:
                # Format code logic (simplistic mock formatter or LLM assisted)
                fmt_btn = st.button("✨ Format Code", use_container_width=True)
            with col_btns[2]:
                save_title = st.text_input("Snippet Title", placeholder="My Code", label_visibility="collapsed")
                save_btn = st.button("💾 Save Snippet", use_container_width=True)
                
            if fmt_btn:
                # Format code
                with st.spinner("Formatting code..."):
                    # Use LLM to format/beautify code if API key exists, otherwise generic strip spacing
                    api_key = st.session_state.api_key
                    if api_key:
                        prompt = f"Format this {lang} code properly, maintain indentation and output ONLY the formatted code inside standard fences:\n\n{code_input}"
                        res, _ = generate_llm_response(prompt, play_model, api_key)
                        # Extract code from fence
                        fence_match = re.search(r"```[a-zA-Z]*\n(.*)```", res, re.DOTALL)
                        formatted_code = fence_match.group(1) if fence_match else res
                        st.session_state.editor_code = formatted_code.strip()
                        st.rerun()
                    else:
                        # Fallback basic strip
                        st.session_state.editor_code = code_input.strip()
                        st.success("Generic formatting complete (Mock).")
                        st.rerun()
                        
            if save_btn:
                if not save_title:
                    st.error("Please enter a title to save the snippet.")
                else:
                    success, msg = save_code_snippet(user['id'], save_title, lang, code_input)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                        
        with col_con:
            st.markdown("#### Output Console")
            
            if run_btn:
                with st.spinner("Compiling and executing code..."):
                    stdout, stderr, exit_code = run_code_safely(lang, code_input)
                    
                    st.session_state.sandbox_stdout = stdout
                    st.session_state.sandbox_stderr = stderr
                    st.session_state.sandbox_exit_code = exit_code
                    
            # Display output
            if "sandbox_exit_code" in st.session_state:
                stdout = st.session_state.sandbox_stdout
                stderr = st.session_state.sandbox_stderr
                exit_code = st.session_state.sandbox_exit_code
                
                st.markdown(f"**Exit Status:** `{exit_code}`")
                
                if stdout:
                    st.markdown("##### Standard Output:")
                    st.markdown(f'<div class="terminal-console">{stdout}</div>', unsafe_allow_html=True)
                    
                if stderr:
                    st.markdown("##### Standard Error:")
                    st.markdown(f'<div class="terminal-console terminal-console-error">{stderr}</div>', unsafe_allow_html=True)
                    
                    # Explain Error Button
                    st.markdown("---")
                    explain_btn = st.button("🤖 Explain Error with AI", use_container_width=True)
                    if explain_btn:
                        with st.spinner("AI analyzing compiler diagnostics..."):
                            api_key = st.session_state.api_key
                            exp, _ = explain_code_error(code_input, lang, stderr, play_model, api_key)
                            st.markdown("##### Debugger Explanation:")
                            st.markdown(exp)
            else:
                st.info("Console ready. Click 'Run Code' to compile and see output.")

    with pg_tab2:
        st.markdown("#### Your Saved Snippets")
        snippets = get_code_snippets(user['id'])
        
        if not snippets:
            st.info("No saved snippets found.")
        else:
            for s in snippets:
                with st.expander(f"💾 {s['title']} ({s['language']}) - {s['created_at']}"):
                    st.code(s['code'], language=s['language'].lower())
                    col_load, col_del = st.columns(2)
                    with col_load:
                        if st.button("Load into Editor", key=f"sload_{s['id']}", use_container_width=True):
                            st.session_state.editor_code = s['code']
                            st.session_state.prev_lang = s['language']
                            st.success("Loaded!")
                            st.rerun()
                    with col_del:
                        if st.button("Delete Snippet", key=f"sdel_{s['id']}", use_container_width=True):
                            success, msg = delete_code_snippet(s['id'], user['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)


# VIEW 5: MOCK INTERVIEW COACH
elif selection == "🎯 Interview Prep Coach":
    st.markdown("### 🎯 AI Interview Preparation Coach")
    
    int_tab1, int_tab2 = st.tabs(["📝 Mock Interview Screen", "📊 Performance History"])
    
    with int_tab1:
        # Session State for Interviews
        if "interview_active" not in st.session_state:
            st.session_state.interview_active = False
        if "interview_questions" not in st.session_state:
            st.session_state.interview_questions = []
        if "interview_answers" not in st.session_state:
            st.session_state.interview_answers = {}
        if "interview_current_idx" not in st.session_state:
            st.session_state.interview_current_idx = 0
        if "interview_topic" not in st.session_state:
            st.session_state.interview_topic = ""
            
        if not st.session_state.interview_active:
            # Interview Setup View
            st.markdown("#### Configure Mock Recruiter Settings")
            col_setup1, col_setup2 = st.columns(2)
            with col_setup1:
                topic = st.selectbox("Interview Technical Topic", ["Python", "Java", "Web Development", "Databases", "Aptitude"])
                difficulty = st.selectbox("Difficulty Tier", ["Beginner", "Intermediate", "Advanced"])
            with col_setup2:
                num_q = st.slider("Number of Questions", min_value=1, max_value=5, value=3)
                int_model = st.selectbox("Recruiter Model", model_names, key="int_model")
                
            start_int_btn = st.button("Start Mock Recruiter Interview", use_container_width=True)
            
            if start_int_btn:
                with st.spinner("Generating interview questions..."):
                    api_key = st.session_state.api_key
                    questions = generate_interview_questions(topic, difficulty, num_q, int_model, api_key)
                    
                    st.session_state.interview_questions = questions
                    st.session_state.interview_answers = {}
                    st.session_state.interview_current_idx = 0
                    st.session_state.interview_topic = topic
                    st.session_state.interview_active = True
                    st.session_state.int_eval_model = int_model
                    st.rerun()
        else:
            # Active Interview Q&A View
            topic = st.session_state.interview_topic
            questions = st.session_state.interview_questions
            curr_idx = st.session_state.interview_current_idx
            
            st.markdown(f"**Interview Topic:** `{topic}` | **Question:** `{curr_idx + 1} of {len(questions)}`")
            st.progress((curr_idx) / len(questions))
            
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid #6366f1;">
                <h5 style="margin: 0 0 10px 0; color: #a5b4fc;">Question:</h5>
                <p style="font-size: 1.1rem; margin: 0;">{questions[curr_idx]}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Answer input
            ans_key = f"ans_input_{curr_idx}"
            user_ans = st.text_area("Your Response Answer:", placeholder="Type your detailed answer here...", key=ans_key)
            
            col_nav1, col_nav2 = st.columns(2)
            with col_nav1:
                if curr_idx > 0:
                    if st.button("⬅️ Previous Question"):
                        st.session_state.interview_current_idx -= 1
                        st.rerun()
            with col_nav2:
                is_last = (curr_idx == len(questions) - 1)
                btn_label = "Complete Interview 🏁" if is_last else "Next Question ➡️"
                
                if st.button(btn_label):
                    st.session_state.interview_answers[curr_idx] = user_ans
                    
                    if is_last:
                        # Grade interview
                        with st.spinner("AI evaluating responses and scoring feedback..."):
                            # Format QA
                            qa_pairs = []
                            for idx, q in enumerate(questions):
                                qa_pairs.append({
                                    "question": q,
                                    "answer": st.session_state.interview_answers.get(idx, "")
                                })
                                
                            api_key = st.session_state.api_key
                            score, feedback = evaluate_interview_answers(topic, qa_pairs, st.session_state.int_eval_model, api_key)
                            
                            # Save to Database
                            save_interview(user['id'], topic, score, feedback)
                            
                            # Save evaluation to local state to render results
                            st.session_state.last_interview_results = {
                                "topic": topic,
                                "score": score,
                                "feedback": feedback,
                                "qa": qa_pairs
                            }
                            st.session_state.interview_active = False
                            st.rerun()
                    else:
                        st.session_state.interview_current_idx += 1
                        st.rerun()
                        
            # Cancel interview button
            if st.button("❌ Quit Interview"):
                st.session_state.interview_active = False
                st.rerun()
                
        # Renders evaluation summary if interview just finished
        if "last_interview_results" in st.session_state:
            res = st.session_state.last_interview_results
            st.markdown("---")
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(f"#### 🏆 Interview Performance Summary: `{res['topic']}`")
            
            col_s1, col_s2 = st.columns([1, 3])
            with col_s1:
                st.metric("Overall Score", f"{res['score']} / 100")
            with col_s2:
                st.markdown(f"**Strengths:** {res['feedback']['strengths']}")
                st.markdown(f"**Weaknesses:** {res['feedback']['weaknesses']}")
                st.markdown(f"**Suggestions:** {res['feedback']['suggestions']}")
                
            # Compile PDF and provide download button
            pdf_bytes = generate_pdf_report(user['username'], res['topic'], res['score'], res['qa'], res['feedback'])
            
            st.download_button(
                label="📥 Download Performance Certificate PDF",
                data=pdf_bytes,
                file_name=f"Interview_Report_{res['topic']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

    with int_tab2:
        st.markdown("#### Your Past Mock Recruiter Ratings")
        history = get_user_interviews(user['id'])
        
        if not history:
            st.info("You haven't completed any mock interviews yet.")
        else:
            for h in history:
                with st.expander(f"🏆 {h['topic']} Interview - Score: {h['score']}/100 ({h['created_at']})"):
                    st.markdown(f"**Strengths:** {h['feedback'].get('strengths', 'N/A')}")
                    st.markdown(f"**Weaknesses:** {h['feedback'].get('weaknesses', 'N/A')}")
                    st.markdown(f"**Suggestions:** {h['feedback'].get('suggestions', 'N/A')}")


# VIEW 6: UPGRADES & BILLING
elif selection == "💳 Upgrades & Billing":
    st.markdown("### 💳 Subscription Management & Billing")
    
    bill_tab1, bill_tab2 = st.tabs(["🔒 Subscription Plans", "🧾 Invoices history"])
    
    with bill_tab1:
        # Check current plan
        if user['subscription_status'] == 'premium':
            st.success("🎉 You are currently a **PREMIUM** tier subscriber. You have unlimited queries and full features.")
        else:
            render_billing_checkout_ui(user)
            
    with bill_tab2:
        st.markdown("#### Transaction Invoice Receipts")
        invoices = get_user_invoices(user['id'])
        
        if not invoices:
            st.info("No invoice logs found.")
        else:
            for idx, inv in enumerate(invoices):
                col_inv_t, col_inv_n, col_inv_a, col_inv_d = st.columns(4)
                with col_inv_t:
                    st.markdown(f"🧾 **{inv['plan_name']}**")
                with col_inv_n:
                    st.markdown(f"`{inv['invoice_number']}`")
                with col_inv_a:
                    st.markdown(f"${inv['amount_paid']}")
                with col_inv_d:
                    st.markdown(inv['created_at'])


# VIEW 7: ADMINISTRATOR DASHBOARD
elif selection == "🔑 Administrator Panel" and user['role'] == 'Admin':
    st.markdown("### 🔑 Administrator Analytics & Diagnostics Dashboard")
    
    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["📊 Global Usage Charts", "🔌 Model Integrations", "💻 SQL Database Diagnostics"])
    
    with admin_tab1:
        # Call Plotly layout
        render_admin_analytics_dashboard()
        
    with admin_tab2:
        st.markdown("#### Register a new LLM provider model")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_name = st.text_input("Model Name", placeholder="e.g. GPT-5 (Mock)")
            m_prov = st.selectbox("LLM Provider", ["Google", "OpenAI", "Anthropic", "Custom"])
        with col_m2:
            m_mult = st.number_input("Response Latency Multiplier (Simulated delay factor)", min_value=0.1, max_value=5.0, value=1.0)
            
        add_m_btn = st.button("Register Model", use_container_width=True)
        if add_m_btn:
            if not m_name:
                st.error("Please provide a model name.")
            else:
                success, msg = add_custom_model(m_name, m_prov, m_mult)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
        # List of models
        st.markdown("---")
        st.markdown("#### Registered System Models")
        for m in get_available_models():
            st.markdown(f"- 🔌 **{m['name']}** (Provider: `{m['provider']}`, Latency factor: `{m['latency_multiplier']}x` - Custom: `{'Yes' if m['is_custom'] else 'No'}`) ")

    with admin_tab3:
        st.markdown("#### Execute Direct SQLite Query (Safety Mode)")
        sql_input = st.text_area("SQL Statement", placeholder="SELECT * FROM users LIMIT 10;")
        
        run_sql_btn = st.button("Run SQL Command", use_container_width=True)
        
        if run_sql_btn and sql_input:
            # Basic validation restrict modifications
            sql_lower = sql_input.lower().strip()
            # We restrict deleting critical schema tables, but allow standard diagnostics queries
            if "drop" in sql_lower:
                st.error("❌ DROP operations are restricted for safety.")
            else:
                conn = get_db_connection()
                try:
                    import pandas as pd
                    # Run query using pandas for easy rendering
                    df_res = pd.read_sql_query(sql_input, conn)
                    st.dataframe(df_res, use_container_width=True)
                    st.success(f"Query returned {len(df_res)} rows.")
                except Exception as sqle:
                    st.error(f"SQL Execution Error: {sqle}")
                finally:
                    conn.close()
