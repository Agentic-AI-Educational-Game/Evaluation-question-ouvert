import Agents.llm as llm

# Define the tool schema for rubric extraction
RUBRIC_EXTRACTION_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "extract_rubric",
            "description": "Define a detailed scoring rubric based on a question and its key concepts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rubric": {
                        "type": "array",
                        "description": "A list of rubric entries, each with a concept, keywords, and weight.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "concept": {
                                    "type": "string",
                                    "description": "The name of the concept."
                                },
                                "keywords": {
                                    "type": "array",
                                    "description": "A list of relevant keywords for that concept.",
                                    "items": {"type": "string"}
                                },
                                "weight": {
                                    "type": "number",
                                    "description": "A weight (percentage) representing its importance, such that the total weights add up to 100%.",
                                    "minimum": 0,
                                    "maximum": 100
                                }
                            },
                            "required": ["concept", "keywords", "weight"]
                        }
                    }
                },
                "required": ["rubric"]
            }
        }
    }
]

# The INSTRUCTIONS can be simplified as the format is now enforced by the tool schema
INSTRUCTIONS = """
Based on the provided 'Text', 'Question', and 'Key Concepts Expected', define a detailed scoring rubric.
Each rubric entry MUST include:
*   "A concept name" (derived directly from the 'Key Concepts Expected')
*   "A list of relevant keywords for that concept" (derived from the 'Text' and 'Question')
*   "A weight (percentage) representing its importance, such that the total weights add up to 100%."

Prioritize the most important concepts that directly answer the question and distribute weights logically to reflect their significance. Ensure the rubric is comprehensive but not overly granular.
You MUST generate at least one rubric entry if key concepts are provided.

All responses MUST be in French.

IMPORTANT: When generating the JSON for the tool call, STRICTLY adhere to the defined schema. Do NOT include any properties or fields that are not explicitly defined in the tool's 'parameters' section. Ensure all boolean values are `true` or `false`.
"""

def rubric_extract(text, question, key_concepts_expected):
    if not text or not question or not key_concepts_expected:
        return None

    key_concepts_str = ", ".join(key_concepts_expected)

    prompt = f"""
Text: {text}

Question: {question}

Key Concepts Expected: {key_concepts_str}
"""
    # Call llm.completion with the tool schema and force it to call our function
    return llm.completion(
        prompt, 
        INSTRUCTIONS, 
        tools=RUBRIC_EXTRACTION_TOOL_SCHEMA, 
        tool_choice={"type": "function", "function": {"name": "extract_rubric"}}
    )

def test():
    return rubric_extract(
        text="Le cycle de l'eau comprend trois étapes principales : évaporation",
        question="Quelles sont les causes de la Révolution française ?",
        key_concepts_expected=["impôts", "famine", "idées des Lumières", "inégalités sociales", "dates clés"]
    )

# print(test())
