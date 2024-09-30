import os
import shutil
import pandas as pd
from werkzeug.utils import secure_filename
from utils import pdfs_to_cleaned_and_extracted_excel
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify

app = Flask(__name__)
app.config['MAIN_DIR'] = 'data'
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['MAIN_DIR'], 'uploads')
app.config['RESUME_FOLDER'] = os.path.join(app.config['MAIN_DIR'], "resumes")
app.config['PROCESSED_FOLDER'] = os.path.join(app.config['MAIN_DIR'], 'processed')

# Function to clear the folder if it already exists
def clear_folder(folder_path):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['PROCESSED_FOLDER']):
    os.makedirs(app.config['PROCESSED_FOLDER'])

if not os.path.exists(app.config['RESUME_FOLDER']):
    os.makedirs(app.config['RESUME_FOLDER'])


@app.route('/')
def index():
    
    if len(os.listdir(app.config['PROCESSED_FOLDER']))>=1:
        xls_file_path = os.path.join(app.config['PROCESSED_FOLDER'], 'processed_profiles.xlsx')
    
        # Read the processed XLS file and convert it to HTML
        df = pd.read_excel(xls_file_path)
        table_data = df.to_html(classes='table table-striped', index=False)
        
        roles_data = sorted(list(set(df['Role'])))
        roles_data.insert(0, 'All Rows')
        app.config['ROLES'] = roles_data

        return render_template('selected_profiles.html', xls_file='processed_profiles.xlsx', table_data=table_data, roles_data=roles_data)
    
    return render_template('selected_profiles.html')

@app.route('/job_desc')
def job_desc():
    job_description_file, skills_file = None, None
    for file_name in os.listdir(app.config['UPLOAD_FOLDER']):

        if file_name.endswith('.txt'):
            job_description_file = file_name
        if file_name.endswith('.xlsx'):
            skills_file = file_name
    if job_description_file and skills_file:
        return render_template('job_desc.html', job_description_file=job_description_file, skills_file=skills_file)
    else:
        return render_template('job_desc.html')

@app.route('/selected_profiles')
def selected_profiles():
    if len(os.listdir(app.config['PROCESSED_FOLDER']))>=1:
        xls_file_path = os.path.join(app.config['PROCESSED_FOLDER'], 'processed_profiles.xlsx')
    
        # Read the processed XLS file and convert it to HTML
        df = pd.read_excel(xls_file_path)
        table_data = df.to_html(classes='table table-striped', index=False)
        
        roles_data = sorted(list(set(df['Role'])))
        roles_data.insert(0, 'All Rows')
        app.config['ROLES'] = roles_data
        
        return render_template('selected_profiles.html', xls_file='processed_profiles.xlsx', table_data=table_data, roles_data=roles_data)
    return render_template('selected_profiles.html')  # Render the selected profiles page

@app.route('/upload_resumes')
def upload_resumes():
    if os.path.exists(app.config['RESUME_FOLDER']):
        return render_template('upload_resumes.html', resumes=len(os.listdir(app.config['RESUME_FOLDER'])))

@app.route('/upload', methods=['POST'])
def upload_resume_files():
    # Intake Files
    resumes_files = request.files.getlist('resumes')  # Handle multiple resumes

    # Ensure files are uploaded
    if not resumes_files:
        return redirect(request.url)

    # Save each resume
    resume_paths = []
    for resume_file in resumes_files:
        resume_path = os.path.join(app.config['RESUME_FOLDER'], secure_filename(resume_file.filename))
        resume_file.save(resume_path)
        resume_paths.append(resume_path)

    return render_template('selected_profiles.html')

@app.route('/job_desc', methods=['GET', 'POST'])
def upload_files():
    clear_folder(app.config['UPLOAD_FOLDER'])

    job_description_file = None
    skills_file = None
    
    # If it's a POST request, handle file uploads
    if request.method == 'POST':
        job_description = request.files.get('jobDesc')
        skills = request.files.get('skills')

        # Save job description file if provided
        if job_description:
            job_desc_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(job_description.filename))
            job_description.save(job_desc_path)
            job_description_file = job_description.filename
            app.config['JOB_DESCRIPTION'] = job_description_file


        # Save skills file if provided
        if skills:
            skills_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(skills.filename))
            skills.save(skills_path)
            skills_file = skills.filename
            app.config['EVAL_TEMPLATE'] = skills_file


    # Check if files already exist in the UPLOAD_FOLDER (if GET or POST request)
    if os.path.exists(app.config['JOB_DESCRIPTION']):
        job_description_file = os.path.basename(app.config['JOB_DESCRIPTION'])

    if os.path.exists(app.config['EVAL_TEMPLATE']):
        skills_file = os.path.basename(app.config['EVAL_TEMPLATE'])

    return render_template('job_desc.html', job_description_file=job_description_file, skills_file=skills_file)

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    response = send_file(file_path, as_attachment=True)
    clear_folder(app.config['PROCESSED_FOLDER'])
    return response

@app.route('/process_data', methods=['POST'])
def process_data():

    job_description_path, eval_template_path = None, None
    for file_name in os.listdir(app.config['UPLOAD_FOLDER']):

        if file_name.endswith('.txt'):
            job_description_path = os.path.join(app.config['UPLOAD_FOLDER'],file_name)
        if file_name.endswith('.xlsx'):
            eval_template_path = os.path.join(app.config['UPLOAD_FOLDER'],file_name)

    # If either path is None, handle the error
    if not job_description_path or not eval_template_path:
        error_message = "Job Description or Evaluation Template is not uploaded."
        return render_template('selected_profiles.html', error_message=error_message)
    
    if len(os.listdir(app.config['RESUME_FOLDER']))<=0:
        error_message = "Resumes not uploaded."
        return render_template('selected_profiles.html', error_message=error_message)
    
    xls_file_path = os.path.join(app.config['PROCESSED_FOLDER'], 'processed_profiles.xlsx')

    
    # Process the resumes and generate the XLS file
    pdfs_to_cleaned_and_extracted_excel(app.config['RESUME_FOLDER'], job_description_path, eval_template_path, final_excel_path=xls_file_path)

    # Read the processed XLS file and convert it to HTML
    df = pd.read_excel(xls_file_path)
    table_data = df.to_html(classes='table table-striped', index=False)
    
    # Render the same page but now with the table data and XLS file available for download
    roles_data = sorted(list(set(df['Role'])))  # Remove duplicates and sort the roles
    roles_data.insert(0, 'All Rows')  # Ensure "All Rows" is always the first option
    app.config['ROLES'] = roles_data  # Save roles in app config
    return render_template('selected_profiles.html', xls_file='processed_profiles.xlsx', table_data=table_data, roles_data=roles_data)

# Clear uploads route
@app.route('/clear_uploads', methods=['POST'])
def clear_uploads():
    try:
        clear_folder(app.config['RESUME_FOLDER'])
        return jsonify({"status": "success", "message": "Uploads cleared successfully!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_data', methods=['POST'])
def clear_data():
    try:
        clear_folder(app.config['PROCESSED_FOLDER'])
        return jsonify({"status": "success", "message": "Prev. Data cleared successfully!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_jobdesc_skills', methods=['POST'])
def clear_jobdesc_skills():
    try:
        # Clear the upload folder
        clear_folder(app.config['UPLOAD_FOLDER'])
        
        # Return JSON response with status and cleared HTML
        return jsonify({
            "status": "success",
            "message": "Files cleared successfully.",
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/filter_by_role', methods=['POST'])
def filter_by_role():
    selected_role = request.form.get('role')
    xls_file_path = os.path.join(app.config['PROCESSED_FOLDER'], 'processed_profiles.xlsx')
    filtered_profiles = pd.read_excel(xls_file_path)

    if selected_role!="All Rows":
        filtered_profiles = filtered_profiles[filtered_profiles['Role'] == selected_role]
        
    table_data = filtered_profiles.to_html(classes='table table-striped', index=False)

    # Pass the filtered data to the template
    return render_template('selected_profiles.html', xls_file='processed_profiles.xlsx', table_data=table_data, roles_data=app.config['ROLES'])


if __name__ == "__main__":
    app.run(debug=True)
