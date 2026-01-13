from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from rules import check_exaggeration
from scraper import scrape_text

app = FastAPI()

# ----------------------
# หน้าเว็บ
# ----------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Ad Checker</title>
            <style>
                body {
                    font-family: Arial;
                    background: #f5f5f5;
                    padding: 40px;
                }
                textarea, input {
                    width: 100%;
                    padding: 10px;
                    margin-top: 10px;
                }
                button {
                    padding: 10px 20px;
                    font-size: 16px;
                    margin-top: 10px;
                }
                .box {
                    background: white;
                    padding: 20px;
                    max-width: 600px;
                    margin: auto;
                    border-radius: 8px;
                }
            </style>
        </head>
        <body>
            <div class="box">
                <h2>🔍 ตรวจข้อความโฆษณา</h2>

                <form method="post" action="/check-web">
                    <textarea name="text" placeholder="วางข้อความโฆษณาที่นี่..."></textarea>
                    <button type="submit">ตรวจจากข้อความ</button>
                </form>

                <hr>

                <form method="post" action="/check-url">
                    <input type="text" name="url" placeholder="วางลิงก์เว็บโฆษณาที่นี่..." />
                    <button type="submit">ตรวจจากลิงก์</button>
                </form>
            </div>
        </body>
    </html>
    """


# ----------------------
# ไฮไลต์คำโฆษณาเกินจริง
# ----------------------
def highlight_text(text: str, reasons: list[str]) -> str:
    highlighted = text

    for r in reasons:
        if '"' in r:
            word = r.split('"')[1]
            highlighted = highlighted.replace(
                word,
                f'<span style="color:red; font-weight:bold;">{word}</span>'
            )

    return highlighted

def highlight_sentence(sentence: str, words: list[str]):
    for w in words:
        sentence = sentence.replace(
            w,
            f'<span style="color:red; font-weight:bold;">{w}</span>'
        )
    return sentence

# ----------------------
# ตรวจจากข้อความ
# ----------------------
@app.post("/check-web", response_class=HTMLResponse)
def check_web(text: str = Form(...)):
    is_bad, bad_sentences = check_exaggeration(text)

    return f"""
    <html>
        <body style="font-family:Arial; background:#f5f5f5; padding:40px;">
            <div style="background:white; padding:20px; max-width:700px; margin:auto;">
                <h2>ผลการตรวจสอบ</h2>

                {"<p style='color:red;'>⚠️ พบข้อความโฆษณาเกินจริง</p>" if is_bad else "<p style='color:green;'>✅ ไม่พบข้อความโฆษณาเกินจริง</p>"}

                <hr>

                {''.join(
                    f'''
                    <div style="margin-bottom:20px;">
                        <p>❌ {highlight_sentence(item["sentence"], item["words"])}</p>
                        <ul>
                            {''.join(f"<li>📜 {r}</li>" for r in item["reasons"])}
                        </ul>
                    </div>
                    '''
                    for item in bad_sentences
                )}

                <a href="/">⬅️ กลับ</a>
            </div>
        </body>
    </html>
    """



# ----------------------
# ตรวจจากลิงก์เว็บ
# ----------------------
@app.post("/check-url", response_class=HTMLResponse)
def check_url(url: str = Form(...)):
    try:
        text = scrape_text(url)

        if not text or len(text.strip()) < 50:
            raise ValueError("ไม่พบข้อความโฆษณาที่ชัดเจน")

        is_bad, bad_sentences = check_exaggeration(text)

    except Exception as e:
        return f"""
        <html>
            <body style="font-family:Arial; padding:40px;">
                <h2>❌ ตรวจลิงก์ไม่สำเร็จ</h2>
                <p>{e}</p>
                <a href="/">⬅️ กลับ</a>
            </body>
        </html>
        """

    return f"""
    <html>
        <body style="font-family:Arial; background:#f5f5f5; padding:40px;">
            <div style="background:white; padding:20px; max-width:800px; margin:auto;">
                <h2>ผลการตรวจจากลิงก์</h2>
                <p><b>ลิงก์:</b> {url}</p>

                <hr>

                {"<p style='color:red;'>⚠️ พบข้อความโฆษณาเกินจริง</p>" if is_bad else "<p style='color:green;'>✅ ไม่พบข้อความโฆษณาเกินจริง</p>"}

                {''.join(
                    f'''
                    <div style="margin-bottom:20px;">
                        <p>❌ {highlight_sentence(item["sentence"], item["words"])}</p>
                        <ul>
                            {''.join(f"<li>📜 {r}</li>" for r in item["reasons"])}
                        </ul>
                    </div>
                    '''
                    for item in bad_sentences
                )}

                <a href="/">⬅️ กลับ</a>
            </div>
        </body>
    </html>
    """

