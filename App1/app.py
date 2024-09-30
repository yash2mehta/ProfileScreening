import os
import shutil
import pandas as pd
from werkzeug.utils import secure_filename
from utils import pdfs_to_cleaned_and_extracted_excel
from flask import Flask, render_template, request, redirect, url_for, send_file

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESUME_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'],"Resumes")
app.config['PROCESSED_FOLDER'] = 'processed'


# Function to clear the folder if it already exists
def clear_folder(folder_path):
    if os.path.exists(folder_path):
        # List all files in the folder and delete them
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Delete the file
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Delete the directory and its contents
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

# Ensure the uploads and processed folders exist, and clear them if they do
clear_folder(app.config['UPLOAD_FOLDER'])
clear_folder(app.config['RESUME_FOLDER'])
clear_folder(app.config['PROCESSED_FOLDER'])

# Create the directories if they do not exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['PROCESSED_FOLDER']):
    os.makedirs(app.config['PROCESSED_FOLDER'])

if not os.path.exists(app.config['RESUME_FOLDER']):
    os.makedirs(app.config['RESUME_FOLDER'])


@app.route('/')
def index():
    return render_template('index.html', xls_file=None, table_data=None)  # Pass table_data as None initially

@app.route('/upload', methods=['POST'])
def upload_files():

    # Intake Files
    job_description_file = request.files.get('job_description')
    eval_template_file = request.files.get('eval_template')
    resumes_files = request.files.getlist('resumes')  # Handle multiple resumes

    # Ensure files are uploaded
    if not job_description_file or not eval_template_file or not resumes_files:
        return redirect(request.url)

    # Save the job description and evaluation template
    job_description_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(job_description_file.filename))
    eval_template_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(eval_template_file.filename))
    job_description_file.save(job_description_path)
    eval_template_file.save(eval_template_path)

    # Save each resume
    resume_paths = []
    for resume_file in resumes_files:
        resume_path = os.path.join(app.config['RESUME_FOLDER'], secure_filename(resume_file.filename))
        resume_file.save(resume_path)
        resume_paths.append(resume_path)

    # Define the path for the processed XLS file
    xls_file_path = os.path.join(app.config['PROCESSED_FOLDER'], 'processed_profiles.xlsx')

    # Process the resumes and generate the XLS file
    for update in pdfs_to_cleaned_and_extracted_excel(app.config['RESUME_FOLDER'], job_description_path, eval_template_path, final_excel_path=xls_file_path):
        print(update)

    # Read the processed XLS file and convert it to HTML
    df = pd.read_excel(xls_file_path)
    table_data = df.to_html(classes='table table-striped', index=False)

    # Ensure the uploads and processed folders exist, and clear them if they do
    clear_folder(app.config['RESUME_FOLDER'])
    
    # Render the same page but now with the table data and XLS file available for download
    return render_template('index.html', xls_file='processed_profiles.xlsx', table_data=table_data)

# Serve the XLS file for download
@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    response = send_file(file_path, as_attachment=True)
    clear_folder(app.config['PROCESSED_FOLDER'])
    return response

if __name__ == '__main__':
    app.run(debug=True)
