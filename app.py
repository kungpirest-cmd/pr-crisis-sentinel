# ==============================================================================
# ส่วนที่ 1: Import ไลบรารีที่จำเป็นทั้งหมด
# ==============================================================================
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import json
import pandas as pd
import time
from wordcloud import WordCloud
from pythainlp.tokenize import word_tokenize
from pythainlp.corpus import thai_stopwords
import collections
from analysis_engine import get_news_from_api, analyze_sentiment_with_gemini
import sqlite3
from datetime import datetime
import google.generativeai as genai
import os
import requests
from functools import wraps

# ==============================================================================
# ส่วนที่ 2: ตั้งค่าต่างๆ
# ==============================================================================
app = Flask(__name__)
# ===== START: เพิ่มการตั้งค่าสำหรับระบบ Login =====
app.secret_key = 'rbtech' # ตั้งรหัสลับ (เปลี่ยนเป็นอะไรก็ได้)
PIN_CODE = "212224" # <<<< ตั้งรหัส PIN 6 หลักของคุณที่นี่
# =============================================
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')



# ===== START: เพิ่มหน่วยความจำสำหรับเก็บสถานะล่าสุด =====
latest_analysis_status = {
    "keyword": None,
    "status": "normal",
    "timestamp": 0 # เพิ่มนาฬิกาจับเวลา
}
# =======================================================

# --- พจนานุกรมคำศัพท์สำหรับแผนสำรอง ---
NEGATIVE_KEYWORDS = [
    "ล่ม", "ร้องเรียน", "ข้อมูลรั่ว", "ตกต่ำ", "วิกฤต", "ปัญหา", "ขัดข้อง", "ฟ้อง", "เสียหาย",
    "แฉ", "โกง", "ทุจจริต", "ดราม่า", "ร้องทุกข์", "ตกฮวบ", "ขาดทุน", "หนี้สิน", "ล้มละลาย",
    "ถดถอย", "ซบเซา", "ลดลง", "ต่ำสุด", "ติดลบ", "ย่ำแย่", "หดตัว", "ชะลอตัว", "ผันผวน",
    "เสี่ยง", "ฟองสบู่", "ฉ้อโกง", "ยักยอก", "ฟอกเงิน", "ผิดนัดชำระ", "ถูกปรับ", "คว่ำบาตร",
    "ภาษีเพิ่ม", "เงินเฟ้อ", "ว่างงาน", "ห่วย", "แย่", "ไม่ดี", "ช้า", "ล่าช้า", "มีตำหนิ",
    "ใช้งานไม่ได้", "อันตราย", "ไม่ปลอดภัย", "คุณภาพต่ำ", "ของปลอม", "ไม่ได้มาตรฐาน",
    "ยกเลิกบริการ", "ปิดปรับปรุง", "ไม่พอใจ", "โวย", "ประท้วง", "เรียกร้อง", "เดือดร้อน",
    "ถูกหลอก", "เอาเปรียบ", "บริการแย่", "อื้อฉาว", "ข่าวฉาว", "เสื่อมเสีย", "ถูกวิจารณ์",
    "ตำหนิ", "โจมตี", "ขัดแย้ง", "ถูกสอบสวน", "ดำเนินคดี", "ละเมิด", "ผิดกฎหมาย", "ปกปิด",
    "ปิดบัง", "ซ่อนเร้น", "ปฏิเสธ", "ปลดออก", "เลิกจ้าง", "ปิดกิจการ", "ยุติ", "ล้มเหลว",
    "อุปสรรค", "ผลกระทบ", "วุ่นวาย", "กังวล", "น่าเป็นห่วง", "เลวร้าย", "หนัก", "สาหัส",
    "รุนแรง", "สูญเสีย", "เสียชีวิต", "บาดเจ็บ", "ภัยพิบัติ", "ฉุกเฉิน", "เตือนภัย"
]
POSITIVE_KEYWORDS = [
    "กำไร", "สูงสุด", "เปิดตัว", "สำเร็จ", "รางวัล", "ชื่นชม", "ขยาย", "พัฒนา", "ร่วมมือ",
    "อันดับ 1", "เติบโต", "สถิติใหม่", "พุ่ง", "ทะยาน", "เพิ่มขึ้น", "ขยายตัว", "แข็งแกร่ง",
    "มั่นคง", "ผลประกอบการดี", "โบนัส", "ปันผล", "เกินคาด", "ฟื้นตัว", "ตลาดกระทิง",
    "ลงทุนเพิ่ม", "ซื้อกิจการ", "ระดมทุน", "ยอดเยี่ยม", "ดีเลิศ", "คุณภาพสูง", "นวัตกรรม",
    "รุ่นใหม่", "ทันสมัย", "สะดวก", "รวดเร็ว", "ปลอดภัย", "ได้มาตรฐาน", "เป็นที่ยอมรับ",
    "ได้รับความนิยม", "ขายดี", "หมดเกลี้ยง", "พึงพอใจ", "ประทับใจ", "ตอบรับดี", "แห่ซื้อ",
    "ยอดจองถล่มทลาย", "สนับสนุน", "เชื่อมั่น", "ภักดี", "ภาพลักษณ์ดี", "เป็นผู้นำ",
    "สร้างชื่อเสียง", "ได้รับการยกย่อง", "ผ่านการรับรอง", "มาตรฐานสากล", "MOU", "พันธมิตร",
    "วิสัยทัศน์", "บรรลุเป้าหมาย", "ฉลอง", "ครบรอบ", "แต่งตั้ง", "โปรโมท", "เลื่อนตำแหน่ง",
    "วิสัยทัศน์กว้างไกล", "โอกาส", "อนาคต", "สดใส", "ก้าวหน้า", "ยกระดับ", "ส่งเสริม",
    "ช่วยเหลือ", "บริจาค", "คืนสู่สังคม", "CSR", "สร้างสรรค์", "ยิ่งใหญ่", "ประสบความสำเร็จ",
    "น่ายินดี", "ข่าวดี", "ศักยภาพ", "แข็งแกร่ง", "โดดเด่น"
]
NEGATION_WORDS = [
    "ไม่", "มิ", "มิใช่", "หามิได้", "ไม่ใช่", "ไม่มี", "ไร้", "ปราศจาก", "ยังไม่", "ไม่ได้",
    "ไม่เคย", "ไม่เคยมี", "มิได้", "ปฏิเสธ", "ไม่ยอม", "ไม่ยอมรับ", "คัดค้าน", "ไม่เห็นด้วย",
    "โต้แย้ง", "ขัดขวาง", "ยับยั้ง", "ขาด", "ขาดแคลน", "ว่างเปล่า", "สูญ", "สิ้น", "หมด",
    "หมดสิ้น", "สูญสิ้น", "ปราศจากซึ่ง", "หยุด", "ยุติ", "ยกเลิก", "งด", "ละเว้น", "เลิก",
    "เพิกถอน", "ชะงัก", "ระงับ", "เลื่อน", "ป้องกัน", "หลีกเลี่ยง", "ห้าม", "เว้น", "ปลอดจาก",
    "พ้นจาก", "ไม่แน่ใจ", "ไม่ชัดเจน", "คลุมเครือ", "น่าสงสัย", "ไม่ยืนยัน", "ไม่ใช่ว่า",
    "ไม่เชิงว่า", "ไม่ได้หมายความว่า", "ไม่จำเป็นต้อง", "ยากที่จะ", "เป็นไปไม่ได้", "ยังไม่มี",
    "ไร้วี่แวว", "นอกเหนือจาก", "ยกเว้น", "โดยไม่มี", "โดยปราศจาก"
]

# ==============================================================================
# ส่วนที่ 3: ฟังก์ชันเสริมต่างๆ
# ==============================================================================
# ===== START: สร้าง "ยาม" ตรวจสอบการ Login =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# =============================================
@app.before_request
def check_session_timeout():
    SESSION_TIMEOUT_MINUTES = 30
    if 'logged_in' in session and 'last_activity' in session:
        # last_activity is stored as a timestamp string, convert it back to datetime
        last_activity = datetime.fromisoformat(session['last_activity'])
        now = datetime.now()
        if now - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            session.pop('logged_in', None)
            session.pop('last_activity', None)
            flash('คุณไม่ได้ใช้งานระบบนานเกิน 30 นาที กรุณาเข้าสู่ระบบใหม่อีกครั้ง')
            return redirect(url_for('login'))
    if 'logged_in' in session:
        # Update last activity time as a string
        session['last_activity'] = datetime.now().isoformat()

def apply_sentiment_rules(initial_label, text):
    final_label = initial_label
    text_lower = text.lower()
    def has_negation(keyword, text_segment):
        for neg in NEGATION_WORDS:
            if f"{neg}{keyword}" in text_segment or f"{neg} {keyword}" in text_segment:
                return True
        return False
    for keyword in NEGATIVE_KEYWORDS:
        if keyword in text_lower and not has_negation(keyword, text_lower):
            return "NEGATIVE"
    if initial_label == "NEUTRAL":
        for keyword in POSITIVE_KEYWORDS:
            if keyword in text_lower and not has_negation(keyword, text_lower):
                return "POSITIVE"
    return final_label

def create_wordcloud(text):
    if not text.strip(): return None
    # กรณีออนไลน์
    # font_path = 'fonts/Sarabun-Regular.ttf'
     # กรณีออฟไลน์
    font_path = 'C:/Windows/Fonts/tahoma.ttf' # กลับมาใช้ Path เดิมที่แน่นอนกว่า

    try:
        words = word_tokenize(text, engine='newmm')
        text_for_cloud = " ".join(words)
        wordcloud = WordCloud(font_path=font_path, width=800, height=400, background_color="white", regexp=r"[ก-๙]+").generate(text_for_cloud)
        timestamp = int(time.time())
        image_path = f'images/wordcloud_{timestamp}.png'
        full_path = f'static/{image_path}'
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        wordcloud.to_file(full_path)
        return image_path
    except Exception as e:
        print(f"Error: ไม่สามารถสร้าง Word Cloud ได้: {e}")
        return None

def extract_keywords(text):
    words = word_tokenize(text, engine='newmm')
    stopwords_list = thai_stopwords()
    keywords = [word for word in words if word not in stopwords_list and not word.isnumeric() and len(word) > 1]
    counter = collections.Counter(keywords)
    return [item[0] for item in counter.most_common(5)]

def save_to_history(keyword, percentages):
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO analysis_history (keyword, analysis_date, negative_percent, positive_percent, neutral_percent) VALUES (?, ?, ?, ?, ?)", (keyword, today, percentages.get('NEGATIVE', 0), percentages.get('POSITIVE', 0), percentages.get('NEUTRAL', 0)))
    conn.commit()
    conn.close()

def get_historical_average(keyword):
    conn = sqlite3.connect('history.db')
    query = "SELECT AVG(negative_percent) FROM analysis_history WHERE keyword = ? AND analysis_date >= date('now', '-7 days')"
    df = pd.read_sql_query(query, conn, params=(keyword,))
    conn.close()
    historical_avg = df.iloc[0, 0]
    return historical_avg if pd.notna(historical_avg) else None

def send_telegram_notification(message):
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]) or "HERE" in TELEGRAM_BOT_TOKEN:
        print("Warning: ไม่ได้ตั้งค่า Telegram Bot Token หรือ Chat ID")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("ส่งการแจ้งเตือนผ่าน Telegram สำเร็จ")
            return True
        else:
            print(f"Error: ไม่สามารถส่ง Telegram Bot ได้: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"Error: เกิดข้อผิดพลาดในการเชื่อมต่อกับ Telegram: {e}")
        return False

# ==============================================================================
# ส่วนที่ 4: สร้างหน้าเว็บ (Routes)
# ==============================================================================
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    keyword = request.form.get('keyword', '').strip()

    # ===== START: อัปเดต keyword ทันที =====
    # เพื่อให้ ESP32 เห็นคำค้นหาล่าสุดเสมอ แม้ว่าจะไม่เจอข่าวก็ตาม
    latest_analysis_status["keyword"] = keyword
    # latest_analysis_status["timestamp"] = int(time.time()) # บันทึกเวลาปัจจุบัน
    print(f"Received search for '{keyword}', updating global keyword.")
    # ======================================
    
    articles = get_news_from_api(keyword, NEWS_API_KEY)
    
    results_data, labels, values = [], [], []
    wordcloud_image, top_keywords = None, None
    trend_message, trend_status = None, None
    sentiment_summary = {'POSITIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0}
    negative_headlines_for_js = []

    if not articles:
        # ถ้าไม่เจอข่าว ให้รีเซ็ต status เป็น normal
        latest_analysis_status["status"] = "normal"
        latest_analysis_status["timestamp"] = int(time.time()) # บันทึกเวลาปัจจุบัน
        print("No articles found. Setting status to normal.")
    else:
        try:
            analysis_results = analyze_sentiment_with_gemini(articles, model)
            print("Analysis successful using Gemini AI.")
            sentiments_set = {res['sentiment'] for res in analysis_results}
            if len(sentiments_set) == 1 and 'NEUTRAL' in sentiments_set:
                raise ValueError("Gemini analysis returned all NEUTRAL, likely an error.")
        except Exception as e:
            print(f"Warning: Gemini failed ({e}), using Rule-based system as fallback...")
            from transformers import pipeline
            sentiment_analyzer = pipeline("sentiment-analysis", model="lxyuan/distilbert-base-multilingual-cased-sentiments-student")
            headlines = [article['title'] for article in articles]
            initial_analysis = sentiment_analyzer(headlines)
            analysis_results = [{'title': article['title'], 'url': article['url'], 'sentiment': apply_sentiment_rules(initial_analysis[i]['label'].upper(), article['title'])} for i, article in enumerate(articles)]

        negative_headlines_text = ""
        label_map_thai = {"POSITIVE": "ข่าวเชิงบวก", "NEGATIVE": "ข่าวเชิงลบ", "NEUTRAL": "ข่าวเป็นกลาง"}
        
        for result in analysis_results:
            final_label = result['sentiment']
            sentiment_summary[final_label] += 1
            results_data.append({
                'title': result['title'], 'url': result['url'], 'sentiment': final_label,
                'sentiment_thai': label_map_thai.get(final_label, "ไม่ระบุ")
            })
            if final_label == 'NEGATIVE':
                negative_headlines_text += result['title'] + " "
                negative_headlines_for_js.append(result['title'])
        
        sort_order = {"NEGATIVE": 0, "NEUTRAL": 1, "POSITIVE": 2}
        results_data.sort(key=lambda x: sort_order.get(x['sentiment'], 3))

        total_articles = len(articles) if articles else 1
        percentages = {label: (count / total_articles) * 100 for label, count in sentiment_summary.items()}
        current_negative_percent = percentages.get('NEGATIVE', 0)
        save_to_history(keyword, percentages)
        historical_avg = get_historical_average(keyword)
        if historical_avg is not None and historical_avg > 0:
            if current_negative_percent > historical_avg * 1.2: trend_message, trend_status = f"สูงกว่าค่าเฉลี่ย 7 วันล่าสุด ({historical_avg:.1f}%)", "alert"
            elif current_negative_percent < historical_avg * 0.8: trend_message, trend_status = f"ต่ำกว่าค่าเฉลี่ย 7 วันล่าสุด ({historical_avg:.1f}%)", "good"
            else: trend_message, trend_status = f"ใกล้เคียงกับค่าเฉลี่ย 7 วันล่าสุด ({historical_avg:.1f}%)", "normal"
        else:
            trend_message, trend_status = "ยังไม่มีข้อมูลย้อนหลังเพียงพอ", "normal"
        
        is_volume_crisis = sentiment_summary['NEGATIVE'] > sentiment_summary['POSITIVE']
        if trend_status != 'alert' and is_volume_crisis:
            print("Volume crisis detected, overriding status to alert.")
            trend_status = 'alert'
            trend_message = f"สัดส่วนข่าวเชิงลบ ({sentiment_summary['NEGATIVE']}) มากกว่าข่าวเชิงบวก ({sentiment_summary['POSITIVE']})"

        # ===== START: อัปเดต status หลังวิเคราะห์เสร็จ =====
        latest_analysis_status["status"] = trend_status
        latest_analysis_status["timestamp"] = int(time.time())
        print(f"Analysis complete. Final status: {latest_analysis_status}")
        # ===============================================

        if negative_headlines_text:
            wordcloud_image = create_wordcloud(negative_headlines_text)
            top_keywords = extract_keywords(negative_headlines_text)
        
        if trend_status == 'alert':
            notification_message = f"Crisis Alert: {keyword}\nสถานการณ์: {trend_message}\nประเด็นร้อน: {', '.join(top_keywords)}"
            send_telegram_notification(notification_message)

        labels = [label_map_thai.get(label) for label in sentiment_summary.keys()]
        values = list(sentiment_summary.values())

    return render_template('index.html', 
                           keyword=keyword, results=results_data,
                           labels=json.dumps(labels), values=json.dumps(values),
                           wordcloud_image=wordcloud_image, top_keywords=top_keywords,
                           trend_message=trend_message, trend_status=trend_status,
                           sentiment_summary=sentiment_summary,
                           negative_headlines_for_js=negative_headlines_for_js)
                        
# ===== START: เพิ่ม Route สำหรับ Login และ Logout =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('pin') == PIN_CODE:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('รหัส PIN ไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))
# ===== END: เพิ่ม Route =====

@app.route('/get_pr_suggestion', methods=['POST'])
def get_pr_suggestion():
    data = request.json
    keyword = data.get('keyword')
    top_keywords = data.get('top_keywords')
    negative_headlines = data.get('negative_headlines')

    if not keyword or not top_keywords or not negative_headlines:
        return jsonify({'error': 'ยังไม่มีข้อมูลย้อนหลังเพียงพอ'}), 400

    prompt = f"""
    ในฐานะผู้เชี่ยวชาญด้านการประชาสัมพันธ์และการจัดการภาวะวิกฤต โปรดร่าง "ข้อความชี้แจงเบื้องต้น" สำหรับโพสต์ลงโซเชียลมีเดีย (เช่น Facebook, X) เพื่อสื่อสารกับสาธารณะเกี่ยวกับสถานการณ์เชิงลบที่เกิดขึ้น

    **ข้อมูลประกอบ:**
    - **แบรนด์ที่เกี่ยวข้อง:** {keyword}
    - **ประเด็นร้อนหลักที่ตรวจพบ:** {', '.join(top_keywords)}
    - **ตัวอย่างหัวข้อข่าวเชิงลบ:**
    {"\n".join([f"- {h}" for h in negative_headlines])}

    **ข้อกำหนดในการร่างข้อความ:**
    1.  ยอมรับปัญหา, 2. แสดงความห่วงใย, 3. แจ้งการดำเนินการ, 4. ระบุช่องทางติดต่อ, 5. ใช้ภาษาที่เป็นกลาง
    """
    try:
        safety_settings = {
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
        }
        response = model.generate_content(prompt, safety_settings=safety_settings)
        if not response.text:
            raise ValueError("Gemini returned an empty response.")
        return jsonify({'suggestion': response.text})
    except Exception as e:
        print(f"Warning: Gemini suggestion failed ({e}), providing a fallback response.")
        fallback_suggestion = f"""เรียน สื่อมวลชนและผู้ติดตามทุกท่าน,

จากกรณีที่เกิดขึ้นเกี่ยวกับ [{keyword}] ซึ่งเกี่ยวข้องกับประเด็น [{', '.join(top_keywords)}] ทางเราได้รับทราบถึงปัญหาดังกล่าวแล้ว และไม่ได้นิ่งนอนใจต่อสถานการณ์ที่เกิดขึ้น

ขณะนี้ทีมงานที่เกี่ยวข้องกำลังเร่งตรวจสอบข้อเท็จจริงอย่างเร่งด่วนที่สุดเพื่อทำความเข้าใจถึงสาเหตุของปัญหาและผลกระทบทั้งหมด

เราขออภัยเป็นอย่างสูงสำหรับความไม่สะดวกและความกังวลใจที่เกิดขึ้น และจะรีบชี้แจงรายละเอียดทั้งหมดให้ทราบอีกครั้งโดยเร็วที่สุด

ขอขอบพระคุณสำหรับความเข้าใจของท่าน
ทีมงานประชาสัมพันธ์ [{keyword}]"""
        return jsonify({'suggestion': fallback_suggestion})

@app.route('/get_executive_summary', methods=['POST'])
def get_executive_summary():
    data = request.json
    keyword = data.get('keyword')
    sentiment_summary = data.get('sentiment_summary')
    top_keywords = data.get('top_keywords')
    trend_message = data.get('trend_message')

    if not all([keyword, sentiment_summary, top_keywords, trend_message]):
        return jsonify({'error': 'ยังไม่มีข้อมูลย้อนหลังเพียงพอ'}), 400

    prompt = f"""
    ในฐานะนักวิเคราะห์กลยุทธ์อาวุโส โปรดสังเคราะห์ข้อมูลภาพลักษณ์ของแบรนด์ '{keyword}' ต่อไปนี้ และเขียน "บทสรุปสำหรับผู้บริหาร" (Executive Summary) ความยาว 1 ย่อหน้า (ไม่เกิน 4-5 บรรทัด) เพื่อให้ผู้บริหารเข้าใจสถานการณ์ได้อย่างรวดเร็วที่สุด

    **ข้อมูลดิบ:**
    - **สัดส่วนความรู้สึก:** ข่าวเชิงบวก {sentiment_summary.get('POSITIVE', 0)} รายการ, ข่าวเชิงลบ {sentiment_summary.get('NEGATIVE', 0)} รายการ, ข่าวเป็นกลาง {sentiment_summary.get('NEUTRAL', 0)} รายการ
    - **ประเด็นร้อนเชิงลบหลัก:** {', '.join(top_keywords) if top_keywords else 'ไม่มี'}
    - **แนวโน้มล่าสุด:** {trend_message}

    **ข้อกำหนด:**
    - เริ่มต้นด้วยการสรุปภาพรวม
    - ระบุประเด็นความเสี่ยงหลัก (ถ้ามี)
    - ให้ข้อเสนอแนะเชิงกลยุทธ์ 1 ข้อ
    - ใช้ภาษาที่เฉียบคม กระชับ และเป็นกลาง
    ---
    [เริ่มต้นบทสรุปที่นี่]
    """
    try:
        safety_settings = {
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
        }
        response = model.generate_content(prompt, safety_settings=safety_settings)
        if not response.text:
            raise ValueError("Gemini returned an empty response.")
        return jsonify({'summary': response.text})
    except Exception as e:
        print(f"Warning: Gemini executive summary failed ({e}), providing a fallback response.")
        fallback_summary = "ไม่สามารถสร้างบทสรุปอัตโนมัติได้ในขณะนี้ เนื่องจากเกิดข้อผิดพลาดในการเชื่อมต่อกับ AI กรุณาลองใหม่อีกครั้ง"
        return jsonify({'summary': fallback_summary})

@app.route('/send_summary_telegram', methods=['POST'])
def send_summary_telegram():
    data = request.json
    keyword = data.get('keyword')
    summary = data.get('summary')

    if not keyword or not summary:
        return jsonify({'success': False, 'message': 'ยังไม่มีข้อมูลย้อนหลังเพียงพอ'}), 400
    
    telegram_message = f"📄 *บทสรุปสำหรับผู้บริหาร: {keyword}*\n\n{summary}"
    
    success = send_telegram_notification(telegram_message)
    
    if success:
        return jsonify({'success': True, 'message': 'ส่งบทสรุปเข้า Telegram สำเร็จ'})
    else:
        return jsonify({'success': False, 'message': 'ไม่สามารถส่งบทสรุปเข้า Telegram ได้'}), 500

# ===== START: เพิ่มฟังก์ชันที่หายไปกลับเข้ามา =====
@app.route('/get_root_cause', methods=['POST'])
def get_root_cause():
    data = request.json
    negative_headlines = data.get('negative_headlines')

    if not negative_headlines:
        return jsonify({'error': 'ยังไม่มีข้อมูลย้อนหลังเพียงพอ'}), 400

    prompt = f"""
    ในฐานะนักวิเคราะห์ปัญหามืออาชีพ โปรดอ่านหัวข้อข่าวเชิงลบทั้งหมดนี้ แล้ววินิจฉัยว่า "สาเหตุรากเหง้า" (Root Cause) ที่แท้จริงของวิกฤตครั้งนี้คืออะไร โดยให้จัดหมวดหมู่เป็นหนึ่งในสี่ประเภทนี้เท่านั้น: "คุณภาพสินค้า/บริการ", "การสื่อสารล้มเหลว", "ปัญหาด้านราคา", หรือ "ภาพลักษณ์องค์กร"

    โปรดตอบกลับเป็น JSON Object รูปแบบนี้เท่านั้น: {{"category": "หมวดหมู่", "reason": "เหตุผลประกอบ 1 ประโยค"}}

    หัวข้อข่าวเชิงลบ:
    {"\n".join([f"- {h}" for h in negative_headlines])}
    """
    try:
        safety_settings = {
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
        }
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        analysis_result = json.loads(cleaned_response)
        
        return jsonify(analysis_result)
    except Exception as e:
        print(f"Warning: Gemini root cause analysis failed ({e})")
        return jsonify({'error': 'Failed to analyze root cause'}), 500
# ===== END: เพิ่มฟังก์ชันที่หายไปกลับเข้ามา =====

# ===== START: Route ใหม่สำหรับให้ ESP8266 เรียกใช้ =====
@app.route('/api/crisis_status')
def crisis_status():
    """
    API Endpoint ที่จะคืนค่าสถานะล่าสุด และรีเซ็ตสถานะ alert ที่หมดอายุแล้ว
    """
    ALERT_DURATION_SECONDS = 60 # กำหนดให้ Alert อยู่ได้นาน 1 นาที

    # ตรวจสอบว่าสถานะปัจจุบันคือ 'alert' และหมดเวลาแล้วหรือยัง
    if latest_analysis_status["status"] == "alert":
        current_time = int(time.time())
        alert_time = latest_analysis_status.get("timestamp", 0)

        if (current_time - alert_time) > ALERT_DURATION_SECONDS:
            print("Alert has expired. Resetting status to normal.")
            latest_analysis_status["status"] = "normal" # รีเซ็ตสถานะกลับเป็นปกติ

    return jsonify(latest_analysis_status)


# ===== START: Route ใหม่สำหรับห้องจำลองสถานการณ์ =====
@app.route('/simulate_crisis', methods=['POST'])
def simulate_crisis():
    data = request.json
    headline = data.get('headline')

    if not headline:
        return jsonify({'error': 'Missing headline'}), 400

    prompt = f"""
    ในฐานะ AI จำลองสถานการณ์วิกฤต (Crisis Simulation AI) จากหัวข้อข่าวเชิงลบสมมติต่อไปนี้:
    "{headline}"

    โปรดคาดการณ์และวิเคราะห์ผลกระทบที่จะเกิดขึ้นใน 3 มิติหลัก โดยให้ตอบกลับเป็น JSON Object รูปแบบนี้เท่านั้น:
    {{"key_concerns": ["ประเด็นกังวลหลัก 1", "ประเด็นกังวลหลัก 2"], "viral_score": คะแนน (1-10), "first_action": "สิ่งแรกที่ทีม PR ควรทำภายใน 1 ชั่วโมง"}}
    """
    try:
        safety_settings = {
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
        }
        response = model.generate_content(prompt, safety_settings=safety_settings)

        # ทำความสะอาดและแปลงผลลัพธ์จาก AI ให้เป็น JSON
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        simulation_result = json.loads(cleaned_response)

        return jsonify(simulation_result)
    except Exception as e:
        print(f"Warning: Gemini simulation failed ({e})")
        return jsonify({'error': 'Failed to get simulation from AI'}), 500
# ===== END: Route ใหม่ =====

# ==============================================================================
# ส่วนที่ 5: สั่งให้แอปพลิเคชันทำงาน
# ==============================================================================
if __name__ == '__main__':
    
    # กรณีออนไลน์
    app.run(debug=True, host='0.0.0.0')

    # กรณีออฟไลน์
    # app.run(debug=True)