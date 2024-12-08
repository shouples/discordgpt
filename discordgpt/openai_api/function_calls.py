MODEL_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image based on the previous messages in the thread.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to use when generating the image.",
                    },
                    "style": {
                        "type": "string",
                        "enum": ["vivid", "natural"],
                        "description": "Vivid causes the model to lean towards generating hyper-real and dramatic images. Natural causes the model to produce more natural, less hyper-real looking images.",
                        "default": "vivid",
                    },
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_message_reaction",
            "description": "Generate a reaction to the previous message in the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "emojis": {
                        "type": "array",
                        "description": "The emoji(s) or name(s) of a server reaction(s) (if available) to use when generating the reaction(s).",
                        "items": {
                            "type": "string",
                        },
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Reasoning or justification for the chosen reaction(s).",
                    },
                },
                "required": ["emojis", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_text_response",
            "description": "Generate a text response to the previous message in the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "response_text": {
                        "type": "string",
                        "description": "Text to return as a response to the last message.",
                    },
                },
            },
        },
    },
]
