import os
import sys
import subprocess
import logging
from dotenv import load_dotenv
from supabase import create_client
from util.supabase_utils import upload_text_to_supabase
from langgraph.graph import StateGraph, END, START # Keep START for clarity, though its explicit edge is removed
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from typing import TypedDict
import traceback
import tiktoken
from collections import defaultdict

load_dotenv()

# --- Token/cost tracking utilities ---
TOKEN_PRICING = {
    'input': 0.0005,   # $0.50 per 1K tokens (gpt-3.5-turbo example)
    'output': 0.0015   # $1.50 per 1K tokens
}

def count_tokens(text, model="gpt-4"):
    try:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        # fallback: 1 token ≈ 4 chars
        return max(1, len(text) // 4)

token_stats = defaultdict(lambda: {'input': 0, 'output': 0, 'calls': 0})

# Helper to update stats
def add_token_stats(agent, input_tokens, output_tokens):
    token_stats[agent]['input'] += input_tokens
    token_stats[agent]['output'] += output_tokens
    token_stats[agent]['calls'] += 1

# --- Prompt Loading Utilities ---
def load_prompt(prompt_path):
    try:
        with open(prompt_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load prompt '{prompt_path}': {e}")
        return None

def validate_state(required_keys, state):
    missing = [k for k in required_keys if k not in state]
    if missing:
        raise ValueError(f"Missing required state keys: {missing}")

def log_agent_step(agent_name, state, output_key=None):
    pass

# --- State Schema ---
class ResumeState(TypedDict, total=False):
    job_description: str
    resume_text: str
    job_requirements: str
    parsed_resume: str
    compatibility_score: str
    audit_result: str

# --- Agent 1: Job Description ---
JD_PROMPT_PATH = "prompts/job_description_prompt.txt"
JD_PROMPT = load_prompt(JD_PROMPT_PATH)
jd_llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    base_url="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

def job_description_agent(state: ResumeState) -> ResumeState:
    try:
        validate_state(["job_description"], state)
        if JD_PROMPT is None:
            raise RuntimeError(f"Prompt not loaded from {JD_PROMPT_PATH}")
        prompt = JD_PROMPT.replace("{{job_description}}", state["job_description"])
        import re, json
        response = jd_llm.invoke(prompt)
        # --- Token/cost tracking ---
        input_tokens = count_tokens(prompt, model="llama-3.1-8b-instant")
        output_tokens = count_tokens(response.content, model="llama-3.1-8b-instant")
        add_token_stats("job_description_agent", input_tokens, output_tokens)
        # Extract JSON from LLM output
        json_match = re.search(r'\{[\s\S]*\}', response.content)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(0))
                state["job_requirements"] = json.dumps(parsed_json)
            except Exception as e:
                state["job_requirements"] = response.content
        else:
            state["job_requirements"] = response.content
        log_agent_step("JobDescriptionAgent", state, output_key="job_requirements")
        return state
    except Exception as e:
        logging.error(f"[JobDescriptionAgent] Exception: {e}\n{traceback.format_exc()}")
        raise

# --- Agent 2: Resume Parser ---
RESUME_PROMPT_PATH = "prompts/resume_parser_prompt.txt"
RESUME_PROMPT = load_prompt(RESUME_PROMPT_PATH)
resume_llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    base_url="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

def resume_parser_agent(state: ResumeState) -> ResumeState:
    try:
        validate_state(["resume_text"], state)
        if RESUME_PROMPT is None:
            raise RuntimeError(f"Prompt not loaded from {RESUME_PROMPT_PATH}")
        prompt = RESUME_PROMPT.replace("{{resume_text}}", state["resume_text"])
        import re, json
        response = resume_llm.invoke(prompt)
        # --- Token/cost tracking ---
        input_tokens = count_tokens(prompt, model="llama-3.1-8b-instant")
        output_tokens = count_tokens(response.content, model="llama-3.1-8b-instant")
        add_token_stats("resume_parser_agent", input_tokens, output_tokens)
        json_match = re.search(r'\{[\s\S]*\}', response.content)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(0))
                state["parsed_resume"] = json.dumps(parsed_json)
            except Exception as e:
                state["parsed_resume"] = response.content
        else:
            state["parsed_resume"] = response.content
        log_agent_step("ResumeParserAgent", state, output_key="parsed_resume")
        return state
    except Exception as e:
        logging.error(f"[ResumeParserAgent] Exception: {e}\n{traceback.format_exc()}")
        raise

# --- Agent 3: Compatibility Analyzer ---
COMP_PROMPT_PATH = "prompts/compatibility_prompt.txt"
COMP_PROMPT = load_prompt(COMP_PROMPT_PATH)
compat_llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    base_url="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

def compatibility_analyzer_agent(state: ResumeState) -> ResumeState:
    try:
        validate_state(["job_requirements", "parsed_resume"], state)
        if COMP_PROMPT is None:
            raise RuntimeError(f"Prompt not loaded from {COMP_PROMPT_PATH}")
        prompt = COMP_PROMPT
        prompt = prompt.replace("{{job_requirements}}", state["job_requirements"])
        prompt = prompt.replace("{{parsed_resume}}", state["parsed_resume"])
        import re, json
        response = compat_llm.invoke(prompt)
        # --- Token/cost tracking ---
        input_tokens = count_tokens(prompt, model="llama-3.3-70b-versatile")
        output_tokens = count_tokens(response.content, model="llama-3.3-70b-versatile")
        add_token_stats("compatibility_analyzer_agent", input_tokens, output_tokens)
        json_match = re.search(r'\{[\s\S]*\}', response.content)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(0))
                state["compatibility_score"] = json.dumps(parsed_json)
            except Exception as e:
                state["compatibility_score"] = response.content
        else:
            state["compatibility_score"] = response.content

        log_agent_step("CompatibilityAnalyzerAgent", state, output_key="compatibility_score")
        return state
    except Exception as e:
        logging.error(f"[CompatibilityAnalyzerAgent] Exception: {e}\n{traceback.format_exc()}")
        raise

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PARSED_FOLDER = "parsed"

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("SUPABASE_URL or SUPABASE_KEY not set in environment.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_job_document_detail():
    """
    Interactive job and resume selection and parsing workflow, integrated directly (no subprocess).
    Returns the selected job folder name after parsing/uploading.
    """
    # List all job folders from Supabase
    try:
        response = supabase.storage.from_("job-documents").list("")
        job_folders = [item["name"] for item in response if not item["name"].endswith(".pdf")]
        if not job_folders:
            print("❌ No job folders found.")
            sys.exit(1)
        print("\n📂 Available Job Folders:\n")
        for idx, folder in enumerate(job_folders, 1):
            print(f"{idx}. {folder}")
        selection = int(input("\n👉 Select a job folder number to view details: "))
        selected_job = job_folders[selection - 1]
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # List job descriptions and resumes for the selected job
    print(f"\n📄 Checking contents in '{selected_job}'...\n")
    try:
        jd_response = supabase.storage.from_("job-documents").list(selected_job)
        jd_files = [item["name"] for item in jd_response if item["name"].endswith(".pdf")]
        if jd_files:
            print("📄 Job Description(s):")
            for jd in jd_files:
                url = supabase.storage.from_("job-documents").get_public_url(f"{selected_job}/{jd}")
                print(f"• {jd} → {url}")
        else:
            print("📭 No job description found.")
    except Exception as e:
        print(f"❌ Error checking JD: {e}")
    try:
        resumes_path = f"{selected_job}/resumes"
        resumes_response = supabase.storage.from_("job-documents").list(resumes_path)
        resumes = [item["name"] for item in resumes_response if item["name"].endswith(".pdf")]
        if resumes:
            print("\n📁 Resumes:")
            for resume in resumes:
                url = supabase.storage.from_("job-documents").get_public_url(f"{resumes_path}/{resume}")
                print(f"• {resume} → {url}")
        else:
            print("\n📭 No resumes found.")
    except Exception as e:
        print(f"❌ Error checking resumes: {e}")

    # Check if parsing is needed (if .txt files are missing)
    from util.parsing import process_and_upload
    parsed_folder = f"{selected_job}/parsed"
    try:
        parsed_txts = supabase.storage.from_("job-documents").list(parsed_folder)
        jd_txts = supabase.storage.from_("job-documents").list(selected_job)
        has_jd_txt = any(f["name"].endswith(".txt") for f in jd_txts)
        has_resume_txt = any(f["name"].endswith(".txt") for f in parsed_txts)
    except Exception:
        has_jd_txt = False
        has_resume_txt = False
    if not has_jd_txt or not has_resume_txt:
        print(f"\n🔄 Now parsing and uploading documents for job: {selected_job}\n")
        try:
            process_and_upload(selected_job)
        except Exception as e:
            print(f"❌ Error during parsing/upload: {e}")
            sys.exit(1)
    else:
        print(f"\n✅ Parsed text files already exist for job: {selected_job}\n")
    return selected_job

SRC_BUCKET = "job-documents"

def list_txt_files(job_folder):
    """
    List .txt files for job description and resumes for the selected job.
    Returns (jd_txt_path, [resume_txt_paths])
    """
    try:
        # List JD .txt directly under job folder
        jd_files = supabase.storage.from_(SRC_BUCKET).list(job_folder)
        # List resumes .txt in parsed subfolder ONLY
        parsed_folder = f"{job_folder}/parsed"
        resume_files = supabase.storage.from_(SRC_BUCKET).list(parsed_folder)
    except Exception as e:
        logging.error(f"Failed to list files in bucket: {e}")
        sys.exit(1)
    # Find the job description txt (JD usually named like jobdesc.txt or similar)
    jd_txt = None
    for f in jd_files:
        fname = f["name"]
        if fname.endswith(".txt"):
            # Heuristic: if file name contains 'job' or 'jd', treat as JD
            if "job" in fname.lower() or "jd" in fname.lower():
                jd_txt = f"{job_folder}/{fname}"
                break
    # List all resume .txt files in parsed subfolder ONLY
    resume_txts = [f"{parsed_folder}/{f['name']}" for f in resume_files if f["name"].endswith(".txt")]
    if not jd_txt or not resume_txts:
        print("No job description or resumes found!")
        sys.exit(1)
    return jd_txt, resume_txts

def download_txt(bucket, src_path):
    try:
        data = supabase.storage.from_(bucket).download(src_path)
        return data.decode("utf-8")
    except Exception as e:
        # Handle Supabase StorageException: 'Object not found'
        if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict):
            err = e.args[0]
            if err.get('statusCode') == 400 and err.get('error') == 'not_found':
                print(f"❌ File not found in Supabase: {src_path}")
                return None
        print(f"❌ Error downloading file from Supabase: {src_path}\n{e}")
        return None

from langchain_openai import ChatOpenAI

def audit_agent(state: ResumeState) -> ResumeState:
    import os, json
    # Load prompt from prompts/audit_agent.txt (corrected)
    prompt_path = "prompts/audit_agent.txt"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            audit_prompt = f.read()
    except Exception as e:
        print(f"[AuditAgent] Failed to load prompt from '{prompt_path}': {e}")
        state["audit_result"] = json.dumps({"error": f"Prompt load failed: {prompt_path} not found or unreadable."})
        return state
    job_requirements = state.get("job_requirements", "{}")
    parsed_resume = state.get("parsed_resume", "{}")
    compatibility_score = state.get("compatibility_score", "{}")
    prompt = audit_prompt
    prompt = prompt.replace("{{job_requirements}}", job_requirements)
    prompt = prompt.replace("{{parsed_resume}}", parsed_resume)
    prompt = prompt.replace("{{compatibility_result}}", compatibility_score)
    llm = ChatOpenAI(
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        openai_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1
    )
    try:
        # Debug: print prompt content
        print("[DEBUG] AuditAgent prompt preview:\n", prompt[:1000])
        response = llm.invoke(prompt)
        # Always print the full raw LLM response for debugging
        print("[DEBUG] AuditAgent FULL RAW response:", response.content)
        # Store raw LLM response for printing after [AuditAgent Output]:
        state["audit_agent_raw_response"] = response.content
        # Token/cost tracking
        input_tokens = count_tokens(prompt, model="llama-3.3-70b-versatile")
        output_tokens = count_tokens(response.content, model="llama-3.3-70b-versatile")
        add_token_stats("audit_agent", input_tokens, output_tokens)
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response.content)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(0))
                state["audit_result"] = json.dumps(parsed_json, ensure_ascii=False)
            except Exception:
                state["audit_result"] = response.content
        else:
            state["audit_result"] = response.content
    except Exception as e:
        state["audit_result"] = json.dumps({"error": str(e)})
    return state

def create_resume_filtering_graph():
    """
    Create and return the compiled LangGraph for resume filtering, including the audit agent.
    """
    graph = StateGraph(ResumeState)
    graph.add_node("job_description_agent", job_description_agent)
    graph.add_node("resume_parser_agent", resume_parser_agent)
    graph.add_node("compatibility_analyzer_agent", compatibility_analyzer_agent)
    graph.add_node("audit_agent", audit_agent)
    graph.set_entry_point("job_description_agent")
    graph.add_edge("job_description_agent", "resume_parser_agent")
    graph.add_edge("resume_parser_agent", "compatibility_analyzer_agent")
    graph.add_edge("compatibility_analyzer_agent", "audit_agent")
    graph.add_edge("audit_agent", END)
    return graph.compile()

def main():
    print("\n==== Resume Filtering Agentic Workflow ====")
    # 1. Run job-document_detail.py and trigger parsing
    job_folder = run_job_document_detail()
    print(f"Selected job: {job_folder}")

    # 2. Fetch parsed .txt files from Supabase
    jd_txt_path, resumes_txt_paths = list_txt_files(job_folder)
    jd_txt_content = download_txt(SRC_BUCKET, jd_txt_path)
    parsed_folder = f"{job_folder}/parsed"

    # 3. Run job_description_agent ONCE and cache job_requirements
    import copy
    if jd_txt_content is None:
        print(f"❌ Could not load job description file: {jd_txt_path}. Please check if the file exists in Supabase and try again.")
        sys.exit(1)
    job_desc_state = {"job_description": jd_txt_content}
    job_desc_state = job_description_agent(job_desc_state)
    job_requirements = job_desc_state.get("job_requirements", "{}")

    # --- Save job requirements JSON to Supabase ---
    # Use the job description PDF file name (without extension) as the JSON name
    jd_pdf_name = None
    jd_files = supabase.storage.from_(SRC_BUCKET).list(job_folder)
    for f in jd_files:
        fname = f["name"]
        if fname.endswith(".pdf"):
            jd_pdf_name = os.path.splitext(fname)[0]
            break
    if jd_pdf_name:
        job_json_name = f"{jd_pdf_name}.json"
    else:
        job_json_name = "job_requirements.json"
    json_path = f"{job_folder}/{job_json_name}"
    try:
        upload_text_to_supabase('job-documents', json_path, job_requirements)
        print(f"[INFO] Uploaded job requirements JSON to Supabase: {json_path}")
    except Exception as e:
        print(f"[ERROR] Failed to upload job requirements JSON to Supabase: {json_path}\n{e}")

    # 4. Create the graph for resumes (starting from resume_parser_agent if job_requirements is present)
    def create_resume_graph():
        graph = StateGraph(ResumeState)
        graph.add_node("resume_parser_agent", resume_parser_agent)
        graph.add_node("compatibility_analyzer_agent", compatibility_analyzer_agent)
        graph.add_node("audit_agent", audit_agent)
        graph.set_entry_point("resume_parser_agent")
        graph.add_edge("resume_parser_agent", "compatibility_analyzer_agent")
        graph.add_edge("compatibility_analyzer_agent", "audit_agent")
        graph.add_edge("audit_agent", END)
        return graph.compile()

    resume_graph = create_resume_graph()

    # 5. For each resume, run agentic workflow
    results = []
    for resume_txt_path in resumes_txt_paths:
        try:
            resume_txt_content = download_txt(SRC_BUCKET, resume_txt_path)
        except Exception as e:
            logging.error(f"Error downloading resume {resume_txt_path}: {e}")
            continue

        # State for workflow (reuse job_requirements)
        state = {
            "job_description": jd_txt_content,
            "resume_text": resume_txt_content,
            "job_requirements": job_requirements
        }

        try:
            validate_state(["job_description", "resume_text", "job_requirements"], state)
        except Exception as e:
            logging.error(f"State validation error: {e}")
            continue

        # Run graph and print agentic output
        try:
            final_state = resume_graph.invoke(state)
            import json
            print("\n============================================================")
            print(f"RESUME: {resume_txt_path}")
            print("------------------------------------------------------------")
            print("[Job Requirements]")
            try:
                job_req = json.loads(final_state.get("job_requirements", "{}"))
                print(json.dumps(job_req, indent=2, ensure_ascii=False))
            except Exception:
                print(final_state.get("job_requirements", "{}"))
            print("------------------------------------------------------------")
            print("[Parsed Resume]")
            try:
                parsed_resume = json.loads(final_state.get("parsed_resume", "{}"))
                print(json.dumps(parsed_resume, indent=2, ensure_ascii=False))
            except Exception:
                print(final_state.get("parsed_resume", "{}"))
            print("------------------------------------------------------------")
            print("[Compatibility Result]")
            try:
                comp_result = json.loads(final_state.get("compatibility_score", "{}"))
                print(json.dumps(comp_result, indent=2, ensure_ascii=False))
            except Exception:
                comp_result = final_state.get("compatibility_score", "{}")
                print(comp_result)

            print("------------------------------------------------------------")
            # --- Print audit agent output ---
            print("[AuditAgent Output]:")
            audit_result = state.get("audit_result", "{}")
            try:
                parsed_json = json.loads(audit_result)
                print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
            except Exception:
                print(audit_result)
            results.append((resume_txt_path, final_state.get("compatibility_score", "N/A")))
        except Exception as e:
            logging.error(f"Error in agentic workflow for resume {resume_txt_path}: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")
            continue

    # --- Print token/cost summary table ---
    AGENT_PRICING = {
        "job_description_agent": {"input": 0.0005, "output": 0.0015},
        "resume_parser_agent": {"input": 0.0005, "output": 0.0015},
        "compatibility_analyzer_agent": {"input": 0.0005, "output": 0.0015},
        "audit_agent": {"input": 0.0005, "output": 0.0015},
    }
    print("==================== TOKEN & COST SUMMARY ====================")
    print(f"{'Agent':<28}{'Calls':>7}{'Input':>12}{'Output':>12}{'Cost($)':>12}")
    print("-"*71)
    total_cost = 0.0
    for agent in ["job_description_agent", "resume_parser_agent", "compatibility_analyzer_agent", "audit_agent"]:
        stats = token_stats[agent]
        cost = (
            stats["input"] * AGENT_PRICING[agent]["input"] +
            stats["output"] * AGENT_PRICING[agent]["output"]
        ) / 1000
        total_cost += cost
        print(f"{agent:<28}{stats['calls']:>7}{stats['input']:>12}{stats['output']:>12}{cost:>12.4f}")
    print("-"*71)
    print(f"{'TOTAL':<28}{sum(token_stats[a]['calls'] for a in AGENT_PRICING):>7}{sum(token_stats[a]['input'] for a in AGENT_PRICING):>12}{sum(token_stats[a]['output'] for a in AGENT_PRICING):>12}{total_cost:>12.4f}")
    print("============================================================")

    if not results:
        print("No compatibility scores generated!")


if __name__ == "__main__":
    main()