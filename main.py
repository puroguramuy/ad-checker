from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import html  # เพิ่ม import นี้เพื่อจัดการ text ใน input hidden ไม่ให้ HTML พัง

from rules import check_exaggeration
from scraper import scrape_text
from llm_explainer import explain_with_llm, suggest_safe_text
from llm_explainer import rewrite_sentence_safe


app = FastAPI()

# ----------------------
# หน้าเว็บ (Home)
# ----------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <title>Ad Checker</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                padding: 40px;
                line-height: 1.6;
            }
            .container {
                max-width: 900px;
                margin: auto;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            .header h1 {
                margin-bottom: 5px;
            }
            .header p {
                color: #666;
            }
            .box {
                background: white;
                padding: 25px;
                border-radius: 10px;
                margin-bottom: 25px;
            }
            textarea, input {
                width: 100%;
                padding: 10px;
                margin-top: 10px;
                font-size: 14px;
            }
            button {
                padding: 10px 20px;
                font-size: 15px;
                margin-top: 10px;
                cursor: pointer;
            }
            .how {
                background: #f9f9f9;
                padding: 20px;
                border-radius: 8px;
            }
            .tag {
                display: inline-block;
                background: #e8f0fe;
                color: #1a73e8;
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 12px;
                margin-right: 5px;
            }
            footer {
                text-align: center;
                color: #aaa;
                font-size: 12px;
                margin-top: 30px;
            }
        </style>
    </head>

    <body>
        <div class="container">

            <div class="header">
                <h1>🛡️ Ad Checker</h1>
                <p>
                    ระบบช่วยตรวจสอบข้อความโฆษณาเกินจริง  
                    พร้อมคำอธิบายตามแนวทางกฎหมายไทย (อย.)
                </p>
                <div>
                    <span class="tag">Rule-based</span>
                    <span class="tag">Explainable AI</span>
                    <span class="tag">LLM-assisted</span>
                </div>
            </div>

            <div class="box">
                <h3>📝 ตรวจจากข้อความ</h3>
                <p style="color:#777;">
                    เหมาะสำหรับข้อความโฆษณา, แคปชั่นขายของ, สคริปต์การตลาด
                </p>

                <form method="post" action="/check-web">
                    <textarea 
                        name="text" 
                        rows="5"
                        placeholder="เช่น: ลดน้ำหนักเห็นผล 100% ภายใน 7 วัน โดยไม่ต้องออกกำลังกาย">
                    </textarea>
                    <button type="submit">🔍 ตรวจข้อความ</button>
                </form>
            </div>

            <div class="box">
                <h3>🌐 ตรวจจากลิงก์เว็บไซต์</h3>
                <p style="color:#777;">
                    ระบบจะดึงข้อความจากหน้าเว็บ แล้ววิเคราะห์อัตโนมัติ
                </p>

                <form method="post" action="/check-url">
                    <input 
                        type="text" 
                        name="url" 
                        placeholder="https://example.com/ads-page"
                    />
                    <button type="submit">🔗 ตรวจจากลิงก์</button>
                </form>
            </div>

            <div class="box how">
                <h3>🔎 ระบบทำงานอย่างไร</h3>
                <ol>
                    <li>รับข้อความ หรือดึงข้อมูลจากเว็บไซต์</li>
                    <li>วิเคราะห์คำและประโยคที่เข้าข่ายโฆษณาเกินจริง (Rule-based)</li>
                    <li>ใช้ LLM อธิบายเหตุผลและเชื่อมโยงแนวทางกฎหมาย อย.</li>
                    <li>แนะนำข้อความที่ปลอดภัยและเหมาะสมกว่า</li>
                </ol>
            </div>

            <div class="box">
                <h3>🎯 เหมาะสำหรับใคร</h3>
                <ul>
                    <li>นักการตลาด / เจ้าของเพจออนไลน์</li>
                    <li>ผู้ประกอบการที่ต้องการลดความเสี่ยงด้านกฎหมาย</li>
                    <li>นักศึกษา ที่เรียนด้าน AI, NLP หรือกฎหมายโฆษณา</li>
                </ul>
            </div>

            <footer>
                Mini Project | Advertisement Compliance Checker  
                <br>
                Built with FastAPI + Rule-based NLP + LLM
            </footer>

        </div>
    </body>
    </html>
    """


# ----------------------
# Helper: ไฮไลต์คำ
# ----------------------
def highlight_sentence(sentence: str, words: list[str]) -> str:
    for w in words:
        sentence = sentence.replace(
            w,
            f'<span style="color:red; font-weight:bold;">{w}</span>'
        )
    return sentence

# ----------------------
# ตรวจจากข้อความ (Check Web)
# ----------------------
@app.post("/check-web", response_class=HTMLResponse)
def check_web(text: str = Form(...)):
    is_bad, bad_sentences = check_exaggeration(text)

    total = len(bad_sentences)
    risk_level = "สูง" if total >= 3 else "ปานกลาง" if total == 2 else "ต่ำ"

    # -------- LLM Explainability --------
    llm_result = ""
    if is_bad and bad_sentences:
        found_words = []
        for item in bad_sentences:
            found_words.extend(item["words"])
        llm_result = explain_with_llm(text, found_words)

    # -------- รายละเอียด rule-based --------
    detail_html = ""

    if is_bad and bad_sentences:
        detail_html = "".join(
            f"""
            <div class="card">
                <div class="sentence">
                    ❌ {highlight_sentence(item["sentence"], item["words"])}
                </div>

                <ul>
                    {''.join(f"<li>📜 {r}</li>" for r in item["reasons"])}
                </ul>

                <div style="margin-top:8px;">
                    {''.join(
                        f"<span style='background:#fff3cd;color:#856404;"
                        f"padding:4px 8px;border-radius:6px;font-size:12px;"
                        f"margin-right:6px;'>⚠️ {c}</span>"
                        for c in item.get("risk_categories", [])
                    )}
                </div>
            </div>
            """
            for item in bad_sentences
        )

    # แปลง text ให้ปลอดภัยสำหรับใส่ใน HTML attribute
    safe_text_value = html.escape(text)

    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                padding: 40px;
            }}
            .box {{
                background: white;
                padding: 30px;
                max-width: 900px;
                margin: auto;
                border-radius: 10px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            }}
            .summary {{
                padding: 15px;
                border-radius: 8px;
                background: {'#ffe5e5' if is_bad else '#e6fffa'};
                margin-bottom: 20px;
                border-left: 5px solid {'#ef4444' if is_bad else '#10b981'};
            }}
            .card {{
                border: 1px solid #eee;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 15px;
            }}
            pre {{
                white-space: pre-wrap;
                background: #fafafa;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #4f46e5;
            }}
            .btn-suggest {{
                background: #7c3aed;
                color: white;
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                font-size: 15px;
                cursor: pointer;
                margin-top: 10px;
                margin-bottom: 20px;
                transition: background 0.2s;
            }}
            .btn-suggest:hover {{
                background: #6d28d9;
            }}
        </style>
    </head>

    <body>
        <div class="box">
            <h2>📊 ผลการตรวจสอบโฆษณา</h2>

            <div class="summary">
                <b>ผลลัพธ์:</b> {'⚠️ พบข้อความโฆษณาเกินจริง' if is_bad else '✅ ปลอดภัย'}<br>
                <b>จำนวนประโยคที่เข้าข่าย:</b> {total}<br>
                <b>ระดับความเสี่ยง:</b> {risk_level}
            </div>

            <h3>🔍 วิเคราะห์ตามกฎ (Rule-based)</h3>
            {detail_html}

            <hr>

            <h3>🧠 คำอธิบายจาก AI (LLM)</h3>
            <pre>{llm_result if llm_result else "ไม่มีการเรียกใช้ LLM หรือไม่พบข้อผิดพลาด"}</pre>

            <form method="post" action="/suggest">
                <input type="hidden" name="text" value="{safe_text_value}">
                <button type="submit" class="btn-suggest">
                    ✨ แนะนำข้อความที่ปลอดภัยแทน
                </button>
            </form>

            <a href="/" style="text-decoration:none; color:#555;">⬅️ กลับหน้าหลัก</a>
        </div>
    </body>
    </html>
    """

# ----------------------
# ตรวจจากลิงก์เว็บ (Check URL)
# ----------------------
@app.post("/check-url", response_class=HTMLResponse)
def check_url(url: str = Form(...)):
    try:
        text = scrape_text(url)

        if not text or len(text.strip()) < 50:
            raise ValueError("ไม่พบข้อความโฆษณาที่ชัดเจน หรือข้อความสั้นเกินไป")

        is_bad, bad_sentences = check_exaggeration(text)

        llm_result = ""
        if is_bad and bad_sentences:
            found_words = []
            for item in bad_sentences:
                found_words.extend(item["words"])
            llm_result = explain_with_llm(text, found_words)
        
        # แปลง text ให้ปลอดภัยสำหรับใส่ใน HTML attribute
        safe_text_value = html.escape(text)

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
        <head>
            <style>
                .btn-suggest {{
                    background: #7c3aed;
                    color: white;
                    padding: 10px 18px;
                    border: none;
                    border-radius: 6px;
                    font-size: 15px;
                    cursor: pointer;
                    margin-top: 10px;
                    margin-bottom: 20px;
                }}
                .btn-suggest:hover {{
                    background: #6d28d9;
                }}
            </style>
        </head>
        <body style="font-family:Arial, sans-serif; background:#f5f5f5; padding:40px;">
            <div style="background:white; padding:30px; max-width:900px; margin:auto; border-radius:10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                <h2>ผลการตรวจจากลิงก์</h2>
                <p style="color:gray;"><b>ลิงก์:</b> {url}</p>

                <hr>

                {"<div style='background:#ffe5e5; padding:15px; border-radius:8px; border-left:5px solid #ef4444; color:#b91c1c;'>⚠️ พบข้อความโฆษณาเกินจริง</div>" if is_bad else "<div style='background:#e6fffa; padding:15px; border-radius:8px; border-left:5px solid #10b981; color:#047857;'>✅ ไม่พบข้อความโฆษณาเกินจริง</div>"}

                <br>
                {''.join(
                    f'''
                    <div style="margin-bottom:20px; border:1px solid #eee; padding:15px; border-radius:8px;">
                        <p>❌ {highlight_sentence(item["sentence"], item["words"])}</p>
                        <ul>
                            {''.join(f"<li>📜 {r}</li>" for r in item["reasons"])}
                        </ul>
                    </div>
                    '''
                    for item in bad_sentences
                )}

                <hr>
                <h3>🧠 คำอธิบายจาก AI (LLM)</h3>
                <pre style="white-space:pre-wrap; background:#fafafa; padding:15px; border-radius:8px; border-left: 4px solid #4f46e5;">{llm_result if llm_result else "ไม่มีการเรียกใช้ LLM"}</pre>

                <form method="post" action="/suggest">
                    <input type="hidden" name="text" value="{safe_text_value}">
                    <button type="submit" class="btn-suggest">
                        ✨ แนะนำข้อความที่ปลอดภัยแทน
                    </button>
                </form>

                <a href="/" style="text-decoration:none; color:#555;">⬅️ กลับหน้าหลัก</a>
            </div>
        </body>
    </html>
    """

# ----------------------
# แนะนำข้อความ (Suggest)
# ----------------------
@app.post("/suggest", response_class=HTMLResponse)
def suggest(text: str = Form(...)):
    safe_version = suggest_safe_text(text)

    return f"""
    <html>
    <body style="font-family:Arial, sans-serif; background:#f4f6f8; padding:40px;">
        <div style="background:white; padding:30px; max-width:800px; margin:auto; border-radius:10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <h2>✨ ข้อความโฆษณาที่ปลอดภัยกว่า</h2>
            <p style="color:gray;">AI ได้ปรับแก้ข้อความของคุณให้ถูกต้องตามกฎหมายโฆษณา (อย./สคบ.)</p>
            <hr>

            <h4>📝 ข้อความที่แนะนำ:</h4>
            <div style="background:#f0fdf4; padding:20px; border-left:5px solid #16a34a; font-size:16px; line-height:1.6; border-radius:4px;">
                {safe_version.replace('\n', '<br>')}
            </div>

            <br>
            <a href="/" style="text-decoration:none; display:inline-block; margin-top:10px; color:#555;">⬅️ กลับหน้าหลัก</a>
        </div>
    </body>
    </html>
    """