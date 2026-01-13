import re

# คำต้องห้าม + เหตุผลตามแนวทาง อย.
EXAGGERATION_RULES = {
    "เห็นผลทันที": "เป็นการกล่าวอ้างผลลัพธ์แน่นอน เข้าข่ายโฆษณาเกินจริงตามแนวทาง อย.",
    "100%": "เป็นการรับประกันผลลัพธ์ ซึ่งไม่สามารถพิสูจน์ได้",
    "ดีที่สุด": "เป็นคำเปรียบเทียบเชิงยกย่องโดยไม่มีหลักฐานรองรับ",
    "ภายใน": "การระบุระยะเวลาผลลัพธ์ที่ชัดเจน อาจทำให้ผู้บริโภคเข้าใจผิด",
    "ไม่ต้องออกกำลังกาย": "อาจทำให้เข้าใจว่าผลิตภัณฑ์ทดแทนพฤติกรรมสุขภาพได้",
    "รับรองผล": "เป็นการยืนยันผลลัพธ์แบบแน่นอน",
}

def split_sentences(text: str):
    """แยกข้อความเป็นประโยค"""
    return re.split(r'[.!?\n]', text)

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
                "reasons": reasons
            })

    return len(bad_sentences) > 0, bad_sentences
