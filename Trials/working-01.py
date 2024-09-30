import pdfplumber
import re
import os
import pandas as pd
import time
import nltk
import docx2txt
from pathlib import Path
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Download the required NLTK resources
nltk.download('stopwords')
from nltk.corpus import stopwords

# Phi3 Model
model = OllamaLLM(model="phi3")

# Function to clean the extracted text by removing non-printable characters and stopwords
def clean_text(text):
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable())
    # Remove stopwords
    stop_words = set(stopwords.words('english')).union(set(ENGLISH_STOP_WORDS))
    cleaned_text = ' '.join(word for word in text.split() if word.lower() not in stop_words)
    return cleaned_text

# Function to extract text from PDF files
def extract_text_from_pdf(pdf_path):
    text_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                cleaned_text = clean_text(page_text)
                text_data.extend(cleaned_text.split('\n'))
    return text_data

# Function to extract text from .docx files
def extract_text_from_docx(docx_path):
    return clean_text(docx2txt.process(docx_path)).split('\n')

# Function to extract text from .txt files
def extract_text_from_txt(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as file:
        return clean_text(file.read()).splitlines()

# Function to clean text using regular expressions for better formatting
def clean_text_column(text):
    if isinstance(text, str):
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'(\d)([A-Z])', r'\1 \2', text)
        text = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', text)
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    return text

# Function to extract information using LLM prompt engineering
def extract_information_llm(resume_text):
    if not isinstance(resume_text, str):
        return {"Name": "Not mentioned", "Location": "Not mentioned"}

    prompt = """
    Extract the name and location from the following resume text. The name may appear anywhere in the text and may be capitalized.

    Resume Text: {resume_text}

    Provide the extracted information in this format:
    - Name: [Extracted Name]
    - Location: [Extracted Location]
    """

    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    extracted_text = chain.invoke({'resume_text': resume_text})
    
    extracted_info = {
        "Name": "Not mentioned",
        "Location": "Not mentioned"
    }

    lines = extracted_text.split('\n')
    for line in lines:
        if "Name:" in line:
            extracted_info["Name"] = line.split(":", 1)[1].strip() or "Not mentioned"
        elif "Location:" in line:
            extracted_info["Location"] = line.split(":", 1)[1].strip() or "Not mentioned"
    
    return extracted_info

# Function to extract phone number using LLM prompt engineering
def extract_phone_number(resume_text):
    if not isinstance(resume_text, str):
        return "Not mentioned"

    prompt = """
    Extract the phone number from the following resume text. The phone number may appear in various formats, such as international or local.

    Resume Text: {resume_text}

    Provide the extracted phone number in this format:
    - Phone Number: [Extracted Phone Number]
    """

    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    extracted_text = chain.invoke({'resume_text': resume_text})
    
    phone_number = "Not mentioned"
    
    lines = extracted_text.split('\n')
    for line in lines:
        if "Phone Number:" in line:
            extracted_value = line.split(":", 1)[1].strip()
            if extracted_value.lower() == "none" or not extracted_value:
                phone_number = "Not mentioned"
            else:
                phone_number = extracted_value
    
    return phone_number

# Function to extract links using pdfplumber
def extract_links_pdfplumber(pdf_path):
    github_links = set()  # Use a set to ensure uniqueness
    linkedin_links = set()  # Ensure LinkedIn links are unique

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extracting annotations
            if page.annots:
                for annot in page.annots:
                    if 'uri' in annot:
                        url = annot['uri']
                        if url:
                            if 'github.com' in url:
                                github_links.add(url)  # Add to set to remove duplicates
                            elif 'linkedin.com' in url:
                                linkedin_links.add(url)
    
    return list(github_links), list(linkedin_links)

# Fallback function to extract links using regex if pdfplumber didn't find any
def extract_links_regex(pdf_path):
    github_links = set()
    linkedin_links = set()

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract text and search for links using regex
            page_text = page.extract_text()
            if page_text:
                # Regex to capture URLs
                urls = re.findall(r'(https?://[^\s]+|www\.[^\s]+)', page_text)
                for url in urls:
                    if 'github.com' in url:
                        github_links.add(url)
                    elif 'linkedin.com' in url:
                        linkedin_links.add(url)
    
    return list(github_links), list(linkedin_links)

# Function to generate a fitment summary using LLM
def fitment_summary(resume_text, job_description):
    if not isinstance(resume_text, str) or not isinstance(job_description, str):
        return "Not mentioned"
    
    prompt = """
    Based on the following resume and job description, provide a summary of how this candidate is suitable for the role in 50 words.

    Resume Text: {resume_text}

    Job Description: {job_description}

    Provide the fitment summary in this format:
    - Summary: [50-word Summary]
    """

    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    extracted_text = chain.invoke({'resume_text': resume_text, 'job_description':job_description})
    
    summary = "Not mentioned"
    
    lines = extracted_text.split('\n')
    for line in lines:
        if "Summary:" in line:
            summary = line.split(":", 1)[1].strip() or "Not mentioned"
    
    return summary

# Function to calculate total experience using LLM
def total_experience(resume_text):
    if not isinstance(resume_text, str):
        return "Fresher or Not mentioned"

    prompt = """
    Calculate the total years of experience from the work experience section of the following resume text. If no work experience section is available, return 'Fresher or Not mentioned.'

    Resume Text: {resume_text}

    Provide the total experience in this format:
    - Experience: [Total Experience in Years]
    """

    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    extracted_text = chain.invoke({'resume_text': resume_text})

    lines = extracted_text.split('\n')
    for line in lines:
        if "Experience:" in line:
            experience = line.split(":", 1)[1].strip() or "Fresher or Not mentioned"
    
    return experience

# Function to calculate a suitability score using LLM
def calculate_score(resume_text, job_description):
    if not isinstance(resume_text, str) or not isinstance(job_description, str):
        return "Not mentioned"

    prompt = """
    Based on the job description below, evaluate the suitability of the candidate described in the resume. 
    Provide a score from 1 to 100 on how suitable the candidate is for the job role.

    Job Description:{job_description}

    Candidate Resume:{resume_text}

    Please respond with only the numerical score.
    """

    try:
        prompt = ChatPromptTemplate.from_template(prompt)
        chain = prompt | model
        extracted_text = chain.invoke({
            'job_description':job_description,
            'resume_text': resume_text
        })
        score = int(extracted_text.strip())
    except (ValueError, KeyError):
        score = None

    return score


# Function to extract text from different file types
def extract_text_from_file(file_path):
    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext == '.txt':
        return extract_text_from_txt(file_path)
    else:
        return []

# Function to evaluate candidate's resume against the extracted skills
def evaluate_candidate(skill, resume_text):
    prompt = "Does the candidate have the skill '{skill}'? If so, briefly describe their experience with it in 50-100 words.\n\nCandidate Resume:\n{resume_text}"
    
    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    result = chain.invoke({'skill':skill, 'resume_text': resume_text})
    
    # Check if the skill is mentioned in the response, otherwise return "Not mentioned"
    if "not mentioned" in result.lower() or "does not have" in result.lower():
        return "Not mentioned"
    return result

# Main function to extract, clean, and process resumes
def pdfs_to_cleaned_and_extracted_excel(resume_folder, job_description_file, skills_file, final_excel_path):
    # Load existing data if the Excel file already exists
    if os.path.exists(final_excel_path):
        df_existing = pd.read_excel(final_excel_path)
        processed_files = set(df_existing['Filename'].tolist())
    else:
        df_existing = pd.DataFrame()
        processed_files = set()

    all_extracted_data = []

    # Extract the job description text
    job_description_text = "\n".join(extract_text_from_file(job_description_file))

    # Load skills and requirements from the provided Excel sheet
    skills_df = pd.read_excel(skills_file)
    skills = skills_df['Skills'].tolist()  # Assuming the column is named 'Skills'

    # Record the start time
    start_time = time.time()

    # Loop through all files in the specified folder
    for filename in os.listdir(resume_folder):
        if filename in processed_files:
            print(f"Skipping already processed file: {filename}")
            continue  # Skip the already processed files

        if filename.endswith((".pdf", ".docx", ".txt")):
            file_path = os.path.join(resume_folder, filename)
            print(f"Processing: {filename}")

            # Extract text from the current file
            resume_text = "\n".join(extract_text_from_file(file_path))

            # Clean the extracted text
            cleaned_text = clean_text_column(resume_text)

            # Extract Name and Location using LLM
            extracted_info = extract_information_llm(cleaned_text)
            print("Name and Location Extracted!")

            # Extract Phone Number
            phone_number = extract_phone_number(cleaned_text)
            print("Phone Number Extracted!")

            # Extract GitHub and LinkedIn links using pdfplumber, with regex fallback
            github_links, linkedin_links = extract_links_pdfplumber(file_path)
            if not github_links and not linkedin_links:
                github_links, linkedin_links = extract_links_regex(file_path)
            print("Links Extracted!")

            # Generate Fitment Summary
            summary = fitment_summary(cleaned_text, job_description_text)
            print("Summary generated!")            

            # Calculate Total Experience
            experience = total_experience(cleaned_text)
            print("Experience Extracted")

            # Calculate Suitability Score
            score = calculate_score(cleaned_text, job_description_text)
            print("Score Extracted")
            
            # Join multiple links into a single string (comma-separated)
            github_links_str = ', '.join(github_links) if github_links else "Not mentioned"
            linkedin_links_str = ', '.join(linkedin_links) if linkedin_links else "Not mentioned"

            # Initialize a dictionary to store all extracted information
            extracted_data = {
                "Filename": filename,
                "Name": extracted_info["Name"],
                "Location": extracted_info["Location"],
                "Phone Number": phone_number,
                "Github Links": github_links_str,
                "LinkedIn Links": linkedin_links_str,
                "Total Experience": experience,
                "Fitment Summary": summary,
                "Score": score
            }

            # Generate candidate observations for each skill
            for skill in skills:
                observation = evaluate_candidate(skill, cleaned_text)
                extracted_data[skill] = observation
            print("Individual Skill Evaluation!")

            # Append the extracted data to the list
            all_extracted_data.append(extracted_data)

            # Save progress after each resume
            df_progress = pd.DataFrame(all_extracted_data)
            df_combined = pd.concat([df_existing, df_progress], ignore_index=True)
            df_combined.to_excel(final_excel_path, index=False)
    
    # Record the end time and calculate elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Process completed in {elapsed_time:.2f} seconds.")
    
# Example usage:
if __name__=="__main__":
    resume_folder = "./Resumes"
    job_description_file = "./Role Description.txt"
    skills_file = "./Evaluation Criteria Sheet.xlsx"
    final_excel_path = 'final_output1.xlsx'
    pdfs_to_cleaned_and_extracted_excel(
        resume_folder, job_description_file, 
        skills_file, final_excel_path
    )
    
# Problems:
#     1.0 Too slow
#     2.0 Too many model calls