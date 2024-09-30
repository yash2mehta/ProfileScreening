import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration
from optimize_03 import *

# Load the T5 model and tokenizer
tokenizer = T5Tokenizer.from_pretrained("t5-base")
model = T5ForConditionalGeneration.from_pretrained("t5-base")

def extract_role_score(resume_text, job_description):
    data = {
        "Role": "Not mentioned",
        "Score": "Not generated"
    }
    if not resume_text:
        return data

    prompt = f"""
    You are tasked with evaluating a candidate based on the provided resume and job description. Your task is to produce exactly two outputs:

    1. **Role**: Based on the job description, identify which role this job description is targeted to. Use only one word or phrase for the role.
    2. **Score**: A numerical score (0-100) that represents how well the resume aligns with the job description.

    ### Inputs:
    Resume Text: {resume_text}
    Job Description: {job_description}
    """
    
    # Encode the inputs and generate the output
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    outputs = model.generate(inputs.input_ids, max_length=150, num_beams=4, early_stopping=True)
    
    # Decode the output
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract Role and Score using regex
    role_match = re.search(r'Role:\s*(.*)', generated_text)
    if role_match:
        data["Role"] = role_match.group(1).strip()

    score_match = re.search(r'Score:\s*(\d+)', generated_text)
    if score_match:
        data["Score"] = int(score_match.group(1))
    
    return data

def extract_bulk_info_llm(resume_text):
    if not resume_text:
        return {"Name": "Not mentioned", "Location": "Not mentioned", "Phone": "Not mentioned", "Experience": "Not mentioned", "Fitment Summary": "Not mentioned"}

    prompt = f"""
    You are given a resume. Your task is to strictly retrieve information from the resume text provided and not infer or generate any additional content. If the required information is not present in the resume, return "Not mentioned" without making any assumptions.

    Please extract and return the following information from the resume text:
    1. Name: (The exact name as written in the resume).
    2. Location: (The full address or location as mentioned in the resume).
    3. Phone Number: (The phone number as written in the resume).
    4. Total Experience in Years: (Extract the number of years of experience mentioned in the resume).
    5. Fitment Summary: (Summarize the relevant skills and experience found in the resume).
    """

    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    outputs = model.generate(inputs.input_ids, max_length=200, num_beams=4, early_stopping=True)

    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Extract relevant information using regex
    extracted_info = {"Name": "Not mentioned", "Location": "Not mentioned", "Phone": "Not mentioned", "Experience": "Not mentioned", "Fitment Summary": "Not mentioned"}

    name_match = re.search(r'Name:\s*(.*)', generated_text)
    if name_match:
        extracted_info["Name"] = name_match.group(1).strip()

    location_match = re.search(r'Location:\s*(.*)', generated_text)
    if location_match:
        extracted_info["Location"] = location_match.group(1).strip()

    phone_match = re.search(r'Phone Number:\s*(.*)', generated_text)
    if phone_match:
        extracted_info["Phone"] = phone_match.group(1).strip()

    experience_match = re.search(r'Total Experience in Years:\s*(.*)', generated_text)
    if experience_match:
        extracted_info["Experience"] = experience_match.group(1).strip()

    summary_match = re.search(r'Fitment Summary:\s*(.*)', generated_text, re.DOTALL)
    if summary_match:
        extracted_info["Fitment Summary"] = summary_match.group(1).strip()

    return extracted_info

if __name__ == "__main__":
    resume_folder = "../Resumes"
    job_description_file = "../Role Description.txt"
    skills_file = "../Evaluation Criteria Sheet.xlsx"
    final_excel_path = 'final_output1.xlsx'
    pdfs_to_cleaned_and_extracted_excel(resume_folder, job_description_file, skills_file, final_excel_path)
