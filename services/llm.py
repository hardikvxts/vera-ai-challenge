import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def generate_message(prompt):
    client = get_client()
    if not client:
        raise ValueError("GROQ_API_KEY environment variable is not set")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=180
    )

    return response.choices[0].message.content.strip()