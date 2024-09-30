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

# Download NLTK resources
nltk.download('stopwords')
from nltk.corpus import stopwords

# Initialize the LLM model
model = OllamaLLM(model="phi3")

def clean_text(text):
    if not text:
        return ""
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable())
    # Remove stopwords
    stop_words = set(stopwords.words('english')).union(set(ENGLISH_STOP_WORDS))
    return ' '.join(word for word in text.split() if word.lower() not in stop_words)

def extract_text_from_file(file_path):
    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        with pdfplumber.open(file_path) as pdf:
            text = ''.join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif ext == '.docx':
        text = docx2txt.process(file_path)
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
    else:
        return ""
    
    return clean_text(text)

def extract_bulk_info_llm(resume_text, job_description):
    if not resume_text:
        return {"Name": "Not mentioned", "Location": "Not mentioned", "Phone": "Not mentioned", "Experience": "Not mentioned", "Fitment Summary": "Not mentioned"}

    prompt = f"""
    Analyze the following resume text and job description, and provide the following information:
    - Name
    - Location
    - Phone Number
    - Total Experience in Years: (Only Number in years)
    - Fitment Summary in 50 words for suitability to the job description.

    Resume Text: {resume_text}
    Job Description: {job_description}
    Output:
    - Name: (Only Name)
    - Location: (Full Location)
    - Phone Number: (Only Number)
    - Total Experience in Years: (Experience in years only)
    - Fitment Summary in 50 words for suitability to the job description.: (Brief summary containing all aspects)
    """

    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    response = chain.invoke({
        'resume_text': resume_text, 
        'job_description': job_description
    })
    print(f"\nResponce: {response}")

    # Parsing the response to extract key fields using regex
    extracted_info = {"Name": "Not mentioned", "Location": "Not mentioned", "Phone": "Not mentioned", "Experience": "Not mentioned", "Fitment Summary": "Not mentioned"}

    # Extract Name
    name_match = re.search(r'Name:\s*([^\n]+)', response)
    if name_match:
        extracted_info["Name"] = name_match.group(1).strip()

    # Extract Location
    location_match = re.search(r'Location:\s*([^\n]+)', response)
    if location_match:
        extracted_info["Location"] = location_match.group(1).strip()

    # Extract Phone Number
    phone_match = re.search(r'Phone Number:\s*([^\n]+)', response)
    if phone_match:
        extracted_info["Phone"] = phone_match.group(1).strip()

    # Extract Total Experience
    experience_match = re.search(r'Total Experience in Years:\s*([^\n]+)', response)
    if experience_match:
        extracted_info["Experience"] = experience_match.group(1).strip()

    # Extract Fitment Summary
    summary_match = re.search(r'Fitment Summary.*?:\s*(.*)', response, re.DOTALL)
    if summary_match:
        extracted_info["Fitment Summary"] = summary_match.group(1).strip()

    return extracted_info

def extract_links(file_path):
    github_links, linkedin_links = set(), set()

    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if page.annots:
                    for annot in page.annots:
                        if 'uri' in annot:
                            url = annot['uri']
                            if 'github.com' in url:
                                github_links.add(url)
                            elif 'linkedin.com' in url:
                                linkedin_links.add(url)
                if text:
                    urls = re.findall(r'(https?://[^\s]+|www\.[^\s]+)', text)
                    for url in urls:
                        if 'github.com' in url:
                            github_links.add(url)
                        elif 'linkedin.com' in url:
                            linkedin_links.add(url)
    else:
        text = extract_text_from_file(file_path)
        urls = re.findall(r'(https?://[^\s]+|www\.[^\s]+)', text)
        for url in urls:
            if 'github.com' in url:
                github_links.add(url)
            elif 'linkedin.com' in url:
                linkedin_links.add(url)
    
    return list(github_links), list(linkedin_links)

def pdfs_to_cleaned_and_extracted_excel(resume_folder, job_description_file, skills_file, final_excel_path):
    # Load existing data if Excel file exists
    if os.path.exists(final_excel_path):
        df_existing = pd.read_excel(final_excel_path)
        processed_files = set(df_existing['Filename'].tolist())
    else:
        df_existing = pd.DataFrame()
        processed_files = set()

    all_extracted_data = []

    # Extract job description text once
    job_description_text = "\n".join(extract_text_from_file(job_description_file))

    # Load skills from the provided Excel sheet
    skills_df = pd.read_excel(skills_file)
    skills = skills_df['Skills'].tolist()

    start_time = time.time()

    # Loop through all files in the specified folder
    for filename in os.listdir(resume_folder):
        if filename in processed_files:
            continue  # Skip already processed files

        if filename.endswith((".pdf", ".docx", ".txt")):
            file_path = os.path.join(resume_folder, filename)
            print(f"Processing: {file_path}")

            # Extract text from the current file
            start = time.time()
            resume_text = extract_text_from_file(file_path)
            end = time.time()
            print(f"\nResume Text (Time: {end - start}s): \n\t{resume_text}")


            # Extract name, location, phone, experience, and fitment summary in bulk
            start = time.time()
            extracted_info = extract_bulk_info_llm(resume_text, job_description_text)
            end = time.time()
            print(f"\n\nExtrated Information (Time: {end - start}s): \n\t{extracted_info}")
            

            # Extract GitHub and LinkedIn links
            start = time.time()
            github_links, linkedin_links = extract_links(file_path)
            end = time.time()
            print(f"\nGitHub (Time: {end - start}s): \n\t{github_links, linkedin_links}")
                  
            # Join links into comma-separated strings
            github_links_str = ', '.join(github_links) if github_links else "Not mentioned"
            linkedin_links_str = ', '.join(linkedin_links) if linkedin_links else "Not mentioned"

            # Initialize a dictionary to store all extracted information
            extracted_data = {
                "Filename": filename,
                "Name": extracted_info["Name"],
                "Location": extracted_info["Location"],
                "Phone": extracted_info["Phone"],
                "Github Links": github_links_str,
                "LinkedIn Links": linkedin_links_str,
                "Total Experience": extracted_info["Experience"],
                "Fitment Summary": extracted_info["Fitment Summary"],
                "Score": extracted_info.get("Score", "Not calculated")
            }

            # Evaluate candidate's skills using resume text
            start = time.time()
            print("Skill Based Extraction started")
            for skill in skills:
                extracted_data[skill] = "Not mentioned" if skill.lower() not in resume_text.lower() else "Has the skill"
            end = time.time()
            print(f"\nSkill Extraction Time: {end - start}")

            # Append the extracted data to the list
            all_extracted_data.append(extracted_data)

            # Save progress after each resume
            df_progress = pd.DataFrame(all_extracted_data)
            df_combined = pd.concat([df_existing, df_progress], ignore_index=True)
            # df_combined.to_excel(final_excel_path, index=False)

    end_time = time.time()
    print(f"Process completed in {end_time - start_time:.2f} seconds.")

# Example usage
if __name__ == "__main__":
    resume_folder = "../Resumes"
    job_description_file = "../Role Description.txt"
    skills_file = "../Evaluation Criteria Sheet.xlsx"
    final_excel_path = 'final_output1.xlsx'
    pdfs_to_cleaned_and_extracted_excel(resume_folder, job_description_file, skills_file, final_excel_path)
