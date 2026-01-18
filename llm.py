import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_text(text: str, rules: dict):
    prompt = f"""
คุณเป็นผู้เชี่ยวชาญด้านโฆษณาประกันในประเทศไทย

กฎที่ต้องพิจารณา:
{json.dumps(rules, ensure_ascii=False)}

ข้อความโฆษณา:
{text[:4000]}

ตอบเป็น JSON เท่านั้น:
{{
  "risk": "ไม่เสี่ยง | เสี่ยง",
  "reason": "",
  "highlight": []
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return json.loads(response.choices[0].message.content)
