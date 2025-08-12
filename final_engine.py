# ==============================================================================
# ส่วนที่ 1: Import ไลบรารีที่จำเป็น
# ==============================================================================
import requests
import pandas as pd
from transformers import pipeline


# ==============================================================================
# ขั้นตอนที่ 2.1: สร้างระบบดึงข้อมูล (Data "Collector" via API)
# ==============================================================================
def get_data_from_api(keyword, api_key):
    """
    ดึงข้อมูลข่าวโดยตรงผ่าน NewsAPI เพื่อความเสถียร
    จะคืนค่าเป็น DataFrame ของ Pandas ที่มี 'title' และ 'timestamp'
    """
    url = f'https://newsapi.org/v2/everything?q={keyword}&language=th&sortBy=publishedAt&apiKey={api_key}'
    print(f"🚀 [Step 2.1] กำลังดึงข้อมูลสำหรับคำว่า: '{keyword}' จาก NewsAPI...")


    try:
        response = requests.get(url)
        data = response.json()


        if data['status'] == 'ok':
            articles = data.get('articles', [])
            if not articles:
                return pd.DataFrame() # คืนค่า DataFrame ว่างถ้าไม่เจอข่าว


            # สร้าง DataFrame ด้วย Pandas
            df = pd.DataFrame(articles)
            df = df[['title', 'publishedAt']] # เลือกเฉพาะคอลัมน์ที่ต้องการ
            df = df.rename(columns={'publishedAt': 'timestamp'}) # เปลี่ยนชื่อคอลัมน์
            print(f"✅ [Step 2.1] ดึงข้อมูลสำเร็จ ได้มา {len(df)} ข่าว")
            return df
        else:
            print(f"🚨 [Step 2.1] Error จาก API: {data.get('message')}")
            return pd.DataFrame()


    except Exception as e:
        print(f"🚨 [Step 2.1] เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
        return pd.DataFrame()


# ==============================================================================
# ขั้นตอนที่ 2.2: สร้างระบบวิเคราะห์ความรู้สึก (Sentiment Analyzer)
# ==============================================================================
def analyze_sentiment_and_update_df(df):
    """
    รับ DataFrame เข้ามา, วิเคราะห์คอลัมน์ 'title',
    แล้วเพิ่มคอลัมน์ 'sentiment' กลับเข้าไปใน DataFrame เดิม
    """
    print("\n🧠 [Step 2.2] กำลังโหลดโมเดล AI เพื่อวิเคราะห์ความรู้สึก...")
    sentiment_analyzer = pipeline(
        "sentiment-analysis",
        model="lxyuan/distilbert-base-multilingual-cased-sentiments-student"
    )
   
    titles = df['title'].tolist()
    print("...เริ่มการวิเคราะห์ความรู้สึก...")
    results = sentiment_analyzer(titles)
   
    # ดึงเฉพาะ 'label' (เช่น 'POSITIVE', 'NEGATIVE') ออกมา
    sentiments = [result['label'].upper() for result in results]
    df['sentiment'] = sentiments
   
    print("✅ [Step 2.2] วิเคราะห์ความรู้สึกสำเร็จ")
    return df


# ==============================================================================
# ขั้นตอนที่ 2.3: สร้างระบบตรวจจับความผิดปกติ (Anomaly Detector)
# ==============================================================================
def detect_anomalies(df):
    """
    รับ DataFrame ที่มีข้อมูลสมบูรณ์แล้วมาตรวจจับความผิดปกติ
    """
    print("\n🕵️  [Step 2.3] กำลังเริ่มตรวจจับความผิดปกติ...")
    if df.empty or 'sentiment' not in df.columns:
        print("...ไม่มีข้อมูลให้วิเคราะห์")
        return


    # แปลงคอลัมน์ timestamp ให้เป็นรูปแบบวันที่และเวลาที่ Python เข้าใจ
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)


    # นับจำนวนข่าว 'NEGATIVE' ในแต่ละชั่วโมง
    negative_counts_per_hour = df[df['sentiment'] == 'NEGATIVE'].resample('h').size()
   
    if len(negative_counts_per_hour) < 2:
        print("...ข้อมูลน้อยเกินไปที่จะคำนวณค่า Baseline")
        return
       
    # คำนวณค่า Baseline
    mean_negatives = negative_counts_per_hour.mean()
    std_dev_negatives = negative_counts_per_hour.std()
   
    # กำหนดเกณฑ์ (Threshold)
    threshold = mean_negatives + (2 * std_dev_negatives)
   
    # ดึงข้อมูลชั่วโมงล่าสุด
    last_hour_count = negative_counts_per_hour.iloc[-1]
   
    print(f"...ค่าเฉลี่ยข่าวเชิงลบต่อชั่วโมง: {mean_negatives:.2f}")
    print(f"...เกณฑ์แจ้งเตือน (Threshold): {threshold:.2f}")
    print(f"...จำนวนข่าวเชิงลบในชั่วโมงล่าสุด: {last_hour_count}")


    # ตรวจสอบว่าเกินเกณฑ์หรือไม่
    if last_hour_count > threshold and last_hour_count > 0:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! 🚨 ALERT: พบภาวะผิดปกติ! จำนวนข่าวเชิงลบพุ่งสูงขึ้น !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        print("\n✅ [Step 2.3] สถานการณ์ปกติ ไม่พบความผิดปกติ")


# ==============================================================================
# ส่วนทำงานหลักของโปรแกรม (Main Program)
# ==============================================================================
if __name__ == "__main__":
    # 1. ใส่ API Key ของคุณที่คัดลอกมา ตรงนี้
    MY_API_KEY = "91bba17953f340ffa7c7989b7c063ece" # <<<< ใส่ KEY ของคุณที่นี่
    target_keyword = "AIS"


    if "YOUR_API_KEY" in MY_API_KEY:
        print("!!! กรุณาใส่ API Key ที่ถูกต้องก่อนรันโปรแกรม !!!")
    else:
        # Step 2.1: ดึงข้อมูล
        data_df = get_data_from_api(target_keyword, MY_API_KEY)


        if not data_df.empty:
            # Step 2.2: วิเคราะห์ความรู้สึก
            data_df = analyze_sentiment_and_update_df(data_df)


            # Step 2.3: ตรวจจับความผิดปกติ
            detect_anomalies(data_df)


            # บันทึกผลลัพธ์ทั้งหมดลงไฟล์ CSV
            try:
                data_df.to_csv("pr_crisis_data.csv", encoding='utf-8-sig')
                print("\n💾 บันทึกข้อมูลทั้งหมดลงไฟล์ 'pr_crisis_data.csv' เรียบร้อยแล้ว")
            except Exception as e:
                print(f"เกิดข้อผิดพลาดในการบันทึกไฟล์ CSV: {e}")

