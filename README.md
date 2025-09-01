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

## 🧑‍💻 Example Output

==== Resume Filtering Agentic Workflow ====
📂 Available Job Folders:
1. ai_engineer
2. data_scientist

👉 Select a job folder number to view details: 1

📄 Job Description(s):
• job_ai_engineer.pdf → https://...

📁 Resumes:
• resume_1.pdf → https://...
• resume_2.pdf → https://...

🔄 Now parsing and uploading documents for job: ai_engineer
...
[Compatibility Result]
{
  "score": 0.87,
  "fit": "High",
  "reasons": ["Matches required ML experience", "Good Python skills"]
}
[AuditAgent Output]
{
  "decision": "Fit",
  "explanation": "Resume aligns with 80%+ of core job requirements..."
}
==================== TOKEN & COST SUMMARY ====================
Agent                        Calls       Input      Output      Cost($)
job_description_agent            1         220         350       0.0008
resume_parser_agent              2         400         500       0.0014
compatibility_analyzer_agent     2         310         420       0.0011
audit_agent                      2         280         390       0.0010
-----------------------------------------------------------------------
TOTAL                            7        1210        1660       0.0043
============================================================
