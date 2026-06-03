import os
from groq import Groq
from dotenv import load_dotenv


load_dotenv()

client = Groq(GROQ_API_KEY = "your_api_key_here")

messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant. Be concise."
    },
    {
        "role": "user",
        "content": "Explain what a langchaingraph is in 2 sentences."
    }
]

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=messages,
    temperature=0.7,  
)

reply = response.choices[0].message.content
print("Model reply:")
print(reply)

