import time
import random
import streamlit as st
import google.generativeai as genai
from db_helpers import get_db_connection

def get_available_models():
    """Fetches list of models from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM models ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_custom_model(name: str, provider: str, latency_multiplier: float) -> tuple:
    """Adds a custom model to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO models (name, provider, latency_multiplier, is_custom) VALUES (?, ?, ?, 1)",
            (name, provider, latency_multiplier)
        )
        conn.commit()
        return True, f"Model '{name}' added successfully."
    except Exception as e:
        return False, f"Failed to add model: {e}"
    finally:
        conn.close()

def generate_llm_response(prompt: str, model_name: str, api_key: str = None, system_instruction: str = None) -> tuple:
    """
    Generates content using Gemini API (if key provided and provider is Google)
    or returns high-quality mock responses.
    Returns (response_text, latency_ms).
    """
    start_time = time.time()
    
    # Resolve latency multiplier from database configuration
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT latency_multiplier FROM models WHERE name = ?", (model_name,))
    row = cursor.fetchone()
    multiplier = row['latency_multiplier'] if row else 1.0
    conn.close()
    
    # Check if we should call the real Gemini API
    is_gemini = "Gemini" in model_name
    
    if is_gemini and api_key:
        try:
            genai.configure(api_key=api_key)
            # Map friendly name to API name
            api_model_name = "gemini-1.5-flash"
            if "Pro" in model_name:
                api_model_name = "gemini-1.5-pro"
                
            model = genai.GenerativeModel(
                model_name=api_model_name,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            latency_ms = int((time.time() - start_time) * 1000)
            return response.text, latency_ms
        except Exception as e:
            # Fallback to mock on error but show a warning
            err_msg = str(e)
            st.sidebar.warning(f"Gemini API Error: {err_msg[:60]}... Falling back to Mock mode.")
    
    # Mock Response Generator (Smart Fallbacks)
    # Simulate API network delay based on the model's latency multiplier
    simulated_delay = random.uniform(0.8, 1.8) * multiplier
    time.sleep(simulated_delay)
    
    response_text = ""
    prompt_lower = prompt.lower()
    
    # Smart routing based on prompt subject
    if "explain" in prompt_lower and "error" in prompt_lower:
        # Code execution helper fallback
        response_text = f"""### AI Code Debugger Explanation ({model_name})

It looks like your code encountered a runtime/compilation error. Here is a breakdown of what happened:

1. **The Issue:** The interpreter/compiler was unable to execute the instructions due to a mismatch in variable references or syntax structure.
2. **Analysis:** The console output indicates an execution block failure.
3. **Corrected Code Solution:**
```python
# Here is the corrected version of the code with safety checks
def main():
    try:
        # Implemented correct logic
        print("Hello World!")
    except Exception as e:
        print(f"Error caught: {{e}}")

if __name__ == '__main__':
    main()
```
*Note: Make sure all variable types are cast properly before operations.*"""
        
    elif "interview" in prompt_lower or "question" in prompt_lower:
        if "aptitude" in prompt_lower:
            response_text = """Q1: Solve for x: 2x + 7 = 15.
Q2: A train travels at 60 km/h. How long does it take to cover 150 km?
Q3: If A completes a job in 4 days and B in 6 days, how long do they take together?"""
        else:
            response_text = """Q1: Explain the difference between '==' and '===' in JavaScript.
Q2: What is the Time Complexity of searching in a Hash Map on average?
Q3: Explain the concept of Inheritance in Object-Oriented Programming."""
            
    elif "grade" in prompt_lower or "score" in prompt_lower or "evaluate" in prompt_lower:
        response_text = """### Interview Performance Evaluation Report
**Overall Grade:** Good (B+)
**Scoring Summary:** 78/100

**Feedback Details:**
- **Strengths:** Demonstrates a solid understanding of fundamental computer science concepts, memory structures, and language-specific details.
- **Weaknesses:** Coding responses could benefit from more focus on edge cases, validation checks, and time complexity considerations.
- **Actionable Suggestions:** Practice writing clean error handling routines and study garbage collection algorithms."""
        
    elif "context" in prompt_lower or "document" in prompt_lower or "pdf" in prompt_lower:
        response_text = f"""Based on the provided document contexts, here is the answer:
The uploaded technical manual details that the system architecture is built around modular services connected by a message queue.

**Source References:**
- `document.pdf` (Paragraph 3): "...architected around modular services..."
- `document.pdf` (Paragraph 5): "...connected via a message bus broker..."

**Answer Confidence:** High (88%)"""
        
    else:
        # Standard chat mock response
        greetings = [
            f"Hello! I am your AI assistant running on {model_name}. How can I help you today?",
            f"Hi there! I am the {model_name} model. Feel free to ask me anything about coding or study documents.",
            f"Greetings! How can I assist you in your learning journey today? (Model: {model_name})"
        ]
        response_text = random.choice(greetings) + "\n\nHere are some things we can do:\n1. Upload and chat with PDF study guides.\n2. Write and execute code safely in the Playground.\n3. Run a mock technical interview and download a report."

    latency_ms = int((time.time() - start_time) * 1000)
    return response_text, latency_ms
