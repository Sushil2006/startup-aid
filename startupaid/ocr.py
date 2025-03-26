import base64
import os
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv
from google import genai
from google.genai import types

def ocr_image(image_path):
    """Extract text from an image using Gemini OCR and return as JSON."""
    # Load environment variables
    load_dotenv()
    
    # Initialize client
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    # Read and encode the image
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")
    
    model = "gemini-2.5-pro-exp-03-25"
    
    # Correctly format the image data for Gemini
    subject = "Linear Algebra"

    prompt = """
You are an expert in extracting students' handwritten answers from exam papers with high accuracy. The subject being evaluated is linear algebra so use this context to resolve ambiguities in handwriting.

Extract all handwritten answers along with their corresponding question numbers. Ignore any printed text, instructions, or irrelevant content. Ignore strikethrough text as well. DO NOT modify ANY of the student's answers even if they are wrong and DO NOT hallucinate anything about what the user has written, just extract them as they are. Represent the extracted data as a list of JSON objects in the following format:

[
  {
    "question_number": 5,
    "answer": "Student's handwritten answer here, preserving formatting using markdown. Any mathematical expressions should be accurately represented in the markdown as well."
  },
  {
    "question_number": 6,
    "answer": "Next student's answer..."
  }
]

In case the question number for a given question is not specified, write "Contd" there, implying that it's a continuation of the answer on the previous page. Note that the question number can also be like 1a and stuff like that (not always an integer). However, dont include dots or brackets in the question number (just alphanumeric characters). 
Ensure precise segmentation of answers and their correct association with question numbers. If any text is unclear, infer the most likely content based on subject knowledge while preserving the original intent.

"""

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(text=prompt),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/jpeg",
                        data=image_base64
                    )
                ),
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
    
    print(response.text)

    # Convert response to JSON and return
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        # Fallback in case the response is not valid JSON
        return {"text": response.text}


def process_question_paper(qp_text):
    """Extract text from an image using Gemini OCR and return as JSON."""
    # Load environment variables
    load_dotenv()
    
    # Initialize client
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    
    model = "gemini-2.5-pro-exp-03-25"
    
    # Correctly format the image data for Gemini

    prompt = """
You are an expert in extracting structured data from exam question papers. I will provide you with the text of a question paper, and your task is to extract the following details for each question:

- **question_number**: The question number.  
- **question**: The question text, formatted in **Markdown**. Remember to wrap any math using $...$ signs, the markdown would be visualized in a markdown engine and i want the math to be rendered properly.   
- **marks**: The marks allocated for the question. If marks are not explicitly mentioned, assume a default value of **10**.

Your output should be a structured **JSON** list, where each entry follows this format:

[
  {
    "question_number": 1,
    "question": "### What is Newton’s First Law of Motion? Explain with an example.",
    "marks": 5
  },
  {
    "question_number": 2,
    "question": "### Derive the equation of motion: \\( v^2 = u^2 + 2as \\).",
    "marks": 10
  }
]

Extract the data accurately and ensure proper Markdown formatting for clarity. Do not add any extra details beyond what is present in the question paper text. Here is the question paper:

"""
    prompt += qp_text

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
    
    print(response.text)

    # Convert response to JSON and return
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        # Fallback in case the response is not valid JSON
        return {"text": response.text}

def extract_text_from_pdf(pdf_path):
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        String containing all text extracted from the PDF
    """
    try:
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        text = ""
        
        # Extract text from each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text += page.get_text()
            text += "\n\n"  # Add spacing between pages
            
        pdf_document.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return ""

def process_question_paper_pdf(pdf_path):
    """
    Process a question paper PDF by extracting text and then analyzing it.
    
    Args:
        pdf_path: Path to the question paper PDF
        
    Returns:
        JSON object containing structured question data
    """
    try:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(pdf_path)
        
        if not pdf_text:
            return {"error": "Failed to extract text from PDF"}
        
        # Process the extracted text
        question_data = process_question_paper(pdf_text)
        
        return question_data
    except Exception as e:
        print(f"Error processing question paper PDF: {str(e)}")
        return {"error": f"Failed to process question paper: {str(e)}"}

def process_grading_scheme(gs_text):
    """
    Process grading scheme text and extract structured information.
    
    Args:
        gs_text: Text extracted from a grading scheme document
        
    Returns:
        JSON object containing structured grading scheme data
    """
    # Load environment variables
    load_dotenv()
    
    # Initialize client
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    
    model = "gemini-2.5-pro-exp-03-25"
    
    prompt = """
You are an expert in analyzing grading schemes for academic assessments. I will provide you with the text of a grading scheme document, and your task is to extract the following details for each question:

- **question_number**: The question number the grading criteria applies to.
- **grading_scheme**: The detailed grading criteria, formatted in **Markdown** including any point breakdowns, rubrics, or evaluation guidelines.

Your output should be a structured **JSON** list, where each entry follows this format:

[
  {
    "question_number": 1,
    "grading_scheme": "- Full marks (5 points): Correctly states Newton's First Law and provides a relevant example\\n- Partial marks (3 points): States the law correctly but example is incomplete\\n- Minimal marks (1 point): Only mentions inertia without proper explanation"
  },
  {
    "question_number": 2,
    "grading_scheme": "- Derivation steps (6 points):\\n  * Start with correct equations (2 points)\\n  * Mathematical manipulation (2 points)\\n  * Final correct equation (2 points)\\n- Explanation of variables (4 points)"
  }
]

Extract the data accurately and ensure proper Markdown formatting for clarity. If the grading scheme does not explicitly mention point allocations for a question, include whatever grading criteria are provided. Here is the grading scheme document:

"""
    prompt += gs_text

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
    
    print(response.text)

    # Convert response to JSON and return
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        # Fallback in case the response is not valid JSON
        return {"text": response.text}

def process_grading_scheme_pdf(pdf_path):
    """
    Process a grading scheme PDF by extracting text and then analyzing it.
    
    Args:
        pdf_path: Path to the grading scheme PDF
        
    Returns:
        JSON object containing structured grading scheme data
    """
    try:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(pdf_path)
        
        if not pdf_text:
            return {"error": "Failed to extract text from PDF"}
        
        # Process the extracted text
        grading_data = process_grading_scheme(pdf_text)
        
        return grading_data
    except Exception as e:
        print(f"Error processing grading scheme PDF: {str(e)}")
        return {"error": f"Failed to process grading scheme: {str(e)}"}

if __name__ == "__main__":

    res = process_question_paper_pdf("qp.pdf")
    print(res)

    #generate()