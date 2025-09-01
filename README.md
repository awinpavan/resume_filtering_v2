# 📄 Resume Filtering v2  

An **agentic AI workflow** for automated resume filtering.  
This project parses job descriptions and resumes stored in **Supabase**, extracts structured information using **LLMs**, and generates a **compatibility score** with an **audit report** — helping recruiters quickly identify the best candidates.  

---

## 🚀 Features  
- **Job Description Agent** → Extracts structured requirements from job description PDFs.  
- **Resume Parser Agent** → Parses resumes into structured JSON.  
- **Compatibility Analyzer** → Compares parsed resume data with job requirements.  
- **Audit Agent** → Produces a final audit explaining compatibility decisions.  
- **Supabase Integration** → Stores job documents, parsed resumes, and results.  
- **Token & Cost Tracking** → Logs LLM usage and estimates costs per agent.  

---

## 📂 Project Structure  

resume_filtering_v2/

│── main.py                  # Entry point: runs the entire workflow

│── requirements.txt         # Python dependencies

│

├── agents/                  # (Optional extension for agent definitions)

├── prompts/                 # Prompt templates for each agent

│   ├── job_description_prompt.txt

│   ├── resume_parser_prompt.txt

│   ├── compatibility_prompt.txt

│   └── audit_agent.txt

│

├── util/

│   ├── supabase_utils.py    # Supabase upload/download helpers

│   └── parsing.py           # Resume & JD text parsing utilities

│

└── job_folders/             # Example job/resume storage (mirrors Supabase bucket)

---

