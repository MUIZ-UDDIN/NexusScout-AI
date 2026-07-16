import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = "You are a sales assistant. Write a single short sentence complimenting a business based on its name. Do not mention the name in the compliment. Return only the sentence, no quotes, no labels."

def generate_opening(business_name: str) -> str:
    if not os.getenv("GROQ_API_KEY"):
        return "I came across your business and was impressed by your work."

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": business_name},
        ],
        max_tokens=60,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()
