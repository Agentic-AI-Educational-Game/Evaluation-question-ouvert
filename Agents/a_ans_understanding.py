import Agents.llm as llm

# Define the tool schema for answer understanding
ANS_UNDERSTANDING_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "understand_answer",
            "description": "Analyze a student's answer in relation to provided text and question, extracting concepts, semantic alignment, entities, dates, and structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "concepts_found": {
                        "type": "array",
                        "description": "List of relevant concepts identified in the student's answer.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "concept": {"type": "string", "description": "The name of the concept."},
                                "relevance_score": {"type": "number", "description": "Relevance score (0-100) of the concept to the question and context.", "minimum": 0, "maximum": 100},
                                "completeness_score": {"type": "number", "description": "Completeness score (0-100) of the concept's explanation.", "minimum": 0, "maximum": 100}
                            },
                            "required": ["concept", "relevance_score", "completeness_score"]
                        }
                    },
                    "overall_semantic_alignment": {
                        "type": "number",
                        "description": "Overall semantic alignment score (0-100) of the answer with expected content.",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "named_entities": {
                        "type": "array",
                        "description": "List of named entities (people, places, organizations) mentioned.",
                        "items": {"type": "string"}
                    },
                    "dates": {
                        "type": "array",
                        "description": "List of specific time references or dates mentioned.",
                        "items": {"type": "string"}
                    },
                    "structure": {
                        "type": "object",
                        "description": "Assessment of the answer's structure.",
                        "properties": {
                            "coherent": {"type": "boolean", "description": "True if the answer is coherent."},
                            "has_intro": {"type": "boolean", "description": "True if the answer has an introduction."},
                            "has_body": {"type": "boolean", "description": "True if the answer has a body."},
                            "has_conclusion": {"type": "boolean", "description": "True if the answer has a conclusion."}
                        },
                        "required": ["coherent", "has_intro", "has_body", "has_conclusion"]
                    }
                },
                "required": ["concepts_found", "overall_semantic_alignment", "named_entities", "dates", "structure"]
            }
        }
    }
]

# The INSTRUCTIONS can be simplified as the format is now enforced by the tool schema
INSTRUCTIONS = """
Analyze the following student’s answer in relation to the provided 'Text' and 'Question'.
Your task is to extract the following information:
-   **Concepts found**: Identify all relevant concepts present in the student's answer. For each concept, assign a `relevance_score` (how well it relates to the question and context) and a `completeness_score` (how thoroughly it's explained).
    -   **Direct/Perfect Matches**: If a concept in the student's answer directly and perfectly matches information in the 'Text' that answers the 'Question', assign `relevance_score` and `completeness_score` of **100**. Minor spelling differences (e.g., "lecon" vs "leçon") should not reduce these scores, as they are handled by the grammar agent.
    -   **Near-Direct Matches**: If a concept very closely matches but isn't absolutely perfect, assign `relevance_score` and `completeness_score` between 95 and 99.
    -   **Partial Matches**: If a concept is partially addressed or less clearly stated, assign proportional scores.
    -   **Semantic Similarity**: Be flexible with phrasing; consider semantic similarity even if the exact words are not used.
-   **Overall semantic alignment**: Provide an `overall_semantic_alignment` score (0-100) indicating how well the student's answer aligns with the expected content based on the 'Text' and 'Question'.
-   **Named entities**: List any named entities (people, places, organizations) found *within the student's answer*.
-   **Dates**: List any specific time references or dates found *within the student's answer*.
-   **Structure**: Assess the answer's structure (coherence, presence of intro, body, conclusion).

Ensure all analysis and scoring are strictly based on the provided 'Text', 'Question', and 'Student Answer'.

All extracted information MUST be in French.
STRICTLY adhere to the defined function schema for the output format. Do NOT include any properties or fields that are not explicitly defined in the tool's 'parameters' section. Ensure all boolean values are `true` or `false`.
"""

def ans_understanding(text, question, answer):
    prompt = f"""
Text: {text}

Question: {question}

Student Answer: {answer}
"""
    # Call llm.completion with the tool schema and force it to call our function
    return llm.completion(
        prompt, 
        INSTRUCTIONS, 
        tools=ANS_UNDERSTANDING_TOOL_SCHEMA, 
        tool_choice={"type": "function", "function": {"name": "understand_answer"}}
    )

def test():
    text = ""
    question = ""
    answer = "Les impôts élevés, la famine, et les idées des Lumières ont contribué à la révolte du peuple."
    
    return ans_understanding(text, question, answer)

# print(test())
