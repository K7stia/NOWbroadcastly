import re
from openai import AsyncOpenAI
import os

client = AsyncOpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")

def remove_all_links(text: str) -> str:
    text = re.sub(r'<a href="[^"]+">(.+?)</a>', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    return text.strip()

async def rewrite_text(text: str, style: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Перефразуй цей текст у стилі: {style}"},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[❗️Помилка рерайту: {e}]\n{text}"
