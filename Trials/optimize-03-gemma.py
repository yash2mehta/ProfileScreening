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
model = OllamaLLM(model="gemma2")

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
You are given a resume and a job description. Your task is to **strictly retrieve information** from the resume text provided and not infer or generate any additional content. If the required information is not present in the resume, return "Not mentioned" without making any assumptions.

Please **extract** and **return** the following information from the resume text:
1. **Name**: (The exact name as written in the resume).
2. **Location**: (The full address or location as mentioned in the resume).
3. **Phone Number**: (The phone number as written in the resume).
4. **Total Experience in Years**: (Extract the number of years of experience mentioned in the resume. If it's not directly specified, compute it and provide reasoning for the computed experience).
5. **Fitment Summary**: (Summarize the relevant skills and experience found in the resume, but do not infer or add any extra details).

Here is the resume text:
{resume_text}

Important:
- Only retrieve information directly from the resume text.
- If any required information is missing, mention "Not mentioned."
- Do NOT infer or generate details.
- Provide the output in the following format:

Output:
- Name: [Extracted Full Name]
- Location: [Extracted Full Location]
- Phone Number: [Extracted Phone Number]
- Total Experience in Years: [Extracted Experience in Years]
- Fitment Summary: [Extracted Fitment Summary]
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

def evaluate_candidate(skill, resume_text):
    prompt = "Does the candidate have the skill '{skill}'? If so, briefly describe their experience with it in 50-100 words.\n\nCandidate Resume:\n{resume_text}"
    
    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    result = chain.invoke({'skill':skill, 'resume_text': resume_text})
    
    # Check if the skill is mentioned in the response, otherwise return "Not mentioned"
    if "not mentioned" in result.lower() or "does not have" in result.lower():
        return "Not mentioned"
    return result

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

        print("\n\n")
        print("--"*100)

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

            # Optimized Skill-Based Extraction
            start = time.time()
            print("Skill Based Extraction started")

            # Combine all skills into a single prompt to reduce the number of model calls
            skills_prompt = "Evaluate the candidate's proficiency in the following skills: \n"
            skills_prompt += "\n".join([f"- {skill}" for skill in skills])

            prompt_template = """
            Candidate Resume:
            {resume_text}

            {skills_prompt}

            For each skill, provide a brief evaluation in 50-100 words or say 'Not mentioned' if the skill is not mentioned in the resume.
            """

            # Sending a single request to the model for all skills
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | model
            skills_response = chain.invoke({'resume_text': resume_text, 'skills_prompt':skills_prompt})

            # Parse the model response to extract skill-based observations
            for skill in skills:
                # Search for the evaluation of each skill in the response
                skill_pattern = rf"{re.escape(skill)}:?\s*(.*)"
                skill_match = re.search(skill_pattern, skills_response, re.IGNORECASE)
                
                # Assign the extracted observation to the skill, or 'Not mentioned' if not found
                extracted_data[skill] = skill_match.group(1).strip() if skill_match else "Not mentioned"

            print(f"Individual Skill Evaluation completed!\n\n\t{skills_response}")
            end = time.time()
            print(f"\nSkill Extraction Time: {end - s]tart}")


            # Append the extracted data to the list
            all_extracted_data.append(extracted_data)

            # Save progress after each resume
            df_progress = pd.DataFrame(all_extracted_data)
            df_combined = pd.concat([df_existing, df_progress], ignore_index=True)
            df_combined.to_excel(final_excel_path, index=False)

    end_time = time.time()
    print(f"Process completed in {end_time - start_time:.2f} seconds.")

# Example usage
if __name__ == "__main__":
    resume_folder = "../Resumes"
    job_description_file = "../Role Description.txt"
    skills_file = "../Evaluation Criteria Sheet.xlsx"
    final_excel_path = 'optimize-03-gemma.xlsx'
    pdfs_to_cleaned_and_extracted_excel(resume_folder, job_description_file, skills_file, final_excel_path)
