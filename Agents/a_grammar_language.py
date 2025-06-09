# Agents/a_grammar_language.py
import Agents.llm as llm
import json
import time

MAX_ATTEMPTS = 5 # Define max retry attempts for getting valid tool call response

# Define the tool schema for grammar evaluation
# Updated GRAMMAR_TOOL_SCHEMA to include 'accentuation' and enum for type
GRAMMAR_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "evaluate_grammar",
            "description": "Evaluate the grammar, spelling, accentuation, and clarity of a student's answer and calculate a language quality penalty.",
            "parameters": {
                "type": "object",
                "properties": {
                    "penalty": {
                        "type": "number",
                        "description": "A number between 0 and 10, representing a percentage (e.g., 5 for 5% penalty) based on the severity and frequency of errors. A perfect answer should have a 0 penalty.",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "errors": {
                        "type": "array",
                        "description": "List of major errors found in the student's answer.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "Type of error. Must be one of: grammar, spelling, accentuation, style.",
                                    "enum": ["grammar", "spelling", "accentuation", "style"] # Enforce specific types
                                },
                                "text": {
                                    "type": "string",
                                    "description": "Exact incorrect text from the student's answer."
                                },
                                "suggestion": {
                                    "type": "string",
                                    "description": "Exact suggested correction for the error. Must be a valid French word/phrase."
                                }
                            },
                            "required": ["type", "text", "suggestion"]
                        }
                    }
                },
                "required": ["penalty", "errors"]
            }
        }
    }
]

# Heavily revised INSTRUCTIONS
INSTRUCTIONS = """
You are an expert French language evaluator. Your task is to identify and list **ONLY clear and undeniable errors** in a student's answer that affect grammatical correctness, spelling, accentuation, or clarity. For each identified error, provide its `type`, the `text` (the exact incorrect part from the student's answer), and a precise `suggestion` for correction.

**ABSOLUTELY CRITICAL GUIDELINES FOR ERROR IDENTIFICATION AND SUGGESTIONS:**

1.  **Strictly Undeniable Errors Only**:
    *   Only identify errors that are unequivocally incorrect according to standard French.
    *   If a phrase is grammatically correct, a common usage, or a valid stylistic choice (e.g., "des chiffres" vs "des nombres", "au tableau"), it is **NOT an error**.
    *   The `text` you identify as incorrect must be *actually present* in the student's answer. Do not invent errors.

2.  **High-Quality, Valid Suggestions**: Each `suggestion` MUST adhere to the following:
    *   **Real and Correct French**: The `suggestion` MUST be a real, standard, correctly spelled, and complete French word or phrase. It must NOT be a hallucination or a non-existent word (e.g., for `text` "ecrit", do NOT suggest "crit"; for `text` "lecon", do NOT suggest "leôn"). The suggestion itself must not contain errors.
    *   **Minimal and Direct Correction**: The `suggestion` should correct *only* the identified error in the `text` and be the most direct, minimal change possible.
        *   Do NOT unnecessarily shorten, truncate, or fundamentally alter words if a simple correction (e.g., accent, single letter) is sufficient. (e.g., if `text` is "ecrit", a valid suggestion is "écrit", NOT "crit").
        *   Do NOT add new words, concepts, or information not present in or clearly implied by the original `text` (e.g., if `text` is "la leçon", `suggestion` should be "la leçon", not "la leçon de maths").
    *   **Contextual Appropriateness & Meaning Preservation**:
        *   **Gender/Agreement**: Do NOT change the gender of a noun (e.g., from "maitresse" to "maître") unless the original noun creates an *undeniable and explicit grammatical agreement error* with other words *clearly visible in the provided student answer*. If "maitresse" is a valid French word and grammatically plausible in its local context, it is NOT an error to be corrected by changing its gender. An example of a clear error would be "le maitresse intelligent" (should be "la maîtresse intelligente" or "le maître intelligent").
        *   The `suggestion` must preserve the original intended meaning of the `text` as much as possible.
    *   **Accentuation Focus**: For words that are otherwise spelled correctly but have missing or incorrect accents (e.g., `text`: "lecon", `suggestion`: "leçon"; `text`: "mathematiques", `suggestion`: "mathématiques"; `text`: "ecrit", `suggestion`: "écrit"), these are valid corrections and should be typed as `accentuation`.

3.  **Error Types (Strict Adherence to `enum` in schema)**:
    *   `grammar`: Errors in sentence structure, verb conjugation (e.g., "ils mange" -> "ils mangent"), clear subject-verb or noun-adjective agreement errors (e.g., "les voiture vert" -> "les voitures vertes"), incorrect prepositions or pronouns.
    *   `spelling`: Misspelled words – i.e., wrong letters, missing/extra letters that result in a non-word or an incorrect word (e.g., `text`: "expliqe", `suggestion`: "explique"; `text`: "gramaire", `suggestion`: "grammaire"). This is for errors beyond just accents.
    *   `accentuation`: Missing, incorrect, or superfluous accents on an otherwise correctly spelled word (e.g., `text`: "eleve", `suggestion`: "élève"; `text`: "lecon", `suggestion`: "leçon"; `text`: "maitresse" (if contextually feminine), `suggestion`: "maîtresse").
    *   `style`: Only for severe issues that significantly impede clarity or make the text highly unnatural or ungrammatical. Avoid for minor stylistic preferences.

4.  **Focus on Impact**: Prioritize errors that genuinely impede understanding or are fundamental mistakes. Minor, debatable stylistic preferences should be ignored.

5.  **Self-Correction Check (Mentally Perform This Before Outputting)**:
    *   Is the identified `text` truly an undeniable error based on these guidelines?
    *   Is the `suggestion` a valid, real, correctly spelled French word/phrase? Is it free of errors itself?
    *   Is the `suggestion` a minimal and direct correction of *only* the error in `text`?
    *   Does the `suggestion` make sense in the context of the original answer and preserve meaning?
    *   Is the `type` accurate according to the definitions above?

**Penalty Calculation**:
*   A perfect answer (with **no identified errors**) MUST result in a **0% penalty**.
*   For answers with errors, the penalty (0-10) should be strictly proportionate to the severity and frequency of the **actual, undeniable errors** identified.
*   Multiple minor `accentuation` errors might collectively warrant a small penalty (e.g., 0.5-1.5%). More significant `grammar` or `spelling` errors that impede understanding should result in a higher penalty.

All responses MUST be in French.

IMPORTANT: When generating the JSON for the tool call, STRICTLY adhere to the defined schema, including the `enum` for the error `type`. Do NOT include any properties or fields that are not explicitly defined in the tool's 'parameters' section.
"""

def grammar(answer):
    prompt = f"""
Student's Answer to evaluate:
{answer}
"""
    
    for attempt in range(MAX_ATTEMPTS):
        print(f"Attempt {attempt + 1}/{MAX_ATTEMPTS} to get valid tool call from Grammar and Language agent.")
        try:
            # Call llm.completion with the tool schema and force it to call our function
            res = llm.completion(
                prompt, 
                INSTRUCTIONS, 
                tools=GRAMMAR_TOOL_SCHEMA, 
                tool_choice={"type": "function", "function": {"name": "evaluate_grammar"}}
            )
            
            # llm.completion now returns the parsed arguments directly if a tool is called
            if isinstance(res, dict) and "penalty" in res and "errors" in res:
                # Programmatically enforce 0% penalty if no errors are identified
                if not res["errors"]:
                    res["penalty"] = 0
                    print(f"Grammar agent: Overriding penalty to 0% because no errors were identified.")
                
                # Further validation of suggestions (optional, but can help catch stubborn LLM issues)
                valid_errors = []
                for error in res.get("errors", []):
                    # Simplified validation: ensure suggestion is not empty and is different from the original text
                    if error.get("suggestion") and error.get("suggestion") != error.get("text"):
                        valid_errors.append(error)
                    else:
                        print(f"Grammar agent: Discarding error because suggestion is invalid or same as text: {error}")
                
                if len(valid_errors) < len(res.get("errors", [])):
                    print(f"Grammar agent: Some errors were filtered out due to invalid suggestions.")
                    res["errors"] = valid_errors
                    if not res["errors"]: # If all errors were filtered, penalty should be 0
                        res["penalty"] = 0
                        print(f"Grammar agent: All errors filtered, overriding penalty to 0%.")
                
                print(f"Successfully received and validated tool call arguments on attempt {attempt + 1}.")
                return res # Return the parsed dictionary
            else:
                print(f"LLM completion returned unexpected format on attempt {attempt + 1}: {res}")
                time.sleep(1) # Wait before retrying
        except Exception as e:
            print(f"Error during LLM completion or tool call processing on attempt {attempt + 1}: {e}")
            time.sleep(1) # Wait before retrying

    raise ValueError(f"Failed to get valid tool call arguments from Grammar and Language agent after {MAX_ATTEMPTS} attempts.")

def test():
    test_answer = "La maitresse explique la lecon de mathematiques et elle ecrit au tableau"
    # test_answer = "Bonne compréhension générale. Vous avez bien identifié les causes"
    # test_answer = "elle ecrit crit au tableau" # Test with a potential hallucination source
    print(f"Testing grammar agent with: \"{test_answer}\"")
    res = grammar(test_answer)
    print("Raw output from grammar agent test:")
    print(res) 
    if res:
        print("\nParsed JSON output from grammar test (already parsed):")
        print(json.dumps(res, indent=2, ensure_ascii=False)) 
    return res

if __name__ == '__main__':
    # test() # Uncomment to test this agent directly
    pass
