import Agents.llm as llm

# Define the tool schema for question understanding
QST_UNDERSTANDING_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "understand_question",
            "description": "Analyze a question and extract its type, key concepts expected, and teacher's expectations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_type": {
                        "type": "string",
                        "description": "The type of question.",
                        "enum": ["descriptive", "analytical", "argumentative"]
                    },
                    "key_concepts_expected": {
                        "type": "array",
                        "description": "An array of keywords or phrases representing the key concepts expected in a complete answer.",
                        "items": {"type": "string"}
                    },
                    "teacher_expectations": {
                        "type": "array",
                        "description": "An array of points outlining the teacher’s expectations regarding the answer.",
                        "items": {"type": "string"}
                    }
                },
                "required": ["question_type", "key_concepts_expected", "teacher_expectations"]
            }
        }
    }
]

# The INSTRUCTIONS can be simplified as the format is now enforced by the tool schema
INSTRUCTIONS = """
Analyze the provided 'Text' and 'Question' to extract the following:
1. The type of question (choose one: descriptive, analytical, argumentative).
2. The key concepts or actions directly mentioned in the 'Text' that answer the 'Question'. These should be specific keywords or phrases representing the essential information expected in a complete answer, derived *only* from the 'Text'.
3. The teacher’s expectations regarding the answer, based on the 'Question' and the 'Text'.

All responses MUST be in French.

IMPORTANT: When generating the JSON for the tool call, STRICTLY adhere to the defined schema. Do NOT include any properties or fields that are not explicitly defined in the tool's 'parameters' section. Ensure all boolean values are `true` or `false`.
"""

def qst_understanding(text, question):
    prompt = f"""
Text: {text}

Question: {question}
"""
    # Call llm.completion with the tool schema and force it to call our function
    return llm.completion(
        prompt, 
        INSTRUCTIONS, 
        tools=QST_UNDERSTANDING_TOOL_SCHEMA, 
        tool_choice={"type": "function", "function": {"name": "understand_question"}}
    )

def test():
    text = "Le cycle de l'eau comprend trois étapes principales : évaporation, condensation et précipitation. L'évaporation se produit lorsque l'eau des océans se transforme en vapeur."
    question = "Quelles sont les causes de la Révolution française ?"
    
    return qst_understanding(text, question)

# print(test())
