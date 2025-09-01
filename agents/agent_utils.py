import os
import logging

def load_prompt(prompt_path):
    """Load a prompt from a file, with error handling."""
    try:
        with open(prompt_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load prompt '{prompt_path}': {e}")
        raise

def validate_state(required_keys, state):
    """Ensure all required keys are present in the state dict."""
    missing = [k for k in required_keys if k not in state]
    if missing:
        raise ValueError(f"Missing required state keys: {missing}")


def log_agent_step(agent_name, state, output_key=None):
    """Log the input and output of an agent step."""
    logging.info(f"[{agent_name}] Input state: {state}")
    if output_key and output_key in state:
        logging.info(f"[{agent_name}] Output ({output_key}): {state[output_key]}")
