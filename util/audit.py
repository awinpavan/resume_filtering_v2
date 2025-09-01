import os
import json
import logging
import traceback
from typing import Dict, List, Any, Tuple
from datetime import datetime
import re
from langchain_openai import ChatOpenAI
from collections import defaultdict

# Token tracking (reuse from main.py)
def count_tokens(text, model="gpt-4"):
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)

def add_token_stats(agent, input_tokens, output_tokens):
    """Add token statistics - assumes token_stats is imported from main"""
    pass  # Implementation depends on your token tracking system

class AuditResumeAgent:
    """
    LLM-powered agent that audits compatibility analysis for accuracy,
    completeness, and potential bias.
    """
    
    def __init__(self, model="llama-3.1-8b-instant"):
        self.llm = ChatOpenAI(
            model=model,
            base_url="https://api.groq.com/openai/v1",
            openai_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1  # Slightly higher for more nuanced analysis
        )
        
        with open("prompts/audit_agent.txt", "r", encoding="utf-8") as f:
            self.audit_prompt = f.read()
    
    def audit_analysis(self, job_requirements: str, parsed_resume: str, 
                      compatibility_result: str, guard_results: Dict) -> Dict[str, Any]:
        """
        Audit the compatibility analysis using LLM.
        """
        try:
            # Prepare the prompt
            prompt = self.audit_prompt
            prompt = prompt.replace("{{job_requirements}}", job_requirements)
            prompt = prompt.replace("{{parsed_resume}}", parsed_resume)
            prompt = prompt.replace("{{compatibility_result}}", compatibility_result)
            
            # Get LLM response
            response = self.llm.invoke(prompt)
            
            # Token tracking
            input_tokens = count_tokens(prompt, model="llama-3.3-70b-versatile")
            output_tokens = count_tokens(response.content, model="llama-3.3-70b-versatile")
            add_token_stats("audit_resume_agent", input_tokens, output_tokens)

            # DEBUG: Print the raw LLM response
            print("=== RAW AUDIT LLM RESPONSE ===")
            print(response.content)
            print("=============================")

            # DIAGNOSTIC: Extract all JSON-like blocks and log parsing attempts
            json_blocks = re.findall(r'\{[\s\S]*?\}', response.content)
            print(f"[DIAGNOSTIC] Found {len(json_blocks)} JSON-like block(s) in LLM response.")
            for i, block in enumerate(json_blocks):
                print(f"[DIAGNOSTIC] Block {i+1}:\n{block}\n---")
                # Try normal parse first
                try:
                    audit_result = json.loads(block)
                    audit_result = self._validate_audit_result(audit_result)
                    print(f"[DIAGNOSTIC] Successfully parsed block {i+1} as JSON.")
                    return {
                        "status": "SUCCESS",
                        "audit_result": audit_result,
                        "raw_response": response.content
                    }
                except json.JSONDecodeError as e:
                    print(f"[DIAGNOSTIC] JSONDecodeError on block {i+1}: {e}")
                    print(f"[DIAGNOSTIC] Malformed block {i+1} content:\n{block}\n---")
                    # Try to repair JSON and parse again
                    repaired = self._repair_json(block)
                    if repaired:
                        try:
                            audit_result = json.loads(repaired)
                            audit_result = self._validate_audit_result(audit_result)
                            print(f"[DIAGNOSTIC] Successfully repaired and parsed block {i+1} as JSON.")
                            return {
                                "status": "SUCCESS",
                                "audit_result": audit_result,
                                "raw_response": response.content
                            }
                        except Exception as e2:
                            print(f"[DIAGNOSTIC] Repair attempt failed for block {i+1}: {e2}")
                    # Write the malformed block to a debug file for inspection
                    try:
                        with open("audit_agent_debug.json", "a", encoding="utf-8") as debug_f:
                            debug_f.write(f"\n=== Block {i+1} ===\n")
                            debug_f.write(block)
                            debug_f.write("\n---\n")
                    except Exception as file_err:
                        print(f"[DIAGNOSTIC] Failed to write debug file: {file_err}")
                except Exception as e:
                    print(f"[DIAGNOSTIC] Unexpected error on block {i+1}: {e}")
                except json.JSONDecodeError as e:
                    print(f"[DIAGNOSTIC] JSONDecodeError on block {i+1}: {e}")
                    print(f"[DIAGNOSTIC] Malformed block {i+1} content:\n{block}\n---")
                    # Write the malformed block to a debug file for inspection
                    try:
                        with open("audit_agent_debug.json", "a", encoding="utf-8") as debug_f:
                            debug_f.write(f"\n=== Block {i+1} ===\n")
                            debug_f.write(block)
                            debug_f.write("\n---\n")
                    except Exception as file_err:
                        print(f"[DIAGNOSTIC] Failed to write debug file: {file_err}")

                except Exception as e:
                    print(f"[DIAGNOSTIC] Unexpected error on block {i+1}: {e}")
            # If none succeeded
            print("[DIAGNOSTIC] No valid JSON block could be parsed from LLM response.")
            return {
                "status": "ERROR",
                "error": "No JSON found in LLM response",
                "raw_response": response.content
            }
                
        except Exception as e:
            logging.error(f"Audit agent error: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "status": "ERROR",
                "error": str(e),
                "raw_response": ""
            }
    
    def _repair_json(self, s: str) -> str:
        """Attempt to auto-close braces and fix common LLM JSON issues."""
        # Remove trailing commas
        import re
        s = re.sub(r',([\s\n]*[}\]])', r'\1', s)
        # Try to auto-close braces/brackets
        open_braces = s.count('{')
        close_braces = s.count('}')
        open_brackets = s.count('[')
        close_brackets = s.count(']')
        s = s + ('}' * (open_braces - close_braces))
        s = s + (']' * (open_brackets - close_brackets))
        # Remove any trailing junk after last closing brace
        last_brace = s.rfind('}')
        if last_brace != -1:
            s = s[:last_brace+1]
        return s

    def _validate_audit_result(self, audit_result: Dict) -> Dict:
        """Validate and clean up audit result"""
        try:
            # Ensure required fields exist
            required_fields = [
                "auditScore", "originalScore", "recommendedScore", 
                "accuracyAssessment", "completenessReview", "biasAnalysis",
                "scoringRationale", "concerns", "strengths", "recommendations",
                "finalDecision", "confidence", "auditNotes"
            ]
            
            for field in required_fields:
                if field not in audit_result:
                    if field in ["concerns", "strengths", "recommendations"]:
                        audit_result[field] = []
                    elif field == "confidence":
                        audit_result[field] = 0.5
                    elif field in ["auditScore", "originalScore", "recommendedScore"]:
                        audit_result[field] = 0
                    else:
                        audit_result[field] = "Not assessed"
            
            # Validate score ranges
            for score_field in ["auditScore", "originalScore", "recommendedScore"]:
                if not isinstance(audit_result[score_field], (int, float)):
                    audit_result[score_field] = 0
                audit_result[score_field] = max(0, min(100, audit_result[score_field]))
            
            # Validate confidence
            if not isinstance(audit_result["confidence"], (int, float)):
                audit_result["confidence"] = 0.5
            audit_result["confidence"] = max(0.0, min(1.0, audit_result["confidence"]))
            
            # Validate final decision
            valid_decisions = ["ACCEPT", "REVIEW", "REJECT"]
            if audit_result["finalDecision"] not in valid_decisions:
                # Determine based on recommended score
                score = audit_result["recommendedScore"]
                if score >= 80:
                    audit_result["finalDecision"] = "ACCEPT"
                elif score >= 60:
                    audit_result["finalDecision"] = "REVIEW"
                else:
                    audit_result["finalDecision"] = "REJECT"
            
            return audit_result
            
        except Exception as e:
            logging.error(f"Audit result validation error: {e}")
            return {
                "auditScore": 0,
                "originalScore": 0,
                "recommendedScore": 0,
                "accuracyAssessment": "Validation error",
                "completenessReview": "Validation error",
                "biasAnalysis": "Validation error",
                "scoringRationale": "Validation error",
                "concerns": ["Audit validation failed"],
                "strengths": [],
                "recommendations": ["Manual review required"],
                "finalDecision": "REVIEW",
                "confidence": 0.0,
                "auditNotes": f"Validation error: {str(e)}"
            }

def audit_resume_analysis(job_requirements: str, parsed_resume: str, compatibility_result: str) -> dict:
    """
    Run the LLM-powered audit agent on the compatibility result.
    Returns the audit result as a dictionary.
    """
    auditor = AuditResumeAgent()
    return auditor.audit_analysis(job_requirements, parsed_resume, compatibility_result, guard_results=None)