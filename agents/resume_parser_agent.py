import os
import logging
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from dotenv import load_dotenv
from agents.agent_utils import load_prompt, validate_state, log_agent_step

load_dotenv()

PROMPT_PATH = "prompts/resume_parser_prompt.txt"

try:
    RESUME_PROMPT = load_prompt(PROMPT_PATH)
except Exception:
    RESUME_PROMPT = None

resume_llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    base_url="https://api.groq.com/openai/v1",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

def resume_parser_agent(state):
    import traceback
    try:
        validate_state(["resume_text"], state)
        if RESUME_PROMPT is None:
            raise RuntimeError(f"Prompt not loaded from {PROMPT_PATH}")
        resume_text = state["resume_text"]
        prompt = RESUME_PROMPT.replace("{{resume_text}}", resume_text)
        response = resume_llm.invoke(prompt)
        state["parsed_resume"] = response.content
        log_agent_step("ResumeParserAgent", state, output_key="parsed_resume")
        return state
    except Exception as e:
        logging.error(f"[ResumeParserAgent] Exception: {e}\n{traceback.format_exc()}")
        raise

resume_parser_node = RunnableLambda(resume_parser_agent)