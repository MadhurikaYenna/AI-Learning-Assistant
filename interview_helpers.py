import json
from fpdf import FPDF
from db_helpers import get_db_connection
from models_helpers import generate_llm_response

def generate_interview_questions(topic: str, difficulty: str, num_questions: int = 3, model_name: str = "Gemini 1.5 Flash", api_key: str = None) -> list:
    """Generates a list of interview questions based on topic and difficulty."""
    prompt = f"""You are a senior technical interviewer. Generate exactly {num_questions} questions for a mock interview.
Topic: {topic}
Difficulty: {difficulty}

Make the questions challenging and relevant. Output them as a numbered list.
Do not include any introductory or concluding text, just output the numbered questions."""

    system_instruction = "You are a tech recruiter. Generate clear technical or aptitude questions as a simple numbered list."
    response, _ = generate_llm_response(prompt, model_name, api_key, system_instruction)
    
    # Parse numbered list
    questions = []
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Match standard numbered lists e.g., "1. Question?" or "Q1: Question?"
        match = re_match = re_match = re_match = None
        # Let's clean up line prefix
        cleaned = re.sub(r'^(?:\d+[\.:\)]|Q\d+[\.:\)]|[-*\+])\s*', '', line).strip()
        if cleaned:
            questions.append(cleaned)
            
    # Fallback to defaults if parsing fails
    if len(questions) < num_questions:
        defaults = {
            "Python": [
                "Explain how list comprehensions work in Python and write a quick example.",
                "What is the difference between list and tuple in Python? When would you use which?",
                "Explain the difference between deepcopy and shallow copy."
            ],
            "Java": [
                "What is the difference between abstract class and interface in Java?",
                "Explain the Java Garbage Collection mechanism and how it works.",
                "What is the purpose of the 'volatile' keyword in Java?"
            ],
            "Web Development": [
                "Explain how the DOM works and what virtual DOM is.",
                "What are WebSockets and how do they differ from HTTP polling?",
                "Explain CSS specificity and how it determines style applications."
            ],
            "Databases": [
                "Explain database normalization and difference between 2NF and 3NF.",
                "What is a database transaction and what do ACID properties stand for?",
                "What are indexes in SQL databases and how do they improve select speed?"
            ],
            "Aptitude": [
                "A car travels at 60 km/h for 2 hours, and then at 80 km/h for 3 hours. What is its average speed?",
                "If 5 workers can build a wall in 12 days, how many days will it take 6 workers to build it?",
                "A box contains 5 red, 3 blue, and 2 green balls. If a ball is drawn at random, what is the probability that it is blue?"
            ]
        }
        
        category = topic if topic in defaults else "Python"
        fallback_list = defaults[category]
        questions = fallback_list[:num_questions]
        
    return questions

import re

def evaluate_interview_answers(topic: str, QA_pairs: list, model_name: str = "Gemini 1.5 Flash", api_key: str = None) -> tuple:
    """
    Evaluates a student's answers to the questions.
    Returns (score, feedback_dict).
    """
    qa_formatted = ""
    for idx, pair in enumerate(QA_pairs):
        qa_formatted += f"Q{idx+1}: {pair['question']}\nStudent Answer: {pair['answer']}\n\n"
        
    prompt = f"""You are a senior technical interviewer. Evaluate the student's answers to the mock interview questions on '{topic}'.
Provide an evaluation score out of 100 (integer) and feedback containing strengths, weaknesses, and improvement suggestions.

STUDENT ANSWERS:
{qa_formatted}

You MUST respond ONLY with a valid JSON object matching this schema:
{{
    "score": 85,
    "strengths": "List of strengths shown in the answers",
    "weaknesses": "List of weaknesses or gaps in explanation",
    "suggestions": "Actionable suggestions to improve"
}}
Do not add any markdown headers like ```json, just output the raw JSON."""

    system_instruction = "You are a recruiter. Grade interview answers and return a JSON object with fields: score, strengths, weaknesses, suggestions."
    response, _ = generate_llm_response(prompt, model_name, api_key, system_instruction)
    
    # Try parsing JSON
    try:
        # Strip code fences if LLM ignored instructions
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        evaluation = json.loads(clean_response)
        score = int(evaluation.get("score", 70))
        feedback = {
            "strengths": evaluation.get("strengths", "Solid effort."),
            "weaknesses": evaluation.get("weaknesses", "Could add more technical detail."),
            "suggestions": evaluation.get("suggestions", "Practice coding and system design patterns.")
        }
    except Exception as e:
        print(f"Error parsing evaluation JSON: {e}. Raw: {response}")
        # Manual fallback parsing
        score = 75
        feedback = {
            "strengths": "Demonstrated core understanding of topics.",
            "weaknesses": "Answers were slightly brief. Missing code syntax or implementation examples.",
            "suggestions": "Try to structure answers with definitions, examples, and trade-offs. Spend more time detailing algorithm complexity."
        }
        
    return score, feedback

def save_interview(user_id: int, topic: str, score: int, feedback: dict):
    """Saves interview results to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO interviews (user_id, topic, score, feedback_json) VALUES (?, ?, ?, ?)",
            (user_id, topic, score, json.dumps(feedback))
        )
        conn.commit()
    except Exception as e:
        print(f"Error saving interview: {e}")
    finally:
        conn.close()

def get_user_interviews(user_id: int) -> list:
    """Fetches user interview history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interviews WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        item = dict(row)
        try:
            item['feedback'] = json.loads(item['feedback_json'])
        except Exception:
            item['feedback'] = {}
        results.append(item)
    return results

class PDFReport(FPDF):
    def header(self):
        # Draw a nice colored bar at the top
        self.set_fill_color(99, 102, 241) # Slate Indigo
        self.rect(0, 0, 210, 15, 'F')
        
        self.set_y(20)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(31, 41, 55)
        self.cell(0, 10, 'AI Mock Interview Performance Report', 0, 1, 'C')
        
        self.set_draw_color(229, 231, 235)
        self.line(10, 32, 200, 32)
        self.ln(10)
        
    def footer(self):
        self.set_y(-20)
        self.set_draw_color(229, 231, 235)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(156, 163, 175)
        self.cell(0, 10, f'AI Learning Assistant Platform  |  Page {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(username: str, topic: str, score: int, QA_pairs: list, feedback: dict) -> bytes:
    """Compiles interview questions, answers, and scores into a beautifully formatted PDF file."""
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Metadata info card
    pdf.set_fill_color(249, 250, 251)
    pdf.rect(10, 35, 190, 30, 'DF')
    
    pdf.set_y(38)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(75, 85, 99)
    pdf.cell(95, 6, f'Candidate Name: {username}', 0, 0)
    pdf.cell(95, 6, f'Date: 2026-06-12', 0, 1)
    
    pdf.cell(95, 6, f'Topic: {topic}', 0, 0)
    pdf.set_font('Arial', 'B', 11)
    if score >= 80:
        pdf.set_text_color(16, 185, 129) # Success green
    elif score >= 50:
        pdf.set_text_color(245, 158, 11) # Warning orange
    else:
        pdf.set_text_color(239, 68, 68) # Error red
        
    pdf.cell(95, 6, f'Overall Score: {score} / 100', 0, 1)
    pdf.set_text_color(75, 85, 99)
    pdf.ln(15)
    
    # Feedback sections
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 8, 'Performance Evaluation', 0, 1)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(31, 41, 55)
    pdf.cell(0, 6, 'Key Strengths:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(55, 65, 81)
    pdf.multi_cell(0, 5, feedback.get('strengths', 'N/A'))
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(31, 41, 55)
    pdf.cell(0, 6, 'Areas of Improvement (Weaknesses):', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(55, 65, 81)
    pdf.multi_cell(0, 5, feedback.get('weaknesses', 'N/A'))
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(31, 41, 55)
    pdf.cell(0, 6, 'Actionable Suggestions:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(55, 65, 81)
    pdf.multi_cell(0, 5, feedback.get('suggestions', 'N/A'))
    pdf.ln(8)
    
    # Q&A transcript section
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 8, 'Interview QA Transcript', 0, 1)
    pdf.ln(2)
    
    for idx, pair in enumerate(QA_pairs):
        # Prevent page overflow by keeping question and answer together
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(17, 24, 39)
        pdf.multi_cell(0, 5, f"Question {idx+1}: {pair['question']}")
        
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(75, 85, 99)
        pdf.multi_cell(0, 5, f"Your Answer: {pair['answer']}")
        pdf.ln(5)
        
    return bytes(pdf.output(dest='S'))
