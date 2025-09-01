import os
import logging
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from dotenv import load_dotenv
from agents.agent_utils import load_prompt, validate_state, log_agent_step

load_dotenv()

PROMPT_PATH = "prompts/job_description_prompt.txt"

try:
    JD_PROMPT = load_prompt(PROMPT_PATH)
except Exception:
    JD_PROMPT = None

jd_llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    base_url="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

def job_description_agent(state):
    import traceback
    try:
        validate_state(["job_description"], state)
        if JD_PROMPT is None:
            raise RuntimeError(f"Prompt not loaded from {PROMPT_PATH}")
        job_description = state["job_description"]
        prompt = JD_PROMPT.replace("{{job_description}}", job_description)
        response = jd_llm.invoke(prompt)
        state["job_requirements"] = response.content
        log_agent_step("JobDescriptionAgent", state, output_key="job_requirements")
        return state
    except Exception as e:
        logging.error(f"[JobDescriptionAgent] Exception: {e}\n{traceback.format_exc()}")
        raise

job_description_node = RunnableLambda(job_description_agent)