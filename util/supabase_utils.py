import os
from supabase import create_client

def upload_text_to_supabase(bucket: str, dest_path: str, content: str):
    """
    Uploads text content to Supabase Storage, overwriting any existing file at dest_path.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url, supabase_key)
    data = content.encode("utf-8")
    # Remove if file exists (Supabase overwrites by default, but this is safer for some SDKs)
    try:
        supabase.storage.from_(bucket).remove([dest_path])
    except Exception:
        pass  # Ignore if file does not exist
    resp = supabase.storage.from_(bucket).upload(dest_path, data, {"content-type": "application/json"})
    if not resp:
        raise RuntimeError(f"Failed to upload {dest_path} to Supabase.")
    return resp
