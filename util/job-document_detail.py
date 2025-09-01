import os
from supabase import create_client
from dotenv import load_dotenv
import subprocess
import sys

# 🔁 Load .env
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "job-documents"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_all_job_folders():
    try:
        # 🧠 Top-level folders (jobs): ai_engineer/, marketing_head/, etc.
        response = supabase.storage.from_(BUCKET_NAME).list(path="")
        job_folders = [item["name"] for item in response if not item["name"].endswith(".pdf")]

        if not job_folders:
            print("❌ No job folders found.")
            return None

        print("📂 Available Job Folders:\n")
        for idx, folder in enumerate(job_folders, 1):
            print(f"{idx}. {folder}")

        selection = int(input("\n👉 Select a job folder number to view details: "))
        selected_folder = job_folders[selection - 1]
        return selected_folder
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def list_resumes_and_jd(job_folder):
    print(f"\n📄 Checking contents in '{job_folder}'...\n")

    # Check if JD exists
    try:
        jd_response = supabase.storage.from_(BUCKET_NAME).list(job_folder)
        jd_files = [item["name"] for item in jd_response if item["name"].endswith(".pdf")]

        if jd_files:
            print("📄 Job Description(s):")
            for jd in jd_files:
                url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"{job_folder}/{jd}")
                print(f"• {jd} → {url}")
        else:
            print("📭 No job description found.")

    except Exception as e:
        print(f"❌ Error checking JD: {e}")

    # Check resumes
    try:
        resumes_path = f"{job_folder}/resumes"
        resumes_response = supabase.storage.from_(BUCKET_NAME).list(resumes_path)
        resumes = [item["name"] for item in resumes_response if item["name"].endswith(".pdf")]

        if resumes:
            print("\n📁 Resumes:")
            for resume in resumes:
                url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"{resumes_path}/{resume}")
                print(f"• {resume} → {url}")
        else:
            print("\n📭 No resumes found.")

    except Exception as e:
        print(f"❌ Error checking resumes: {e}")

if __name__ == "__main__":
    selected_job = list_all_job_folders()
    if selected_job:
        list_resumes_and_jd(selected_job)
        # --- Call the parsing script with the selected job ---
        script_path = os.path.join(os.path.dirname(__file__), "parsing.py")
        print(f"\n🔄 Now parsing and uploading documents for job: {selected_job}\n")
        subprocess.run([sys.executable, script_path, selected_job])
        # Write to file for main.py
        try:
            with open(".selected_job.txt", "w", encoding="utf-8") as f:
                f.write(selected_job.strip() + "\n")
        except Exception as e:
            print(f"❌ Error writing selected job to file: {e}")
        # Print parseable marker for main.py
        print(f"SELECTED_JOB:{selected_job}")
