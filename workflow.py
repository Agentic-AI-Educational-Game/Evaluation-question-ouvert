# workflow.py
import json
import os
import time
import traceback

# Agent imports (ensure these paths are correct relative to where workflow.py is run)
import Agents.a_ans_understanding as answer_understanding_agent
import Agents.a_qst_understanding as question_understanding_agent
import Agents.a_rubric_extraction as rubric_extraction_agent
import Agents.a_grammar_language as grammar_language_agent
import Agents.a_eval as eval_agent
import Agents.a_final_eval as final_eval_agent

def call_agent_with_retry(agent_function, agent_args: tuple, agent_name: str, max_retries: int = 2, retry_delay_seconds: int = 1):
    """
    Calls an agent function, attempts to parse its string output as JSON, and logs attempts.
    Returns:
        A tuple (parsed_output, raw_output_str, attempt_logs, success_flag).
        - parsed_output: dict/list if successful, else None.
        - raw_output_str: The last raw string output from the agent.
        - attempt_logs: A list of strings logging each attempt and its outcome.
        - success_flag: Boolean indicating if a valid JSON was parsed.
    """
    last_raw_output_for_error_reporting = None
    attempt_logs = []
    success_flag = False

    for attempt in range(max_retries + 1):
        log_message_prefix = f"Attempt {attempt + 1}/{max_retries + 1} for {agent_name}"
        attempt_logs.append(f"{log_message_prefix}...")
        try:
            raw_output = agent_function(*agent_args) # Renamed to raw_output as it might not be a string
            last_raw_output_for_error_reporting = raw_output

            parsed_output = None
            success_flag = False

            if raw_output is None:
                msg = f"{log_message_prefix}: Agent function returned None directly. Not a parsing error."
                attempt_logs.append(msg)
                # No retry for this specific condition, treat as an agent logic failure
                return None, last_raw_output_for_error_reporting, attempt_logs, False
            elif isinstance(raw_output, dict) or isinstance(raw_output, list):
                # If the agent already returned a parsed JSON object (dict or list)
                parsed_output = raw_output
                success_flag = True
                attempt_logs.append(f"{log_message_prefix}: Success - Agent returned pre-parsed JSON.")
                return parsed_output, json.dumps(raw_output, ensure_ascii=False), attempt_logs, True # Return string representation for raw_output_str
            elif isinstance(raw_output, str):
                # If the agent returned a string, try to parse it as JSON
                parsed_output = json.loads(raw_output)
                success_flag = True
                attempt_logs.append(f"{log_message_prefix}: Success - Parsed JSON from string output.")
                return parsed_output, raw_output, attempt_logs, True
            else:
                # Unexpected return type from agent function
                msg = f"{log_message_prefix}: Agent function returned unexpected type {type(raw_output)}. Expected str, dict, or list."
                attempt_logs.append(msg)
                if attempt == max_retries:
                    attempt_logs.append(f"ERROR: {agent_name} failed due to unexpected return type after {max_retries + 1} attempts.")
                    return None, str(raw_output), attempt_logs, False # Convert to string for error reporting
                attempt_logs.append(f"Retrying in {retry_delay_seconds}s...")
                time.sleep(retry_delay_seconds)
                continue # Continue to next attempt

        except json.JSONDecodeError as e:
            msg = f"{log_message_prefix}: JSONDecodeError - {e}"
            attempt_logs.append(msg)
            # The raw_output_str here would be the string that failed to parse
            raw_output_str_for_log = last_raw_output_for_error_reporting if isinstance(last_raw_output_for_error_reporting, str) else str(last_raw_output_for_error_reporting)
            attempt_logs.append(f"Last raw output for {agent_name}: {raw_output_str_for_log[:500]}...") # Log first 500 chars
            if attempt == max_retries:
                attempt_logs.append(f"ERROR: {agent_name} failed to produce valid JSON after {max_retries + 1} attempts.")
                return None, last_raw_output_for_error_reporting, attempt_logs, False
            attempt_logs.append(f"Retrying in {retry_delay_seconds}s...")
            time.sleep(retry_delay_seconds)

        except Exception as e:
            tb_str = traceback.format_exc()
            msg = f"{log_message_prefix}: Unexpected error - {e}\nTraceback:\n{tb_str}"
            attempt_logs.append(msg)
            if attempt == max_retries:
                attempt_logs.append(f"ERROR: {agent_name} failed due to unexpected error after {max_retries + 1} attempts.")
                return None, last_raw_output_for_error_reporting, attempt_logs, False
            attempt_logs.append(f"Retrying in {retry_delay_seconds}s...")
            time.sleep(retry_delay_seconds)
            
    return None, last_raw_output_for_error_reporting, attempt_logs, False


def run_evaluation_workflow(text_input, question_input, student_answer_input):
    """
    Orchestrates the full evaluation workflow and returns detailed step-by-step data.
    Returns:
        A tuple (final_result, workflow_steps_details).
        - final_result: The final JSON output if successful, else None.
        - workflow_steps_details: A list of dictionaries, each detailing a step.
    """
    workflow_steps_details = []
    current_step_data = {}

    # --- Helper to add step data ---
    def add_step_data(name, inputs, parsed_output, raw_output, logs, success):
        status = "Success" if success and parsed_output is not None else "Failure"
        error_msg = None
        if not success:
            error_msg = logs[-1] if logs else "Unknown error"
            if parsed_output is None and raw_output is None and "Agent function returned None directly" in error_msg:
                 error_msg = f"{name} agent logic error: Returned None. Check agent's internal validation or inputs."
            elif parsed_output is None: # JSON parsing failed or other exception
                 error_msg = f"Failed to get valid JSON from {name}. Last attempt log: {error_msg}"


        workflow_steps_details.append({
            "name": name,
            "inputs": inputs,
            "attempts_logs": logs,
            "raw_output": raw_output,
            "parsed_output": parsed_output,
            "status": status,
            "error_message_detail": error_msg if status == "Failure" else None
        })

    # --- 1. Agent de compréhension des questions ---
    step_name = "1. Question Understanding"
    step_inputs = {"text_input": text_input, "question_input": question_input}
    question_analysis, raw_qst_str, qst_logs, qst_success = call_agent_with_retry(
        question_understanding_agent.qst_understanding, (text_input, question_input), step_name
    )
    add_step_data(step_name, step_inputs, question_analysis, raw_qst_str, qst_logs, qst_success)
    if not qst_success or question_analysis is None:
        return None, workflow_steps_details
    
    key_concepts_expected = question_analysis.get("key_concepts_expected", [])
    if not key_concepts_expected:
        # Add a "sub-step" or note for this failure condition
        workflow_steps_details.append({
            "name": f"{step_name} - Logic Check", "status": "Failure",
            "error_message_detail": "No 'key_concepts_expected' found in the output of Question Understanding Agent.",
            "inputs": {"question_analysis_output": question_analysis}, "attempts_logs": [], "raw_output": None, "parsed_output": None
        })
        return None, workflow_steps_details

    # --- 2. Agent d'extraction de rubriques ---
    step_name = "2. Rubric Extraction"
    step_inputs = {"text_input": text_input, "question_input": question_input, "key_concepts_expected": key_concepts_expected}
    rubric_definition, raw_rubric_str, rubric_logs, rubric_success = call_agent_with_retry(
        rubric_extraction_agent.rubric_extract, (text_input, question_input, key_concepts_expected), step_name
    )
    add_step_data(step_name, step_inputs, rubric_definition, raw_rubric_str, rubric_logs, rubric_success)
    if not rubric_success or rubric_definition is None:
        return None, workflow_steps_details

    actual_rubric = rubric_definition.get("rubric", [])
    if not actual_rubric:
        workflow_steps_details.append({
            "name": f"{step_name} - Logic Check", "status": "Failure",
            "error_message_detail": "No 'rubric' list found or rubric is empty in the output of Rubric Extraction Agent.",
            "inputs": {"rubric_definition_output": rubric_definition}, "attempts_logs": [], "raw_output": None, "parsed_output": None
        })
        return None, workflow_steps_details

    # --- 3. Agent de compréhension des réponses ---
    step_name = "3. Answer Understanding"
    step_inputs = {"text_input": text_input, "question_input": question_input, "student_answer_input": student_answer_input}
    answer_analysis, raw_ans_str, ans_logs, ans_success = call_agent_with_retry(
        answer_understanding_agent.ans_understanding, (text_input, question_input, student_answer_input), step_name
    )
    add_step_data(step_name, step_inputs, answer_analysis, raw_ans_str, ans_logs, ans_success)
    if not ans_success or answer_analysis is None:
        return None, workflow_steps_details

    # --- 4. Agent de grammaire et de langue ---
    step_name = "4. Grammar and Language"
    step_inputs = {"student_answer_input": student_answer_input}
    grammar_report, raw_grammar_str, grammar_logs, grammar_success = call_agent_with_retry(
        grammar_language_agent.grammar, (student_answer_input,), step_name
    )
    add_step_data(step_name, step_inputs, grammar_report, raw_grammar_str, grammar_logs, grammar_success)
    if not grammar_success or grammar_report is None:
        return None, workflow_steps_details
    grammar_penalty_percent = grammar_report.get("penalty", 0) # Default to 0 if not found

    # --- 5. Agent d'évaluation ---
    step_name = "5. Evaluation"
    step_inputs = {
        "text_input": text_input, "question_input": question_input, "student_answer_input": student_answer_input,
        "actual_rubric": actual_rubric, "answer_analysis": answer_analysis
    }
    evaluation_scores, raw_eval_str, eval_logs, eval_success = call_agent_with_retry(
        eval_agent.eval,
        (text_input, question_input, student_answer_input, actual_rubric, answer_analysis), step_name
    )
    add_step_data(step_name, step_inputs, evaluation_scores, raw_eval_str, eval_logs, eval_success)
    if not eval_success or evaluation_scores is None:
        return None, workflow_steps_details
    
    rubric_based_score = evaluation_scores.get("total_score")
    breakdown_scores = evaluation_scores.get("scores")
    if rubric_based_score is None or breakdown_scores is None:
        workflow_steps_details.append({
            "name": f"{step_name} - Logic Check", "status": "Failure",
            "error_message_detail": "Missing 'total_score' or 'scores' in the output of Evaluation Agent.",
            "inputs": {"evaluation_scores_output": evaluation_scores}, "attempts_logs": [], "raw_output": None, "parsed_output": None
        })
        return None, workflow_steps_details

    # --- 6. Agent de notation finale ---
    step_name = "6. Final Scoring"
    step_inputs = {
        "text_input": text_input, "question_input": question_input, "student_answer_input": student_answer_input,
        "actual_rubric": actual_rubric, "answer_analysis": answer_analysis,
        "rubric_based_score": rubric_based_score, "grammar_penalty_percent": grammar_penalty_percent,
        "breakdown_scores": breakdown_scores
    }
    final_output, raw_final_str, final_logs, final_success = call_agent_with_retry(
        final_eval_agent.final_eval,
        (text_input, question_input, student_answer_input, actual_rubric, answer_analysis,
         rubric_based_score, grammar_penalty_percent, breakdown_scores), step_name
    )
    add_step_data(step_name, step_inputs, final_output, raw_final_str, final_logs, final_success)
    if not final_success or final_output is None:
        return None, workflow_steps_details

    return final_output, workflow_steps_details

if __name__ == "__main__":
    # This part is for direct execution of workflow.py, not used by Streamlit app
    # It's kept for potential command-line testing.
    example_text_main = """
Dans la cour de l'école, les élèves sont joyeux. Ils jouent en groupes. Certains font de la
corde à sauter. D'autres jouent à cache-cache. On entend des rires partout.
En classe, la maîtresse explique la leçon de mathématiques avec un grand sourire. Elle
écrit des chiffres au tableau. Les enfants l'écoutent avec attention.
Nous prenons nos livres et nos cahiers. Il est temps d'apprendre à faire des additions
et à résoudre des problèmes. La maîtresse nous montre comment faire. Chacun essaie
sur son cahier. Si on a du mal, on peut demander de l'aide. Petit à petit, on devient plus
fort en maths.
"""
    example_question_main = "Que fait la maîtresse ?"
    example_student_answer_main = "La maîtresse explique la leçon de mathématiques, écrit des chiffres au tableau, montre comment faire des additions et résoudre des problèmes, et aide les élèves quand ils ont du mal."

    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY environment variable not set.")
    else:
        print("Running workflow from command line for testing...")
        final_res, steps_data = run_evaluation_workflow(
            example_text_main, example_question_main, example_student_answer_main
        )
        print("\n--- Workflow Steps Data (for CLI testing) ---")
        for i, step in enumerate(steps_data):
            print(f"\n--- Step {i+1}: {step['name']} ---")
            print(f"Status: {step['status']}")
            if step.get('inputs'): print(f"Inputs: {json.dumps(step['inputs'], indent=2, ensure_ascii=False)}")
            if step.get('attempts_logs'):
                print("Attempt Logs:")
                for log in step['attempts_logs']: print(f"  {log}")
            if step.get('raw_output'): print(f"Raw Output: {step['raw_output']}")
            if step.get('parsed_output'): print(f"Parsed Output: {json.dumps(step['parsed_output'], indent=2, ensure_ascii=False)}")
            if step.get('error_message_detail'): print(f"Error Detail: {step['error_message_detail']}")

        if final_res:
            print("\n--- FINAL EVALUATION RESULT (CLI) ---")
            print(json.dumps(final_res, indent=4, ensure_ascii=False))
        else:
            print("\nWorkflow execution failed or was interrupted (CLI).")
