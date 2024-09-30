# Resume Screening Application

This repository contains multiple applications developed using Flask and Python. These applications are designed for profile screening, which involves collecting multiple resumes, job descriptions, and required skills, and then selecting the best resumes based on the provided criteria.

## Overview

Currently, the **best performing application** is **App 5**. It is recommended that users download **App 5** for the most accurate results. This application allows you to screen resumes effectively, using job descriptions and skill sets to identify the best matches.

### Resources

The following resources are available within the repository:
- **Resume Folder**: Contains multiple resumes that can be used as a test set.
- **Job Descriptions**: Files containing relevant job descriptions.
- **Skills File**: Contains the skills required for the job.

### Setting Up the Application

1. **Clone or Download the Repository**:  
   You can either download the entire repository or just **App 5** to get started.

2. **Download Olama**:  
   Visit the official website to download [Ollama](https://ollama.com/download/OllamaSetup.exe). You will need it to pull the specific model required for the application.

3. **Pull the Model**:  
   We are using the **phi3 model** in this case. Once you have downloaded the executable file for Olama, run the following command in your terminal to pull the model:

   ```bash
   olama pull phi3
   ```

4. **Check Environment Requirements**:  
   Ensure that all the necessary dependencies are installed by checking the provided `requirements.txt` file. You can install the dependencies as follows:

   ```bash
   pip install -r requirements.txt --ignore-existing
   ```

   It is advised to create a virtual environment to avoid conflicts between different packages.

### Running the Application

Once all dependencies are installed, you can run the application using the following command:

```bash
python app.py
```

This will start the Flask application for profile screening. You can then begin using the interface to upload resumes, job descriptions, and skill sets.

### Additional Information

- Ensure that the **resume folder**, **job description files**, and **skills files** are correctly placed in the respective directories for proper execution.
- The application is configured to use the **phi3 model**, which is vital for its performance.
