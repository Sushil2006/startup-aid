import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

def grade_answer(answer_data):
    """
    Grade a student's answer using AI based on provided grading scheme and criteria.
    
    Args:
        answer_data: JSON object containing question details, student answer, and grading criteria
        
    Returns:
        JSON object with grading results
    """
    # Load environment variables
    load_dotenv()
    
    # Initialize client
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    
    model = "gemini-2.5-pro-exp-03-25"
    
    # Format the data for the prompt
    prompt = """
You are a **Paper Correction AI**, specialized in grading student answers based on provided grading schemes and lecture material. Your task is to evaluate answers strictly according to the provided data, using your own knowledge base **only as a last resort** when necessary.

You will receive a JSON object containing:
- **question_num**: The number of the question.
- **question**: The question that was asked.
- **marks**: The total marks allocated for the question.
- **student_answer**: The student's response.
- **grading_scheme**: The official criteria for grading this answer.
- **relevant_lecture_text**: Extracts from lecture material relevant to this question.
- **professor_prompt**: Additional instructions on how the grading should be done.

Your task:
1. **Evaluate the student_answer strictly based on the provided grading_scheme and relevant_lecture_text**.
2. If unclear, use the professor_prompt to guide the grading.
3. **Only if absolutely necessary**, refer to your own general knowledge, but ensure alignment with the provided data.
4. **Output a structured JSON** in the following format:

{
  "question_num": 5,
  "marks_awarded": 3,
  "explanation": "The student correctly explained the key concept but missed an important step outlined in the grading scheme."
}

Any text in the explanation should be written in markdown, enclose any math in $...$ so that it's formatted properly.
Make sure your grading is **fair, consistent, and well-justified** based on the provided inputs. **Do not assume information beyond what is given unless necessary**.

Here is the answer data to grade:
"""
    # Add the answer data to the prompt
    prompt += json.dumps(answer_data, indent=2)

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(text=prompt),
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=0.3,
        top_p=0.95,
        top_k=64,
        max_output_tokens=65536,
        response_mime_type="application/json",
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    
    # Convert response to JSON and return
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        # Fallback in case the response is not valid JSON
        return {"error": "Failed to parse grading results", "raw_response": response.text}

if __name__ == "__main__":
    # Example usage
    test_data = {
        "question_num": 1,
        "question": "Explain the concept of vector spaces.",
        "marks": 10,
        "student_answer": "A vector space is a set that is closed under addition and scalar multiplication.",
        "grading_scheme": "- Full marks (10 points): Complete explanation with axioms and examples\n- Partial marks (5 points): Basic definition correct but missing details\n- Minimal marks (2 points): Vague understanding only",
        "relevant_lecture_text": "Vector spaces are mathematical structures that consist of a set V, a field F, and two operations: vector addition and scalar multiplication. These operations must satisfy specific axioms.",
        "professor_prompt": "Focus on whether students understand the closure properties and the axioms."
    }
    
    result = grade_answer(test_data)
    print(json.dumps(result, indent=2))
