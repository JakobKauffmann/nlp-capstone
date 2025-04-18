from together import Together
import os, re
from dotenv import load_dotenv

load_dotenv()

#requires TOGETHER_KEY in .env
client = Together(api_key=os.getenv('TOGETHER_KEY'))

def get_summary(text):
    prompt = """
    Please provide a summary of this text, Please give a clear answer with no extra formatting or special characters.
    Here is the text:
    """
    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
        messages=[{"role": "user", "content": prompt+text}]
    )
    summary = response.choices[0].message.content
    #removes the think tags and all text between
    cleaned_summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
    return {
        "summary" : cleaned_summary,
    }
