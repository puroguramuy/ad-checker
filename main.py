from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import html
import re  # ใช้สำหรับการตัดคำ (Regular Expression) เพื่อนับจำนวนประโยค

# Import โมดูลที่เราเขียนแยกไว้ (ต้องมีไฟล์พวกนี้อยู่ในโฟลเดอร์เดียวกันนะ)
from rules import check_exaggeration       # ฟังก์ชันตรวจคำผิดด้วย Rule-based
from scraper import scrape_text            # ฟังก์ชันดึงข้อความจาก URL
from llm_explainer import explain_with_llm, suggest_safe_text # ฟังก์ชันคุยกับ AI

app = FastAPI()

# ==========================================
# 🧠 ส่วนที่ 1: Logic การคำนวณคะแนน (Score System)
# ==========================================
def calculate_ad_score(text, bad_sentences):
    """
    ฟังก์ชันคำนวณคะแนนความปลอดภัยของโฆษณา
    * ใช้ระบบ Density: คิด % คำผิดเทียบกับความยาวบทความ
    * เหมาะสำหรับทั้ง Caption สั้นๆ และ Website ยาวๆ
    """
    
    # 1.1 ตัดประโยคเพื่อหาจำนวนทั้งหมด (Total Sentences)
    all_sentences = [s.strip() for s in re.split(r'[\n.!?]+', text) if s.strip()]
    total_sentences = max(1, len(all_sentences)) # ป้องกันการหารด้วย 0
    
    # 1.2 กำหนดคำต้องห้ามร้ายแรง (Violation) -> ผิดกฎหมายชัดเจน
    violation_keywords = ["รักษา", "หายขาด", "บำบัด", "ป้องกันโรค", "รับรองผล", "การันตี", "เห็นผลจริง", "100%"]
    
    count_violation = 0  # ตัวนับ: ผิดกฎ (สีแดง)
    count_risk = 0       # ตัวนับ: เสี่ยง (สีเหลือง)
    
    # 1.3 วนลูปเช็ครายการที่ผิด
    for item in bad_sentences:
        is_violation = False
        # เช็คว่าคำที่ผิด มีคำร้ายแรงผสมอยู่ไหม
        for w in item['words']:
            if any(k in w for k in violation_keywords):
                is_violation = True
                break
        
        if is_violation:
            count_violation += 1
            item['severity'] = 'violation' 
        else:
            count_risk += 1
            item['severity'] = 'risk'

    # 1.4 คำนวณจำนวนที่ผ่าน (Pass)
    total_bad = count_violation + count_risk
    
    # กันเหนียวเผื่อตัดประโยคผิดพลาด (ไม่ให้ติดลบ)
    if total_bad > total_sentences:
        total_sentences = total_bad
        
    count_pass = max(0, total_sentences - total_bad)
    
    # ---------------------------------------------------
    # 🔥 สูตรใหม่: หักคะแนนตาม "ความหนาแน่น" (Density)
    # ---------------------------------------------------
    # หาอัตราส่วนคำผิด (0.0 - 1.0)
    risk_ratio = count_risk / total_sentences
    violation_ratio = count_violation / total_sentences
    
    # ตัวคูณบทลงโทษ (Penalty Multiplier)
    # - Risk: คูณ 1.5 (ผิด 10% หัก 15 คะแนน)
    # - Violation: คูณ 5.0 (ผิด 10% หัก 50 คะแนน)
    deduction = (risk_ratio * 100 * 1.5) + (violation_ratio * 100 * 5.0)
    
    score = 100 - deduction
    
    # ---------------------------------------------------
    # 🔒 กฎเหล็ก (Safety Cap): ผิดกฎหมาย 1 จุด = สอบตกทันที
    # ---------------------------------------------------
    # ต่อให้ข้อความยาวมาก แต่ถ้ามีคำว่า "รักษาหายขาด" (Red) แค่คำเดียว
    # ต้องปรับตกเพื่อให้ User แก้ไขก่อน (คะแนนไม่เกิน 49 = สีแดง/ส้ม)
    if count_violation > 0:
        score = min(score, 49)
        
    score = max(0, int(score)) # ปัดเศษเป็นจำนวนเต็มและห้ามติดลบ

    # ส่งค่ากลับไปแสดงผล
    return {
        "score": score,
        "total": total_sentences,
        "pass": count_pass,
        "risk": count_risk,
        "violation": count_violation
    }

# ==========================================
# 🎨 ส่วนที่ 2: HTML/CSS Template (UI)
# ==========================================
def get_base_html(content: str, title: str = "Ad Checker"):
    """
    ฟังก์ชันเก็บโครงสร้าง HTML/CSS หลัก (Template)
    เพื่อให้ทุกหน้ามีหน้าตาเหมือนกัน แก้ที่เดียวเปลี่ยนทุกหน้า
    """
    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap" rel="stylesheet">

        <style>
            :root {{
                --primary: #4F46E5;       /* ม่วง Theme หลัก */
                --primary-hover: #4338ca;
                --bg-body: #F3F4F6;
                --card-bg: #FFFFFF;
                --text-main: #1F2937;
                --danger: #EF4444;        /* แดง */
                --success: #10B981;       /* เขียว */
                --warning: #F59E0B;       /* เหลือง */
            }}
            
            body {{
                font-family: 'Prompt', sans-serif;
                background-color: var(--bg-body);
                color: var(--text-main);
                margin: 0;
                padding-bottom: 40px;
                line-height: 1.6;
            }}

            /* Navbar */
            .navbar {{
                background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
                color: white;
                padding: 20px 0;
                text-align: center;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                margin-bottom: 30px;
            }}
            .navbar h1 {{ margin: 0; font-size: 1.8rem; font-weight: 600; }}

            /* Layout */
            .container {{ max-width: 850px; margin: 0 auto; padding: 0 20px; }}
            .card {{
                background: var(--card-bg);
                border-radius: 16px;
                padding: 30px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                margin-bottom: 25px;
            }}

            /* Form */
            textarea, input[type="text"] {{
                width: 100%; padding: 12px; border: 1px solid #D1D5DB; border-radius: 8px;
                font-family: 'Prompt', sans-serif; margin-bottom: 15px; box-sizing: border-box;
            }}
            button {{
                background-color: var(--primary); color: white; border: none;
                padding: 12px 24px; border-radius: 8px; cursor: pointer; transition: 0.2s;
            }}
            button:hover {{ background-color: var(--primary-hover); }}
            button.btn-suggest {{ 
                background: linear-gradient(to right, #7C3AED, #DB2777); 
                width: 100%; font-weight: bold;
            }}
            
            /* Score Dashboard */
            .score-container {{ display: flex; align-items: center; gap: 30px; }}
            .score-circle {{
                width: 130px; height: 130px; border-radius: 50%;
                display: flex; flex-direction: column;
                align-items: center; justify-content: center;
                font-weight: bold; flex-shrink: 0; background: white;
            }}
            .score-number {{ font-size: 3rem; line-height: 1; }}
            .score-label {{ font-size: 0.9rem; color: #6B7280; font-weight: normal; }}
            
            /* Stats Bars */
            .stat-bars {{ flex-grow: 1; }}
            .stat-row {{ display: flex; align-items: center; margin-bottom: 12px; }}
            .stat-icon {{ width: 30px; text-align:center; }}
            .stat-name {{ width: 120px; font-size: 0.95rem; }}
            .stat-bar-bg {{ flex-grow: 1; height: 10px; background: #F3F4F6; border-radius: 5px; margin: 0 15px; }}
            .stat-bar-fill {{ height: 100%; border-radius: 5px; }}
            .stat-count {{ width: 30px; text-align: right; font-weight: bold; }}

            /* How it works Section (ส่วนที่เพิ่มใหม่) */
            .steps-container {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin-top: 10px;
            }}
            .step-box {{
                background: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
            }}
            .step-icon {{
                background: #EEF2FF;
                color: var(--primary);
                width: 40px; height: 40px;
                border-radius: 50%;
                display: flex; align-items: center; justify-content: center;
                font-weight: bold; font-size: 1.2rem;
                margin: 0 auto 10px auto;
            }}
            .step-title {{ font-weight: 600; margin-bottom: 8px; color: #111827; }}
            .step-desc {{ font-size: 0.85rem; color: #6B7280; list-style: none; padding: 0; margin: 0; }}
            .step-desc li {{ margin-bottom: 4px; }}

            /* Loading Spinner */
            #loading-overlay {{
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(255,255,255,0.9);
                display: none; justify-content: center; align-items: center;
                flex-direction: column; z-index: 999;
            }}
            .spinner {{
                width: 50px; height: 50px; border: 5px solid #E5E7EB;
                border-top: 5px solid var(--primary); border-radius: 50%;
                animation: spin 1s linear infinite; margin-bottom: 15px;
            }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            
            a {{ text-decoration: none; color: #6B7280; }}
            a:hover {{ color: var(--primary); }}
            
            /* Responsive Grid */
            @media (max-width: 768px) {{
                .steps-container, .score-container {{ flex-direction: column; grid-template-columns: 1fr; }}
                .stat-bars {{ width: 100%; }}
            }}
        </style>
        
        <script>
            function showLoading() {{
                document.getElementById('loading-overlay').style.display = 'flex';
            }}
            function copyToClipboard() {{
                 var text = document.getElementById("safe-text-content").innerText;
                 navigator.clipboard.writeText(text).then(function() {{
                     alert("คัดลอกข้อความเรียบร้อย! ✅");
                 }});
            }}
        </script>
    </head>
    <body>
        <div id="loading-overlay">
            <div class="spinner"></div>
            <div style="font-weight: 500; color: #4F46E5;">กำลังวิเคราะห์ข้อมูล...</div>
        </div>

        <div class="navbar">
            <div class="container">
                <h1>🛡️ Ad-Checker</h1>
                <p>เว็บตรวจจับข้อความโฆษณาเกินจริง (AI & Rule-based)</p>
            </div>
        </div>

        <div class="container">
            {content}
        </div>

        <footer style="text-align: center; margin-top: 40px; color: #9CA3AF; font-size: 0.85rem;">
            © 2024 Ad Checker System | CS Project
        </footer>
    </body>
    </html>
    """

def highlight_sentence(sentence: str, words: list[str]) -> str:
    """ฟังก์ชันช่วยไฮไลท์คำผิด"""
    for w in words:
        sentence = sentence.replace(
            w, f'<span style="background-color: #FEE2E2; color: #DC2626; padding: 0 4px; border-radius: 4px; font-weight: 600;">{w}</span>'
        )
    return sentence

# ==========================================
# 🚀 ส่วนที่ 3: Routes (Endpoints)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def home():
    """หน้าแรก: เพิ่มส่วน How it works ตามที่ขอมา"""
    content = """
    <div style="display: grid; grid-template-columns: 1fr; gap: 20px;">
        
        <div class="card">
            <h3>📝 ตรวจสอบจากข้อความ</h3>
            <form method="post" action="/check-web" onsubmit="showLoading()">
                <textarea name="text" rows="5" placeholder="วางข้อความโฆษณาของคุณที่นี่..."></textarea>
                <div style="text-align: right;">
                    <button type="submit">🔍 ตรวจสอบทันที</button>
                </div>
            </form>
        </div>
        
        <div class="card">
            <h3>🌐 ตรวจสอบจากเว็บไซต์</h3>
            <form method="post" action="/check-url" onsubmit="showLoading()">
                <input type="text" name="url" placeholder="https://example.com/product">
                <div style="text-align: right;">
                    <button type="submit" style="background-color: #059669;">🔗 ดึงข้อมูลและตรวจสอบ</button>
                </div>
            </form>
        </div>

        <div class="card" style="border-top: 4px solid #4F46E5;">
            <h3 style="margin-bottom: 20px;">🔍 ระบบตรวจสอบทำงานอย่างไร?</h3>
            <div class="steps-container">
                <div class="step-box">
                    <div class="step-icon">1</div>
                    <div class="step-title">วิเคราะห์ข้อความ (Rule-based)</div>
                    <ul class="step-desc">
                        <li>- ตรวจคำอวดอ้างเกินจริง</li>
                        <li>- ตรวจคำต้องห้ามตามแนวทาง อย.</li>
                    </ul>
                </div>
                
                <div class="step-box">
                    <div class="step-icon">2</div>
                    <div class="step-title">ประเมินระดับความเสี่ยง</div>
                    <ul class="step-desc">
                        <li>- แยกแยะ: ผ่าน / เสี่ยง / ผิดกฎ</li>
                        <li>- คำนวณเป็นคะแนน (0–100)</li>
                    </ul>
                </div>

                <div class="step-box">
                    <div class="step-icon">3</div>
                    <div class="step-title">ใช้ AI อธิบายและแนะนำ</div>
                    <ul class="step-desc">
                        <li>- อธิบายเหตุผลเชิงกฎหมาย</li>
                        <li>- ช่วยร่างข้อความที่ปลอดภัยกว่า</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    """
    return get_base_html(content)


@app.post("/check-web", response_class=HTMLResponse)
def check_web(text: str = Form(...)):
    """ตรวจสอบข้อความ"""
    is_bad, bad_sentences = check_exaggeration(text)
    
    # คำนวณคะแนนด้วยสูตรใหม่
    stats = calculate_ad_score(text, bad_sentences)
    score = stats['score']
    
    # กำหนดสีและคำตัดสิน
    if score >= 80:
        score_color = "#10B981" # เขียว
        verdict = "ดีเยี่ยม (Safe)"
    elif score >= 50:
        score_color = "#F59E0B" # เหลือง
        verdict = "ปานกลาง (Warning)"
    else:
        score_color = "#EF4444" # แดง
        verdict = "เสี่ยงสูง (Danger)"

    # สร้าง Dashboard HTML
    dashboard_html = f"""
    <div class="card">
        <h2 style="margin-bottom:20px;">📊 ผลการวิเคราะห์คะแนน</h2>
        <div class="score-container">
            <div class="score-circle" style="border: 10px solid {score_color}; color: {score_color};">
                <span class="score-number">{score}</span>
                <span class="score-label">{verdict}</span>
            </div>
            <div class="stat-bars">
                <div class="stat-row">
                    <div class="stat-icon">✅</div> <div class="stat-name">ผ่านเกณฑ์</div>
                    <div class="stat-bar-bg"><div class="stat-bar-fill" style="width: {(stats['pass']/stats['total'])*100}%; background: #10B981;"></div></div>
                    <div class="stat-count" style="color: #10B981;">{stats['pass']}</div>
                </div>
                <div class="stat-row">
                    <div class="stat-icon">⚠️</div> <div class="stat-name">ควรปรับปรุง</div>
                    <div class="stat-bar-bg"><div class="stat-bar-fill" style="width: {(stats['risk']/stats['total'])*100}%; background: #F59E0B;"></div></div>
                    <div class="stat-count" style="color: #F59E0B;">{stats['risk']}</div>
                </div>
                <div class="stat-row">
                    <div class="stat-icon">❌</div> <div class="stat-name">ผิดกฎชัดเจน</div>
                    <div class="stat-bar-bg"><div class="stat-bar-fill" style="width: {(stats['violation']/stats['total'])*100}%; background: #EF4444;"></div></div>
                    <div class="stat-count" style="color: #EF4444;">{stats['violation']}</div>
                </div>
            </div>
        </div>
    </div>
    """

    # LLM Logic
    llm_result = ""
    if is_bad and bad_sentences:
        found_words = []
        for item in bad_sentences:
            found_words.extend(item["words"])
        llm_result = explain_with_llm(text, found_words)

    # รายละเอียดจุดผิด
    detail_html = ""
    if is_bad and bad_sentences:
        for item in bad_sentences:
            severity = item.get('severity', 'risk')
            icon = "❌" if severity == "violation" else "⚠️"
            bg_color = "#FEF2F2" if severity == "violation" else "#FFFBEB"
            border_color = "#EF4444" if severity == "violation" else "#F59E0B"
            
            reasons = "".join([f"<li>{r}</li>" for r in item["reasons"]])
            
            detail_html += f"""
            <div style="background:{bg_color}; border-left:4px solid {border_color}; padding:15px; margin-bottom:10px; border-radius:6px;">
                <div style="font-weight:bold; margin-bottom:5px; color:#1F2937; font-size:1.05rem;">
                    {icon} {highlight_sentence(item["sentence"], item["words"])}
                </div>
                <ul style="color:#4B5563; font-size:0.95rem; margin:0; padding-left:20px;">{reasons}</ul>
            </div>
            """

    safe_text_value = html.escape(text)
    content = f"""
    <a href="/" style="display:inline-block; margin-bottom:20px;">⬅️ กลับหน้าหลัก</a>
    {dashboard_html}
    {f'<div class="card"><h3>🔍 รายละเอียดจุดที่ต้องแก้ไข</h3>{detail_html}</div>' if detail_html else ''}
    <div class="card" style="border-top: 5px solid #4F46E5;">
        <h3>🧠 คำแนะนำจาก AI</h3>
        <div style="background:#F9FAFB; padding:20px; border-radius:8px; white-space: pre-wrap;">{llm_result if llm_result else "ไม่พบประเด็นสำคัญ หรือไม่มีการเรียกใช้ AI"}</div>
        <form method="post" action="/suggest" onsubmit="showLoading()" style="margin-top:20px;">
            <input type="hidden" name="text" value="{safe_text_value}">
            <button type="submit" class="btn-suggest">✨ ให้ AI ช่วยร่างข้อความใหม่ (Magic Rewrite)</button>
        </form>
    </div>
    """
    return get_base_html(content)


@app.post("/check-url", response_class=HTMLResponse)
def check_url(url: str = Form(...)):
    """ตรวจสอบ URL"""
    try:
        text = scrape_text(url)
        if not text or len(text.strip()) < 50:
            raise ValueError("ไม่พบข้อความ หรือข้อความสั้นเกินไป")

        is_bad, bad_sentences = check_exaggeration(text)
        stats = calculate_ad_score(text, bad_sentences)
        
        score = stats['score']
        score_color = "#10B981" if score >= 80 else "#F59E0B" if score >= 50 else "#EF4444"
        verdict = "ดีเยี่ยม" if score >= 80 else "ปานกลาง" if score >= 50 else "เสี่ยงสูง"

        dashboard_html = f"""
        <div class="card">
            <h2 style="margin-bottom:10px;">📊 ผลการวิเคราะห์ลิงก์</h2>
            <p style="color:#6B7280; margin-bottom:20px;">URL: <a href="{url}" target="_blank">{url}</a></p>
            <div class="score-container">
                <div class="score-circle" style="border: 10px solid {score_color}; color: {score_color};">
                    <span class="score-number">{score}</span>
                    <span class="score-label">{verdict}</span>
                </div>
                <div class="stat-bars">
                    <div class="stat-row"><div class="stat-icon">✅</div> <div class="stat-bar-bg"><div class="stat-bar-fill" style="width: {(stats['pass']/stats['total'])*100}%; background: #10B981;"></div></div><div class="stat-count" style="color:#10B981">{stats['pass']}</div></div>
                    <div class="stat-row"><div class="stat-icon">⚠️</div> <div class="stat-bar-bg"><div class="stat-bar-fill" style="width: {(stats['risk']/stats['total'])*100}%; background: #F59E0B;"></div></div><div class="stat-count" style="color:#F59E0B">{stats['risk']}</div></div>
                    <div class="stat-row"><div class="stat-icon">❌</div> <div class="stat-bar-bg"><div class="stat-bar-fill" style="width: {(stats['violation']/stats['total'])*100}%; background: #EF4444;"></div></div><div class="stat-count" style="color:#EF4444">{stats['violation']}</div></div>
                </div>
            </div>
        </div>
        """
        
        llm_result = ""
        if is_bad and bad_sentences:
            found_words = []
            for item in bad_sentences:
                found_words.extend(item["words"])
            llm_result = explain_with_llm(text, found_words)

        detail_html = ""
        if is_bad and bad_sentences:
            for item in bad_sentences:
                severity = item.get('severity', 'risk')
                icon = "❌" if severity == "violation" else "⚠️"
                bg_color = "#FEF2F2" if severity == "violation" else "#FFFBEB"
                border_color = "#EF4444" if severity == "violation" else "#F59E0B"
                reasons = "".join([f"<li>{r}</li>" for r in item["reasons"]])
                detail_html += f"""
                <div style="background:{bg_color}; border-left:4px solid {border_color}; padding:15px; margin-bottom:10px; border-radius:6px;">
                    <div style="font-weight:bold; margin-bottom:5px; color:#1F2937;">{icon} {highlight_sentence(item["sentence"], item["words"])}</div>
                    <ul style="color:#4B5563; font-size:0.9rem; margin:0; padding-left:20px;">{reasons}</ul>
                </div>
                """

        safe_text_value = html.escape(text)
        content = f"""
        <a href="/" style="display:inline-block; margin-bottom:20px;">⬅️ กลับหน้าหลัก</a>
        {dashboard_html}
        {f'<div class="card"><h3>🔍 รายละเอียด</h3>{detail_html}</div>' if detail_html else ''}
        <div class="card">
            <h3>🧠 AI Opinion</h3>
            <div style="background:#F9FAFB; padding:20px; border-radius:8px;">{llm_result if llm_result else "-"}</div>
            <form method="post" action="/suggest" onsubmit="showLoading()" style="margin-top:20px;">
                <input type="hidden" name="text" value="{safe_text_value}">
                <button type="submit" class="btn-suggest">✨ สร้างข้อความใหม่</button>
            </form>
        </div>
        """
        return get_base_html(content)

    except Exception as e:
        content = f"""
        <div class="card" style="text-align:center; padding:50px;">
            <div style="font-size:3rem;">❌</div>
            <h2>เกิดข้อผิดพลาด</h2>
            <p style="color:#EF4444;">{e}</p>
            <br><a href="/" style="text-decoration:underline;">ลองใหม่อีกครั้ง</a>
        </div>
        """
        return get_base_html(content)


@app.post("/suggest", response_class=HTMLResponse)
def suggest(text: str = Form(...)):
    """หน้า Suggestion"""
    safe_version = suggest_safe_text(text)
    
    content = f"""
    <a href="/" style="display:inline-block; margin-bottom:20px;">⬅️ กลับหน้าหลัก</a>
    <div class="card" style="border-top: 5px solid #10B981;">
        <div style="text-align:center; margin-bottom:20px;">
            <div style="font-size:3rem; margin-bottom:5px;">✨</div>
            <h2>ข้อความที่แนะนำ (Safe Version)</h2>
            <p style="color:#6B7280;">AI ได้ปรับปรุงให้ถูกต้องตามกฎหมายโฆษณาแล้ว</p>
        </div>

        <div style="background:#ECFDF5; padding:25px; border-radius:12px; border: 1px solid #A7F3D0; color: #065F46; font-size:1.1rem; line-height:1.8; position: relative;">
            <div id="safe-text-content">{safe_version.replace('\n', '<br>')}</div>
        </div>
        
        <div style="text-align:center; margin-top:20px;">
             <button onclick="copyToClipboard()" style="background:#374151; font-size:0.9rem;">📋 คัดลอกข้อความ</button>
        </div>
    </div>
    """
    return get_base_html(content)