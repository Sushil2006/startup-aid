import streamlit as st
import tempfile
import os
import fitz  # PyMuPDF
import io
import json
from PIL import Image
from ocr import ocr_image, process_question_paper_pdf, process_grading_scheme_pdf
from grader import grade_answer

def merge_ocr_results(all_results):
    """
    Merge OCR results from multiple pages:
    - Combine answers for the same question number
    - Handle 'Contd' entries by merging with the previous question
    """
    merged_answers = {}
    last_question = None
    
    # Process all OCR results in order
    for page_results in all_results:
        if not isinstance(page_results, list):
            continue
            
        for item in page_results:
            question_num = item.get('question_number', 'Unknown')
            answer = item.get('answer', 'No answer extracted')
            
            # Convert question_num to string for consistent handling
            question_num = str(question_num)
            
            # Handle "Contd" questions
            if question_num.lower() == "contd" and last_question is not None:
                # Append to the last question
                merged_answers[last_question] = merged_answers.get(last_question, '') + '\n\n' + answer
            else:
                # Update last_question for potential "Contd" entries
                last_question = question_num
                
                # Merge with existing answer or create new entry
                if question_num in merged_answers:
                    merged_answers[question_num] = merged_answers[question_num] + '\n\n' + answer
                else:
                    merged_answers[question_num] = answer
    
    return merged_answers

def ocr_page():
    """First page: PDF OCR Processing"""
    st.title("PDF OCR Processing App")
    st.write("Upload a PDF to extract handwritten text")
    
    # Initialize OCR results in session state if needed
    if "all_ocr_results" not in st.session_state:
        st.session_state.all_ocr_results = []
        
    if "merged_answers" not in st.session_state:
        st.session_state.merged_answers = {}
    
    # Track if processing is needed
    process_pdf = False
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="main_pdf")
    
    if uploaded_file is not None:
        # Check if this is a new file or changed file requiring processing
        if "current_file_name" not in st.session_state or st.session_state.current_file_name != uploaded_file.name:
            st.session_state.current_file_name = uploaded_file.name
            process_pdf = True
        
        if process_pdf:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                pdf_path = tmp_file.name
            
            try:
                # Open the PDF using PyMuPDF
                with st.spinner("Converting PDF to images..."):
                    pdf_document = fitz.open(pdf_path)
                    total_pages = len(pdf_document)
                
                st.success(f"Successfully opened PDF: {total_pages} pages found")
                
                # Store all OCR results for later merging
                all_ocr_results = []
                
                # Process each page
                for i in range(total_pages):
                    st.write(f"## Page {i+1}")
                    
                    # Get the page and render it as an image
                    page = pdf_document[i]
                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
                    
                    # Create a temporary image file
                    img_path = f"{pdf_path}_page_{i+1}.jpg"
                    pix.save(img_path)
                    
                    col1, col2 = st.columns(2)
                    
                    # Display the page image
                    with col1:
                        st.image(img_path, caption=f"Page {i+1}", use_container_width=True)
                    
                    # Process OCR
                    with col2:
                        with st.spinner(f"Performing OCR on page {i+1}..."):
                            try:
                                ocr_result = ocr_image(img_path)
                                # Store the result for later merging
                                all_ocr_results.append(ocr_result)
                                
                                # Display results
                                st.write("### Extracted Text")
                                
                                if isinstance(ocr_result, list):
                                    for item in ocr_result:
                                        # Safely handle question number by converting to string first
                                        try:
                                            question_num = str(item.get('question_number', 'Unknown'))
                                            st.markdown(f"## Question {question_num}")
                                            
                                            # Display answer with proper markdown rendering
                                            answer = item.get('answer', 'No answer extracted')
                                            st.markdown(answer)
                                            
                                            # Add visual separation between questions
                                            st.markdown("---")
                                        except Exception as format_error:
                                            st.error(f"Error formatting question: {str(format_error)}")
                                            st.json(item)  # Show the raw item for debugging
                                else:
                                    # Handle case where response is not the expected format
                                    st.warning("Response format not as expected. Raw output:")
                                    st.json(ocr_result)
                                    
                            except Exception as e:
                                st.error(f"Error processing page {i+1}: {str(e)}")
                    
                    # Clean up temporary image file
                    try:
                        os.remove(img_path)
                    except:
                        pass
                
                # Close the PDF document
                pdf_document.close()
                
                # Store OCR results in session state for access across pages
                st.session_state.all_ocr_results = all_ocr_results
                
                # Display combined answer sheet at the end
                st.header("Complete Answer Sheet")
                st.write("All extracted answers merged across pages:")
                
                # Merge all OCR results
                merged_answers = merge_ocr_results(all_ocr_results)
                
                # Store merged answers in session state
                st.session_state.merged_answers = merged_answers
                
                # Create a container with nice formatting for the final answer sheet
                with st.container():
                    st.markdown("---")
                    st.subheader("Final Merged Answers")
                    
                    # Try to sort questions numerically when possible
                    def sort_key(item):
                        key = item[0]
                        # Try to convert to float for numerical sorting
                        try:
                            return float(key)
                        except:
                            # Fall back to string sorting
                            return key
                    
                    # Display merged answers in order
                    for question_num, answer in sorted(merged_answers.items(), key=sort_key):
                        st.markdown(f"### Question {question_num}")
                        st.markdown(answer)
                        st.markdown("---")
                
                # Clean up the temporary PDF file
                try:
                    os.remove(pdf_path)
                except:
                    pass
                    
            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")
                try:
                    os.remove(pdf_path)
                except:
                    pass
        else:
            # Display previously processed results
            st.success(f"Using previously processed results")
            
            # Display the merged answers from session state
            st.header("Complete Answer Sheet")
            st.write("All extracted answers merged across pages:")
            
            with st.container():
                st.markdown("---")
                st.subheader("Final Merged Answers")
                
                # Try to sort questions numerically when possible
                def sort_key(item):
                    key = item[0]
                    # Try to convert to float for numerical sorting
                    try:
                        return float(key)
                    except:
                        # Fall back to string sorting
                        return key
                
                # Display merged answers in order
                for question_num, answer in sorted(st.session_state.merged_answers.items(), key=sort_key):
                    st.markdown(f"### Question {question_num}")
                    st.markdown(answer)
                    st.markdown("---")
    
    # Add Next button to navigate to the second page
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Next", key="next_button", use_container_width=True):
            # Just navigate to the next page without reprocessing
            st.session_state.page = "additional_materials"
            st.rerun()

def additional_materials_page():
    """Second page: Additional Materials Upload"""
    st.title("Additional Materials")
    st.write("Upload supporting documents to assist with grading")
    
    # Question Paper Upload
    st.subheader("1. Question Paper")
    question_paper = st.file_uploader("Upload Question Paper", type="pdf", key="question_paper")
    
    # Process question paper if uploaded and not already processed
    if question_paper:
        if "qp_file_name" not in st.session_state or st.session_state.qp_file_name != question_paper.name:
            st.session_state.qp_file_name = question_paper.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(question_paper.getvalue())
                qp_path = tmp_file.name
            
            with st.spinner("Processing question paper..."):
                try:
                    qp_json = process_question_paper_pdf(qp_path)
                    st.session_state.question_paper_json = qp_json
                    st.success("Question paper processed successfully!")
                except Exception as e:
                    st.error(f"Error processing question paper: {str(e)}")
                finally:
                    try:
                        os.remove(qp_path)
                    except:
                        pass
        else:
            st.success("Question paper already processed.")
    
    # Grading Scheme Upload
    st.subheader("2. Grading Scheme")
    grading_scheme = st.file_uploader("Upload Grading Scheme", type="pdf", key="grading_scheme")
    
    # Process grading scheme if uploaded and not already processed
    if grading_scheme:
        if "gs_file_name" not in st.session_state or st.session_state.gs_file_name != grading_scheme.name:
            st.session_state.gs_file_name = grading_scheme.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(grading_scheme.getvalue())
                gs_path = tmp_file.name
            
            with st.spinner("Processing grading scheme..."):
                try:
                    gs_json = process_grading_scheme_pdf(gs_path)
                    st.session_state.grading_scheme_json = gs_json
                    st.success("Grading scheme processed successfully!")
                except Exception as e:
                    st.error(f"Error processing grading scheme: {str(e)}")
                finally:
                    try:
                        os.remove(gs_path)
                    except:
                        pass
        else:
            st.success("Grading scheme already processed.")
    
    # Lecture Material Upload
    st.subheader("3. Lecture Material")
    lecture_material = st.file_uploader("Upload Lecture Material", type="pdf", key="lecture_material")
    
    # Text Input
    st.subheader("Additional Notes")
    user_notes = st.text_area("Enter any additional information or notes", height=200)
    st.session_state.user_notes = user_notes
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Back", key="back_button", use_container_width=True):
            st.session_state.page = "ocr"
            st.rerun()
    
    # Add Grade Answers button directly on this page instead of going to results page
    with col3:
        if st.button("Grade Answers", key="grade_button", use_container_width=True):
            # Check if we have the necessary data
            if all(key in st.session_state for key in ["merged_answers", "question_paper_json", "grading_scheme_json"]):
                st.session_state.page = "grading"
                st.rerun()
            else:
                st.error("Missing required data for grading. Please ensure you've uploaded and processed all necessary files.")

def prepare_grading_data():
    """Prepare data for grading by combining question paper, answers, and grading scheme."""
    grading_data = []
    
    # Ensure we have all the required data
    if not all(key in st.session_state for key in ["merged_answers", "question_paper_json", "grading_scheme_json"]):
        return None
    
    # Get the question paper details
    question_paper = st.session_state.question_paper_json
    if not isinstance(question_paper, list):
        return None
    
    # Get the grading scheme details
    grading_scheme = st.session_state.grading_scheme_json
    if not isinstance(grading_scheme, list):
        return None
    
    # Get the student answers
    student_answers = st.session_state.merged_answers
    
    # Create a grading scheme lookup dictionary
    gs_lookup = {str(item.get("question_number")): item.get("grading_scheme", "") for item in grading_scheme}
    
    # Professor prompt from user notes
    professor_prompt = st.session_state.get("user_notes", "")
    
    # For each question in the question paper
    for question in question_paper:
        q_num = str(question.get("question_number", ""))
        
        # Skip if no question number
        if not q_num:
            continue
        
        # Get the corresponding student answer
        student_answer = student_answers.get(q_num, "")
        
        # Get the corresponding grading scheme
        question_grading_scheme = gs_lookup.get(q_num, "")
        
        # Prepare the data in the format expected by grade_answer
        question_data = {
            "question_num": q_num,
            "question": question.get("question", ""),
            "marks": question.get("marks", 5),
            "student_answer": student_answer,
            "grading_scheme": question_grading_scheme,
            "relevant_lecture_text": "",  # Empty for now as per requirements
            "professor_prompt": professor_prompt
        }
        
        grading_data.append(question_data)
    
    return grading_data

def grading_page():
    """Grade answers and display results in tabs."""
    st.title("Answer Grading")
    
    # Check if we need to process the grading
    if "grading_results" not in st.session_state:
        # Prepare the data for grading
        grading_data = prepare_grading_data()
        
        if not grading_data:
            st.error("Missing required data for grading. Please ensure you've uploaded and processed all necessary files.")
            return
        
        # Process each question and grade it
        results = []
        
        # Show a progress bar without the text updates
        with st.spinner("Grading answers..."):
            progress_bar = st.progress(0)
            
            for i, question_data in enumerate(grading_data):
                # Grade the answer without showing the text update
                try:
                    grading_result = grade_answer(question_data)
                    
                    # Combine the grading result with the question data for display
                    display_data = {
                        **question_data,
                        **grading_result
                    }
                    
                    results.append(display_data)
                except Exception as e:
                    # Add a placeholder for failed grading, without showing the error
                    results.append({
                        **question_data,
                        "error": str(e),
                        "marks_awarded": 0,
                        "explanation": "Error during grading"
                    })
                
                # Update progress
                progress_bar.progress((i+1) / len(grading_data))
        
        # Store the results in session state
        st.session_state.grading_results = results
    
    # Display the grading results in tabs
    if "grading_results" in st.session_state:
        results = st.session_state.grading_results
        
        # Calculate and display total marks
        if results:
            total_marks_awarded = sum(result.get('marks_awarded', 0) for result in results)
            total_possible_marks = sum(result.get('marks', 0) for result in results)
            
            st.header(f"Total Score: {total_marks_awarded}/{total_possible_marks} ({(total_marks_awarded/total_possible_marks*100) if total_possible_marks else 0:.1f}%)")
            st.markdown("---")
            
            # Create tabs for each question
            tabs = st.tabs([f"Question {result.get('question_num', i+1)}" for i, result in enumerate(results)])
            
            for i, (tab, result) in enumerate(zip(tabs, results)):
                with tab:
                    # Question details (explicitly using markdown)
                    st.markdown(f"## Question {result.get('question_num')}")
                    st.markdown(result.get('question', ''))
                    
                    # Total marks
                    st.markdown(f"**Total Marks:** {result.get('marks', 'N/A')}")
                    
                    # Student's answer
                    st.markdown("### Student's Answer")
                    st.markdown(result.get('student_answer', 'No answer provided'))
                    
                    # Grading scheme
                    st.markdown("### Grading Scheme")
                    st.markdown(result.get('grading_scheme', 'No grading scheme provided'))
                    
                    # Grading result
                    st.markdown("### Grading Result")
                    st.markdown(f"**Marks Awarded:** {result.get('marks_awarded', 'N/A')} / {result.get('marks', 'N/A')}")
                    
                    # Explanation
                    st.markdown("### Explanation")
                    st.markdown(result.get('explanation', 'No explanation provided'))
        else:
            st.warning("No grading results available.")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to Materials", key="back_to_materials", use_container_width=True):
            st.session_state.page = "additional_materials"
            st.rerun()
    with col2:
        if st.button("Back to OCR", key="back_to_ocr", use_container_width=True):
            st.session_state.page = "ocr"
            st.rerun()

def main():
    # Initialize session state for page navigation
    if "page" not in st.session_state:
        st.session_state.page = "ocr"
    
    # Display the appropriate page
    if st.session_state.page == "ocr":
        ocr_page()
    elif st.session_state.page == "additional_materials":
        additional_materials_page()
    elif st.session_state.page == "grading":
        grading_page()
    # Removed the results_page from the navigation flow

if __name__ == "__main__":
    main()
