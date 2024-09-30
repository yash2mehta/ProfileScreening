import pdfplumber
import re
import os
import pandas as pd
import time
import nltk
import docx2txt
from pathlib import Path
from tqdm import tqdm
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

def extract_role_score(resume_text, job_description, model=model):
    data = {
        "Role": "Not mentioned",
        "Score": "Not generated"
    }
    if not resume_text:
        return data
    
    prompt = """
You are tasked with evaluating a candidate based on the provided resume and job description. Your task is to produce exactly two outputs: 

1. **Role**: Based on the job description, identify which role this job description is targeted to. Use only one word or phrase for the role.
2. **Score**: A numerical score (0-100) that represents how well the resume aligns with the job description.

### Inputs:
Resume Text: {resume_text}
Job Description: {job_description}

### Important Instructions:
- ONLY use information from the job description to infer the role.
- ONLY use the resume to determine how well the candidate fits the role (for scoring).
- The **Role** must be a SINGLE word or phrase, with no additional details.
- The **Score** must be a NUMBER between 0 and 100 based on the alignment between the resume and job description.
- Return the result in this exact format with nothing else:

Role: [SINGLE ROLE, in 2 words] 
Score: [NUMBER]
"""

    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    response = chain.invoke({
        'resume_text': resume_text,
        'job_description': job_description,
    })

    # Extract Role
    role_match = re.search(r'Role:\s*(.*)', response)
    if role_match:
        data["Role"] = role_match.group(1).strip()

    # Extract Score
    score_match = re.search(r'Score:\s*(\d+)', response)
    if score_match:
        data["Score"] = int(score_match.group(1))

    return data

def extract_bulk_info_llm(resume_text, model=model):
    if not resume_text:
        return {"Name": "Not mentioned", "Location": "Not mentioned", "Phone": "Not mentioned", "Experience": "Not mentioned", "Fitment Summary": "Not mentioned"}
    
    prompt = """
You are given a resume and a job description. Your task is to strictly retrieve information from the resume text provided and not infer or generate any additional content. If the required information is not present in the resume, return "Not mentioned" without making any assumptions.

Please extract and return the following information from the resume text:
1. Name: (The exact name as written in the resume).
2. Location: (The full address or location as mentioned in the resume).
3. Phone Number: (The phone number as written in the resume).
4. Total Experience in Years: (Extract the number of years of experience mentioned in the resume. If it's not directly specified, compute it and provide reasoning for the computed experience).
5. Fitment Summary: (Summarize the relevant skills and experience found in the resume, but do not infer or add any extra details).
Here is the resume text:
{resume_text}

Important:
- Only retrieve information directly from the resume text.
- If any required information is missing, mention "Not mentioned."
- Do NOT infer or generate details.
- Location and name might be grouped together, if grouped seperate them.
- If total experience is not specified, try to compute it based on the resume.
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
    })

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
    summary_match = re.search(r'Fitment\sSummary:\s*(.*)', response, re.DOTALL)
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
                            try:
                                if 'github.com' in url:
                                    github_links.add(url)
                                elif 'linkedin.com' in url:
                                    linkedin_links.add(url)
                            except:
                                continue
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

def extract_skills(resume_text, skills_file, model=model):

    extracted_data = {}

    # Load skills from the provided Excel sheet
    skills_df = pd.read_excel(skills_file)
    skills = skills_df['Skills'].tolist()

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
    
    return extracted_data



def pdfs_to_cleaned_and_extracted_excel(resume_folder, job_description_file, skills_file, final_excel_path, model=model):

    if os.path.exists(final_excel_path):
        df_existing = pd.read_excel(final_excel_path)
        processed_files = set(df_existing['Filename'].tolist())
    else:
        df_existing = pd.DataFrame()
        processed_files = set()

    all_extracted_data = []
    job_description_text = "\n".join(extract_text_from_file(job_description_file))

    start_time = time.time()
    processed_file_count = 0  # Initialize a counter
    for filename in os.listdir(resume_folder):

        print("\nProcessing: {filename}".format(filename=filename))

        # Increment the processed file count
        processed_file_count += 1

        if processed_file_count % 10 == 0:
            model = OllamaLLM(model="phi3")  # Reinitialize the model to reset its memory

        if filename in processed_files:
            continue  # Skip already processed files

        if filename.endswith(".pdf"):
            file_path = os.path.join(resume_folder, filename)

            # Extract text from the current file
            resume_text = extract_text_from_file(file_path)

            # Extract name, location, phone, experience, and fitment summary in bulk
            extracted_info = extract_bulk_info_llm(resume_text, model=model)  
            print(f"-- Info Extracted")

            extracted_data = extract_role_score(resume_text, job_description_text, model=model)
            print(f"-- Role Score Calculated")


            # Extract GitHub and LinkedIn links
            github_links, linkedin_links = extract_links(file_path)
            print("-- Links extracted")

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
                "Score": extracted_data["Score"],
                "Role": extracted_data["Role"],
            }

            skills_data = extract_skills(resume_text, skills_file, model=model)
            print("-- Skills Extracted")

            # Append the extracted data to the list
            extracted_data.update(skills_data)
            all_extracted_data.append(extracted_data)

            # Save progress after each resume
            df_progress = pd.DataFrame(all_extracted_data)
            df_combined = pd.concat([df_existing, df_progress], ignore_index=True)
            df_combined.to_excel(final_excel_path, index=False)

            yield processed_file_count

    end_time = time.time()
    time_taken = end_time - start_time
    print(f"Time Taken in process: {time_taken} seconds.")

# Example usage
if __name__ == "__main__":
    resume_folder = "../Resumes"
    job_description_file = "../JobDesc.txt"
    skills_file = "../Skills.xlsx"
    final_excel_path = 'final_output1.xlsx'
    pdfs_to_cleaned_and_extracted_excel(resume_folder, job_description_file, skills_file, final_excel_path)
