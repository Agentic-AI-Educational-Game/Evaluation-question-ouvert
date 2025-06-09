# Agents/a_final_eval.py
import Agents.llm as llm
import json

# Define the tool schema for final evaluation
FINAL_EVAL_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "provide_final_evaluation",
            "description": "Provide nuanced, context-aware, and constructive feedback, and output the pre-calculated final score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "final_score": {
                        "type": "number",
                        "description": "The pre-calculated numerical final score."
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Detailed, constructive feedback highlighting strengths and areas for improvement (2-4 sentences)."
                    }
                },
                "required": ["final_score", "feedback"]
            }
        }
    }
]

INSTRUCTIONS = """
You are an evaluation agent. Your task is to provide nuanced, context-aware, and constructive feedback, and output the pre-calculated final score.

1.  **Provide Feedback**:
    Write a detailed feedback summary (2-4 sentences) for the student. Your feedback should:
    -   **Describe Strengths**: State what the student's answer covered well, referencing specific concepts or aspects where they scored highly, based *only* on the provided text and rubric. (e.g., "L'élève a correctement identifié X et a fourni des détails pertinents sur Y, tels que mentionné dans le texte source.")
    -   **Identify Gaps/Inaccuracies**: Point out what was missing or incorrect in the student's answer, referencing areas where the student scored lower or where their answer lacked completeness, relevance, or accuracy, based *only* on the provided text and rubric. (e.g., "Cependant, l'explication de Z était incomplète, et le concept de A n'a pas été abordé comme attendu par la rubrique.")
    -   **Focus on Content**: Ensure the feedback strictly evaluates the student's answer against the provided text and rubric, without introducing external information, new suggestions, or advice not directly derivable from the evaluation criteria.
    -   **Reflect Nuance**: Incorporate insights from the 'Breakdown Scores' and 'Analysis of Student's Answer' (especially `relevance_score`, `completeness_score`, and `overall_semantic_alignment`) to provide feedback that goes beyond simple correctness, touching on coverage, accuracy, and clarity/coherence as observed in the answer.

All responses MUST be in French.

IMPORTANT: When generating the JSON for the tool call, STRICTLY adhere to the defined schema. Do NOT include any properties or fields that are not explicitly defined in the tool's 'parameters' section. Ensure all boolean values are `true` or `false`.
"""

def final_eval(text, question, answer, rubric, answer_understanding, rubric_score, grammar_penalty_percent, breakdown_scores):
    # Input validation
    if not all([text, question, answer, rubric, answer_understanding]) or breakdown_scores is None:
        print("DEBUG a_final_eval: One of the core inputs (text, question, answer, rubric, answer_understanding, breakdown_scores) is missing or None.")
        return None
    if rubric_score is None or grammar_penalty_percent is None:
        print("DEBUG a_final_eval: rubric_score or grammar_penalty_percent is None. These are required, though can be 0.")
        return None

    extracted_concepts = answer_understanding.get("concepts_found")
    answer_structure_details = answer_understanding.get("structure")

    if extracted_concepts is None or answer_structure_details is None:
        print("DEBUG a_final_eval: Condition 'extracted_concepts is None or answer_structure_details is None' is TRUE.")
        return None

    # Perform the final score calculation in Python
    calculated_final_score = rubric_score * (1 - (grammar_penalty_percent / 100.0))
    # Ensure the score is not negative and is within a reasonable range (e.g., 0-100)
    calculated_final_score = max(0, min(100, calculated_final_score))


    prompt = f"""
Context Information:
Text: {text}
Question: {question}
Student Answer: {answer}
Rubric Used: {json.dumps(rubric, ensure_ascii=False)}
Analysis of Student's Answer (concepts found, structure): {json.dumps(answer_understanding, ensure_ascii=False)}
Breakdown of Scores from Rubric: {json.dumps(breakdown_scores, ensure_ascii=False)}

Pre-calculated Final Score: {calculated_final_score:.2f}

Task:
Provide constructive 'feedback' based on the context and the pre-calculated final score.
Output ONLY the JSON as specified.
"""
    # Call llm.completion with the tool schema and force it to call our function
    return llm.completion(
        prompt, 
        INSTRUCTIONS, 
        tools=FINAL_EVAL_TOOL_SCHEMA, 
        tool_choice={"type": "function", "function": {"name": "provide_final_evaluation"}}
    )

def test():
    # (Your test function remains the same, ensure "structure" key is used in answer_understanding)
    rubric = [
        {"concept": "causes économiques", "keywords": ["impôts", "taxes", "crise économique"], "weight": 25},
        {"concept": "causes sociales", "keywords": ["inégalités", "noblesse", "tiers état"], "weight": 25},
    ]
    answer_understanding_data = {
        "concepts_found": ["impôts", "famine"],
        "structure": {"coherent": True, "has_intro": False, "has_body": True, "has_conclusion": False}
    }
    rubric_score_val = 65
    grammar_penalty_percent_val = 5
    breakdown_scores_data = [
        {"concept": "causes économiques", "score": 25},
        {"concept": "causes sociales", "score": 10},
    ]

    print("Testing final_eval agent...")
    res = final_eval(
        text="Context text example.",
        question="Question example.",
        answer="Student answer example.",
        rubric=rubric,
        answer_understanding=answer_understanding_data,
        rubric_score=rubric_score_val,
        grammar_penalty_percent=grammar_penalty_percent_val,
        breakdown_scores=breakdown_scores_data
    )
    print("Raw output from final_eval test:")
    print(res)
    if res:
        try:
            parsed = json.loads(res)
            print("\nParsed JSON output from final_eval test:")
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
            # Perform calculation manually to check
            expected_score = rubric_score_val * (1 - (grammar_penalty_percent_val / 100.0))
            print(f"Manually calculated score for comparison: {expected_score:.2f}") # Format to 2 decimal places
            if "final_score" in parsed and isinstance(parsed["final_score"], (int, float)):
                 print(f"LLM calculated score: {parsed['final_score']}")
            else:
                print("LLM did not produce a numerical final_score.")

        except json.JSONDecodeError as e:
            print(f"\nJSONDecodeError during final_eval test: {e}")
    return res

if __name__ == '__main__':
    # test() # Uncomment to test this agent directly
    pass
