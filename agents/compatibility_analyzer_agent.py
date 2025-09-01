import os
import logging
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from dotenv import load_dotenv
from agents.agent_utils import load_prompt, validate_state, log_agent_step

load_dotenv()

PROMPT_PATH = "prompts/compatibility_prompt.txt"

try:
    COMP_PROMPT = load_prompt(PROMPT_PATH)
except Exception:
    COMP_PROMPT = None

compat_llm = ChatOpenAI(
    model="llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

def compatibility_analyzer_agent(state):
    import traceback
    try:
        validate_state(["job_requirements", "parsed_resume"], state)
        if COMP_PROMPT is None:
            raise RuntimeError(f"Prompt not loaded from {PROMPT_PATH}")
        prompt = COMP_PROMPT
        prompt = prompt.replace("{{job_requirements}}", state["job_requirements"])
        prompt = prompt.replace("{{parsed_resume}}", state["parsed_resume"])
        response = compat_llm.invoke(prompt)
        state["compatibility_score"] = response.content
        log_agent_step("CompatibilityAnalyzerAgent", state, output_key="compatibility_score")
        return state
    except Exception as e:
        logging.error(f"[CompatibilityAnalyzerAgent] Exception: {e}\n{traceback.format_exc()}")
        raise

compatibility_analyzer_node = RunnableLambda(compatibility_analyzer_agent)