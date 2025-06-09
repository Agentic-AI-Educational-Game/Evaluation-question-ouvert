from groq import Groq
import os
import re
import json # Import json for potential validation/debugging

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

def completion(prompt, instructions, model="gemma2-9b-it", tools=None, tool_choice=None):
    messages = [
        {
            "role": "system",
            "content": f"""{instructions}""",
        },
        {
            "role": "user",
            "content": f"""{prompt}""",
        }
    ]

    # Add tools to the request if provided
    if tools:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.0,
            seed=42,
            stream=False,
            tools=tools,
            tool_choice=tool_choice # Can be "auto", "none", or {"type": "function", "function": {"name": "my_function"}}
        )
    else:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.0,
            seed=42,
            stream=False,
        )

    # Check if the model called a tool
    if chat_completion.choices[0].message.tool_calls:
        tool_call = chat_completion.choices[0].message.tool_calls[0]
        if tool_call.type == "function":
            # Return the arguments of the function call as a dictionary
            return json.loads(tool_call.function.arguments)
        else:
            # Handle other tool types if necessary, though for now we only expect 'function'
            # If an unexpected tool type is returned, it's an error.
            raise ValueError(f"Unexpected tool type returned: {tool_call.type}")
    else:
        # If no tool was called, return the regular message content
        # This path should ideally not be taken if tool_choice is set to 'required' or a specific tool.
        res = chat_completion.choices[0].message.content
        return res
