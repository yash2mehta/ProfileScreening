from optimize_03 import *
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from haystack.document_stores import FAISSDocumentStore
from haystack.nodes import DensePassageRetriever, FARMReader
from haystack.pipelines import ExtractiveQAPipeline

# Initialize FAISS document store
document_store = FAISSDocumentStore(faiss_index_factory_str="Flat")

# Add documents (resumes, job descriptions, etc.) to FAISS
def add_documents_to_store(resume_folder, job_description_file):
    documents = []
    # Loop through resumes and job descriptions, load them into the document store
    for filename in os.listdir(resume_folder):
        file_path = os.path.join(resume_folder, filename)
        resume_text = extract_text_from_file(file_path)
        documents.append({'content': resume_text, 'meta': {'name': filename}})
    
    job_description_text = extract_text_from_file(job_description_file)
    documents.append({'content': job_description_text, 'meta': {'type': 'job_description'}})

    document_store.write_documents(documents)

# Initialize Retriever and Reader for the RAG process
retriever = DensePassageRetriever(
    document_store=document_store,
    query_embedding_model="facebook/dpr-question_encoder-single-nq-base",
    passage_embedding_model="facebook/dpr-ctx_encoder-single-nq-base"
)
reader = FARMReader(model_name_or_path="deepset/roberta-base-squad2")

# Update document store with embeddings
document_store.update_embeddings(retriever)

# Define RAG pipeline
pipeline = ExtractiveQAPipeline(reader, retriever)

# Use the pipeline to retrieve relevant documents and answer questions based on resume
def retrieve_relevant_docs(query, top_k=3):
    return pipeline.run(query=query, params={"Retriever": {"top_k": top_k}, "Reader": {"top_k": 1}})

# Modify your existing `extract_role_score` function to use RAG
def extract_role_score_with_rag(resume_text, job_description, model=model):
    # Retrieve relevant job description parts using RAG
    query = f"What role does this resume fit? {resume_text}"
    retrieved_results = retrieve_relevant_docs(query)

    # Combine retrieved job description context with resume text
    combined_text = resume_text + "\n\n" + retrieved_results['answers'][0].answer

    # Pass the combined text into the LLM model for final role scoring
    prompt = """
    You are tasked with evaluating a candidate based on the provided resume and retrieved job description. Your task is to produce exactly two outputs: 

    1. **Role**: Based on the job description, identify which role this job description is targeted to. Use only one word or phrase for the role.
    2. **Score**: A numerical score (0-100) that represents how well the resume aligns with the job description.

    ### Inputs:
    Resume Text: {combined_text}

    ### Important Instructions:
    - ONLY use information from the job description to infer the role.
    - ONLY use the resume to determine how well the candidate fits the role (for scoring).
    - The **Role** must be a SINGLE word or phrase, with no additional details.
    - The **Score** must be a NUMBER between 0 and 100 based on the alignment between the resume and job description.
    """

    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    response = chain.invoke({
        'combined_text': combined_text,
    })

    # Extract Role and Score using regex (similar to your original function)
    role_match = re.search(r'Role:\s*(.*)', response)
    score_match = re.search(r'Score:\s*(\d+)', response)

    return {
        "Role": role_match.group(1).strip() if role_match else "Not mentioned",
        "Score": int(score_match.group(1)) if score_match else "Not generated"
    }

# Call the RAG-enhanced extraction function
resume_folder = "../Resumes"
job_description_file = "../JobDesc.txt"
add_documents_to_store(resume_folder, job_description_file)

# Now you can use RAG in your bulk processing function, as demonstrated:
# pdfs_to_cleaned_and_extracted_excel(resume_folder, job_description_file, skills_file, final_excel_path)
