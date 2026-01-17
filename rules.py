# rules.py
import re

# ----------------------------
# หมวดความเสี่ยง (Risk Categories)
# ----------------------------
RISK_CATEGORIES = {
    "guarantee": {
        "label": "การอ้างผลลัพธ์แน่นอน",
        "keywords": ["หายขาด", "100%", "การันตี", "ได้ผลแน่นอน", "ถาวร"]
    },
    "exaggeration": {
        "label": "การใช้คำโอ้อวด",
        "keywords": ["ดีที่สุด", "อันดับหนึ่ง", "เห็นผลทันที", "เร็วที่สุด"]
    },
    "medical_claim": {
        "label": "การอ้างสรรพคุณทางการแพทย์",
        "keywords": ["รักษา", "บำบัด", "ลดน้ำหนัก", "ป้องกันโรค", "ฟื้นฟู"]
    },
    "no_reference": {
        "label": "การขาดแหล่งอ้างอิง",
        "keywords": ["พิสูจน์แล้ว", "งานวิจัยยืนยัน", "ผู้เชี่ยวชาญแนะนำ"]
    }
}

# ----------------------------
# กฎคำโฆษณาเกินจริง + เหตุผล (Explainability)
# ----------------------------
EXAGGERATION_RULES = {
    "เห็นผลทันที": "เป็นการกล่าวอ้างผลลัพธ์แน่นอน เข้าข่ายโฆษณาเกินจริงตามแนวทาง อย.",
    "100%": "เป็นการรับประกันผลลัพธ์ ซึ่งไม่สามารถพิสูจน์ได้",
    "ดีที่สุด": "เป็นคำเปรียบเทียบเชิงยกย่องโดยไม่มีหลักฐานรองรับ",
    "ภายใน": "การระบุระยะเวลาผลลัพธ์ที่ชัดเจน อาจทำให้ผู้บริโภคเข้าใจผิด",
    "ไม่ต้องออกกำลังกาย": "อาจทำให้เข้าใจว่าผลิตภัณฑ์สามารถทดแทนพฤติกรรมสุขภาพได้",
    "รับรองผล": "เป็นการยืนยันผลลัพธ์แบบแน่นอน ซึ่งกฎหมายไม่อนุญาต"
}

# ----------------------------
# Utility: แยกข้อความเป็นประโยค
# ----------------------------
def split_sentences(text: str):
    """
    แยกข้อความเป็นประโยค
    รองรับภาษาไทย + อังกฤษ แบบง่าย
    """
    return re.split(r"[.!?\n]", text)

# ----------------------------
# จัดหมวดความเสี่ยง
# ----------------------------
def classify_risk(sentence: str) -> list[str]:
    """
    รับประโยค → คืน list ของหมวดความเสี่ยง
    """
    risks = []

    for cat in RISK_CATEGORIES.values():
        for kw in cat["keywords"]:
            if kw in sentence:
                risks.append(cat["label"])
                break

    # กันซ้ำ
    return list(set(risks))

# ----------------------------
# ตรวจโฆษณาเกินจริง (Core Logic)
# ----------------------------
def check_exaggeration(text: str):
    """
    return:
    is_bad: bool
    bad_sentences: list[dict]
    """

    bad_sentences = []
    sentences = split_sentences(text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        found_words = []
        reasons = []

        for word, reason in EXAGGERATION_RULES.items():
            if word in sentence:
                found_words.append(word)
                reasons.append(reason)

        if found_words:
            bad_sentences.append({
                "sentence": sentence,
                "words": found_words,
                "reasons": reasons,
                "risk_categories": classify_risk(sentence)
            })

    return bool(bad_sentences), bad_sentences
