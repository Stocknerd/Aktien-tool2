import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()
try:
    print("Calling OpenAI with gpt-5.5...")
    res = client.chat.completions.create(model="gpt-5.5", messages=[{"role": "user", "content": "hi"}])
    print("SUCCESS:", res.choices[0].message.content)
except Exception as e:
    print("ERROR:", e)
