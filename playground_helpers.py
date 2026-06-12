import os
import re
import uuid
import subprocess
import shutil
from db_helpers import get_db_connection
from models_helpers import generate_llm_response

PLAYGROUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_playground")

def prepare_dir():
    if not os.path.exists(PLAYGROUND_DIR):
        os.makedirs(PLAYGROUND_DIR)

def clean_dir():
    if os.path.exists(PLAYGROUND_DIR):
        try:
            shutil.rmtree(PLAYGROUND_DIR)
        except Exception as e:
            print(f"Error cleaning playground: {e}")

def run_code_safely(language: str, code: str) -> tuple:
    """
    Executes Python, JS, or Java code inside a subprocess.
    Returns (stdout, stderr, exit_code).
    """
    prepare_dir()
    unique_id = uuid.uuid4().hex
    
    # Defaults
    stdout, stderr = "", ""
    exit_code = 0
    timeout_limit = 5.0 # seconds
    
    try:
        if language.lower() == "python":
            filepath = os.path.join(PLAYGROUND_DIR, f"script_{unique_id}.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Execute python script
            proc = subprocess.run(
                ["python", filepath],
                capture_output=True,
                text=True,
                timeout=timeout_limit
            )
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
            
        elif language.lower() == "javascript":
            filepath = os.path.join(PLAYGROUND_DIR, f"script_{unique_id}.js")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Execute node script
            proc = subprocess.run(
                ["node", filepath],
                capture_output=True,
                text=True,
                timeout=timeout_limit
            )
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
            
        elif language.lower() == "java":
            # Extract public class name or default to Playground
            match = re.search(r"public\s+class\s+([a-zA-Z0-9_]+)", code)
            class_name = match.group(1) if match else f"Playground_{unique_id}"
            
            # Replace class name in code if it was not found, to match file name
            if not match:
                # Replace standard "class Playground" with the unique one
                if "class Playground" in code:
                    code = code.replace("class Playground", f"class Playground_{unique_id}")
                else:
                    # Append class wrapper around code if it looks like code block
                    code = f"public class {class_name} {{\n    public static void main(String[] args) {{\n        {code}\n    }}\n}}"
            
            # Save file
            filepath = os.path.join(PLAYGROUND_DIR, f"{class_name}.java")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
                
            # Compile Java code
            compile_proc = subprocess.run(
                ["javac", filepath],
                capture_output=True,
                text=True,
                timeout=timeout_limit
            )
            
            if compile_proc.returncode != 0:
                stdout = ""
                stderr = f"Compilation Error:\n{compile_proc.stderr}"
                exit_code = compile_proc.returncode
            else:
                # Execute compiled Java code (must run from the directory containing class file)
                run_proc = subprocess.run(
                    ["java", "-cp", PLAYGROUND_DIR, class_name],
                    capture_output=True,
                    text=True,
                    timeout=timeout_limit
                )
                stdout = run_proc.stdout
                stderr = run_proc.stderr
                exit_code = run_proc.returncode
        else:
            return "", "Unsupported language selected.", 1
            
    except subprocess.TimeoutExpired:
        stdout = ""
        stderr = f"Execution Timeout: Code execution exceeded the {timeout_limit} second time limit."
        exit_code = -1
    except Exception as e:
        stdout = ""
        stderr = f"System error executing code: {str(e)}"
        exit_code = -2
    finally:
        clean_dir()
        
    return stdout, stderr, exit_code

def explain_code_error(code: str, language: str, stderr: str, model_name: str, api_key: str = None) -> tuple:
    """Uses the LLM helper to explain coding playground errors."""
    prompt = f"""You are an expert AI Coding Coach. A student's code failed with an execution error.
Please analyze their code and explain why it failed. Then, provide the corrected code block.

LANGUAGE: {language}

STUDENT'S CODE:
```
{code}
```

CONSOLE ERROR OUTPUT:
```
{stderr}
```

Provide a friendly, educational explanation of the error, followed by the complete corrected code:"""

    system_instruction = "You are a coding tutor. Analyze coding playground errors, explain them, and suggest fixes in formatted markdown blocks."
    explanation, latency = generate_llm_response(prompt, model_name, api_key, system_instruction)
    return explanation, latency

def save_code_snippet(user_id: int, title: str, language: str, code: str) -> tuple:
    """Saves a code snippet to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO code_snippets (user_id, title, language, code) VALUES (?, ?, ?, ?)",
            (user_id, title, language, code)
        )
        conn.commit()
        return True, "Snippet saved successfully!"
    except Exception as e:
        return False, f"Failed to save snippet: {e}"
    finally:
        conn.close()

def get_code_snippets(user_id: int) -> list:
    """Fetches all code snippets saved by a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM code_snippets WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_code_snippet(snippet_id: int, user_id: int) -> tuple:
    """Deletes a code snippet."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM code_snippets WHERE id = ? AND user_id = ?", (snippet_id, user_id))
        conn.commit()
        return True, "Snippet deleted successfully."
    except Exception as e:
        return False, f"Failed to delete: {e}"
    finally:
        conn.close()
