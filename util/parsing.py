import os
import sys
import tempfile
from supabase import create_client
from dotenv import load_dotenv
# --- REMOVED THE PROBLEMATIC IMPORT OF parse_pdf ---
# from parsing import parse_pdf # This line caused the circular import

# Define the parse_pdf function directly in this file
def parse_pdf(pdf_path):
    """
    Parses the text content from a PDF file.
    You need to implement the actual PDF parsing logic here.
    Example using pypdf:
    """
    try:
        import pypdf
        with open(pdf_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            text = ""
            for page in reader.pages:
                # Ensure page.extract_text() is not None before appending
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            return text
    except ImportError:
        print("Error: 'pypdf' library not found. Please install it: pip install pypdf")
        return None
    except Exception as e:
        print(f"Error parsing PDF '{pdf_path}': {e}")
        return None


# Load .env from project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SRC_BUCKET = "job-documents"
# No longer using DST_BUCKET; all uploads go to SRC_BUCKET under a 'parsed' subfolder.

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def download_file(bucket, src_path, dst_path):
    data = supabase.storage.from_(bucket).download(src_path)
    with open(dst_path, "wb") as f:
        f.write(data)

def file_exists(bucket, file_path):
    try:
        # Try to list the file in the bucket
        files = supabase.storage.from_(bucket).list(os.path.dirname(file_path))
        return any(f['name'] == os.path.basename(file_path) for f in files)
    except Exception:
        return False

def upload_file(bucket, dst_path, src_path):
    if file_exists(bucket, dst_path):
        print(f"⚠️ Skipping upload (already exists): {dst_path}")
        return
    print(f"Uploading: {dst_path}")
    with open(src_path, "rb") as f:
        supabase.storage.from_(bucket).upload(dst_path, f)
    print(f"✅ Uploaded: {dst_path}")

def process_and_upload(job_folder):
    # List all files in job folder
    jd_files = supabase.storage.from_(SRC_BUCKET).list(job_folder)
    jd_pdfs = [item["name"] for item in jd_files if item["name"].endswith(".pdf")]
    # List all resumes
    resumes_path = f"{job_folder}/resumes"
    resumes = []
    try:
        resumes_files = supabase.storage.from_(SRC_BUCKET).list(resumes_path)
        resumes = [item["name"] for item in resumes_files if item["name"].endswith(".pdf")]
    except Exception: # This bare except is broad, consider catching specific exceptions like StorageException
        pass
    with tempfile.TemporaryDirectory() as tmpdir:
        # Process job description PDFs
        for jd_pdf in jd_pdfs:
            src_path = f"{job_folder}/{jd_pdf}"
            local_pdf = os.path.join(tmpdir, jd_pdf)
            download_file(SRC_BUCKET, src_path, local_pdf)
            # parse_pdf is now directly callable as it's defined in this file
            parsed_text = parse_pdf(local_pdf)
            txt_name = os.path.splitext(jd_pdf)[0] + ".txt"
            local_txt = os.path.join(tmpdir, txt_name)
            with open(local_txt, "w", encoding="utf-8") as f:
                f.write(parsed_text or "")
            # Save JD .txt directly under the job folder
            dst_path = f"{job_folder}/{txt_name}"
            upload_file(SRC_BUCKET, dst_path, local_txt)
        # Process resumes
        for resume_pdf in resumes:
            src_path = f"{job_folder}/resumes/{resume_pdf}"
            local_pdf = os.path.join(tmpdir, resume_pdf)
            download_file(SRC_BUCKET, src_path, local_pdf)
            # parse_pdf is now directly callable
            parsed_text = parse_pdf(local_pdf)
            txt_name = os.path.splitext(resume_pdf)[0] + ".txt"
            local_txt = os.path.join(tmpdir, txt_name)
            with open(local_txt, "w", encoding="utf-8") as f:
                f.write(parsed_text or "")
            parsed_folder = f"{job_folder}/parsed"
            dst_path = f"{parsed_folder}/{txt_name}"
            upload_file(SRC_BUCKET, dst_path, local_txt)

def main():
    if len(sys.argv) != 2:
        print("Usage: python util/parsing.py <job_folder>")
        sys.exit(1)
    job_folder = sys.argv[1]
    process_and_upload(job_folder)

if __name__ == "__main__":
    main()