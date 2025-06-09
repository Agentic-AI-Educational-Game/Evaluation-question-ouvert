# Agents/a_eval.py
import Agents.llm as llm
import json

# Define the tool schema for evaluation
EVAL_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "evaluate_answer",
            "description": "Score the student’s answer based on the given rubric and detailed semantic analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scores": {
                        "type": "array",
                        "description": "A list of scores for each concept in the rubric.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "concept": {"type": "string", "description": "The name of the concept."},
                                "score": {"type": "number", "description": "The score assigned to the concept."}
                            },
                            "required": ["concept", "score"]
                        }
                    },
                    "total_score": {
                        "type": "number",
                        "description": "The total score, which is the sum of all individual concept scores."
                    }
                },
                "required": ["scores", "total_score"]
            }
        }
    }
]

INSTRUCTIONS = """
Score the student’s answer based on the given rubric, considering the detailed semantic analysis from 'Answer Understanding'.
For each rubric item, assign a score from 0 up to the item's weight.

**Scoring Guidelines:**
    -   **Semantic Alignment**: Use the `overall_semantic_alignment` score from 'Answer Understanding' as a primary indicator of the answer's overall quality and relevance. A high overall alignment should lead to higher scores for relevant rubric concepts.
    -   **Concept Relevance & Completeness**: For each concept in the rubric, cross-reference it with the `concepts_found` in 'Answer Understanding'.
        -   If a rubric concept is clearly and accurately addressed by a `concepts_found` entry with high `relevance_score` and `completeness_score` (e.g., 90-100), assign a score very close to or equal to its full weight.
        -   If a rubric concept is partially addressed, or matched by a concept with lower `relevance_score` or `completeness_score`, assign proportional partial credit.
        -   If a rubric concept is not addressed, or addressed irrelevantly/incompletely (low scores), assign 0 or a very low score.
    -   **Accuracy**: Implicitly consider the accuracy based on the `relevance_score` and `overall_semantic_alignment`. Ensure the student's answer aligns factually with the provided 'Text'.
    -   **Structure**: Consider the `structure` details from 'Answer Understanding' (coherence, intro/body/conclusion) for rubric items related to organization or presentation, if applicable.
    -   **Irrelevance/Nonsense**: If the student's answer is completely irrelevant or nonsensical to the question and text, the `total_score` should be 0.

Ensure that for the exact same inputs, the 'scores' and 'total_score' generated are always identical.
Base your scoring strictly on the provided information, focusing on objective evidence from the student's answer in relation to the rubric and the detailed 'Answer Understanding'.
The 'scores' array in your output MUST contain an entry for EACH concept listed in the provided 'Rubric', and ONLY for those concepts. Do NOT invent new concepts for scoring.
Finally, calculate the total score as the sum of all individual scores.

All responses MUST be in French.

IMPORTANT: When generating the JSON for the tool call, STRICTLY adhere to the defined schema. Do NOT include any properties or fields that are not explicitly defined in the tool's 'parameters' section. Ensure all boolean values are `true` or `false`.
"""

def eval(text, question, answer, rubric, answer_understanding):
    if not all([text, question, answer, rubric, answer_understanding]):
        print("DEBUG a_eval: Condition 'not all([text, question, answer, rubric, answer_understanding])' is TRUE. One or more inputs are falsey.")
        if not rubric:
            print("DEBUG a_eval: The 'rubric' input is empty or None.")
        return None

    extracted_concepts = answer_understanding.get("concepts_found")
    answer_structure_details = answer_understanding.get("structure")

    if extracted_concepts is None or answer_structure_details is None:
        print("DEBUG a_eval: Condition 'extracted_concepts is None or answer_structure_details is None' is TRUE.")
        print(f"  extracted_concepts: {extracted_concepts}")
        print(f"  answer_structure_details (from key 'structure'): {answer_structure_details}")
        return None

    prompt = f"""
Context Text: {text}

Question: {question}

Student Answer: {answer}

Rubric: {json.dumps(rubric, ensure_ascii=False)}

Extracted Concepts: {json.dumps(extracted_concepts, ensure_ascii=False)}

Answer Structure: {json.dumps(answer_structure_details, ensure_ascii=False)}
"""
    # Call llm.completion with the tool schema and force it to call our function
    return llm.completion(
        prompt, 
        INSTRUCTIONS, 
        tools=EVAL_TOOL_SCHEMA, 
        tool_choice={"type": "function", "function": {"name": "evaluate_answer"}}
    )

def test():
    # (Your test function remains the same)
    # ...
    rubric = [
        {"concept": "causes économiques", "keywords": ["impôts", "taxes", "crise économique"], "weight": 25},
        {"concept": "causes sociales", "keywords": ["inégalités", "noblesse", "tiers état"], "weight": 25},
        {"concept": "idées des Lumières", "keywords": ["Voltaire", "liberté", "philosophie"], "weight": 20},
        {"concept": "dates clés", "keywords": ["1789", "prise de la Bastille"], "weight": 10},
        {"concept": "structure/analyse", "keywords": [], "weight": 20}
    ]

    answer_understanding_data = { # Renamed to avoid conflict with module name
        "concepts_found": ["impôts", "famine", "idées des Lumières"],
        "structure": { # CORRECTED KEY for test data as well
            "coherent": True,
            "has_intro": False,
            "has_body": True,
            "has_conclusion": False
        }
    }

    return eval(
        text="Le cycle de l'eau comprend trois étapes principales : évaporation, condensation et précipitation. L'évaporation se produit lorsque l'eau des océans se transforme en vapeur.",
        question="Quelles sont les trois étapes principales du cycle de l'eau ?",
        answer="évaporation, condensation",
        rubric=rubric,
        answer_understanding=answer_understanding_data # Use renamed variable
    )

if __name__ == '__main__': # To allow running this file directly for testing
    # print(test())
    pass
