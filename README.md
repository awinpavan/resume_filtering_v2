# 📄 Resume Filtering v2

An **agentic AI workflow** for automated resume filtering.
This project parses job descriptions and resumes stored in **Supabase**, extracts structured information using **LLMs**, and generates a **compatibility score** with an **audit report** — helping recruiters quickly identify the best candidates.

---

## 🚀 Features

* **Job Description Agent** → Extracts structured requirements from job description PDFs.
* **Resume Parser Agent** → Parses resumes into structured JSON.
* **Compatibility Analyzer** → Compares parsed resume data with job requirements.
* **Audit Agent** → Produces a final audit explaining compatibility decisions.
* **Supabase Integration** → Stores job documents, parsed resumes, and results.
* **Token & Cost Tracking** → Logs LLM usage and estimates costs per agent.

---

## 📂 Project Structure

```
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
```

---

## ⚙️ Setup

### 1. Clone the Repository

```bash
git clone https://github.com/awinpavan/resume_filtering_v2.git
cd resume_filtering_v2
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root with:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_role_key
GROQ_API_KEY=your_groq_api_key
```

---

## ▶️ Usage

Run the workflow:

```bash
python main.py
```

**Workflow steps:**

1. Lists available job folders from Supabase (`job-documents/`).
2. Lets you select a job folder.
3. Parses job description and resumes (if not already parsed).
4. Runs agentic pipeline:

   * Extract job requirements
   * Parse resumes
   * Compute compatibility scores
   * Generate audit report
5. Uploads structured results back to Supabase.
6. Prints token usage & cost summary.

---

## 🧑‍💻 Example Output

```
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
```

---

## 🛠️ Tech Stack

* **Python 3.10+**
* [LangGraph](https://github.com/langchain-ai/langgraph)
* [LangChain](https://www.langchain.com/)
* [Groq API](https://groq.com/) for fast LLM inference
* [Supabase](https://supabase.com/) for storage

---

## 📌 Next Steps / TODO

* [ ] Add Dockerfile for easy deployment
* [ ] Build a web UI to visualize compatibility reports
* [ ] Extend with recruiter feedback loop for continuous improvement

```

---

I can also create this as a **downloadable `README.md` file** for you right now so you can just save it in your repo. Do you want me to do that?

```
