import requests
import json
import google.generativeai as genai
import re
import time # <-- เพิ่ม Import สำหรับการหน่วงเวลา


def get_news_from_api(keyword, api_key):
    """
    ฟังก์ชันนี้จะดึงข้อมูลข่าวโดยตรงผ่าน NewsAPI
    และคืนค่าเป็น list ของ dictionary ที่มีทั้ง 'title' และ 'url'
    """
    url = (
        'https://newsapi.org/v2/everything?'
        f'q={keyword}&'
        'language=th&'
        'sortBy=publishedAt&'
        f'apiKey={api_key}'
    )
    print(f"🚀 [Engine] กำลังดึงข้อมูลสำหรับคำว่า: '{keyword}'...")


    try:
        response = requests.get(url)
        data = response.json()


        if data['status'] == 'ok':
            articles_raw = data.get('articles', [])
            articles = [
                {'title': article['title'], 'url': article['url']}
                for article in articles_raw if article.get('title') and article.get('url')
            ]
            print(f"✅ [Engine] ดึงข้อมูลสำเร็จ ได้มา {len(articles)} ข่าว")
            return articles
        else:
            print(f"🚨 [Engine] Error จาก API: {data.get('message')}")
            return []


    except Exception as e:
        print(f"🚨 [Engine] เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
        return []


def analyze_sentiment_with_gemini(articles, model):
    """
    ฟังก์ชันวิเคราะห์ความรู้สึกด้วย Gemini API ที่มีการแบ่งข้อมูลเป็นชุดเล็กๆ (Batching)
    """
    print("\n🧠 [Engine] กำลังส่งข้อมูลให้ Gemini AI วิเคราะห์แบบแบ่งชุด...")


    if not articles:
        return []


    BATCH_SIZE = 20 # แบ่งส่งทีละ 20 ข่าว
    all_results_with_sentiment = []
   
    # วนลูปเพื่อส่งข้อมูลทีละชุด
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i:i + BATCH_SIZE]
        print(f"...กำลังประมวลผลชุดที่ {i//BATCH_SIZE + 1}")


        headlines_text = "\n".join([f"{idx+1}. {article['title']}" for idx, article in enumerate(batch)])


        prompt = f"""
        วิเคราะห์ความรู้สึก (Sentiment) ของหัวข้อข่าวภาษาไทยต่อไปนี้ โดยพิจารณาบริบทของการประชาสัมพันธ์และภาพลักษณ์ของแบรนด์
        จำแนกแต่ละหัวข้อว่าเป็น 'POSITIVE', 'NEGATIVE', หรือ 'NEUTRAL' เท่านั้น


        โปรดตอบกลับเป็น JSON Array รูปแบบนี้เท่านั้น: [{{"id": 1, "sentiment": "SENTIMENT_LABEL"}}, {{"id": 2, "sentiment": "SENTIMENT_LABEL"}}, ...]


        หัวข้อข่าวที่ต้องวิเคราะห์:
        {headlines_text}
        """


        try:
            safety_settings = {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            }
            response = model.generate_content(prompt, safety_settings=safety_settings)
           
            match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if match:
                json_string = match.group(0)
                analysis_results_batch = json.loads(json_string)
               
                sentiment_map = {item['id']: item['sentiment'] for item in analysis_results_batch}


                for idx, article in enumerate(batch):
                    sentiment = sentiment_map.get(idx + 1, "NEUTRAL")
                    all_results_with_sentiment.append({
                        'title': article['title'],
                        'url': article['url'],
                        'sentiment': sentiment.upper()
                    })
            else:
                raise ValueError("ไม่พบ JSON ในการตอบกลับของ AI")


            # หน่วงเวลา 1 วินาที ก่อนส่งชุดต่อไป เพื่อป้องกันการใช้งานถี่เกินไป
            time.sleep(1)


        except Exception as e:
            print(f"🚨 [Engine] เกิดข้อผิดพลาดในการวิเคราะห์ชุดข้อมูล: {e}")
            # ถ้าชุดข้อมูลนี้ล้มเหลว ให้แปะป้าย NEUTRAL ให้กับข่าวในชุดนี้
            for article in batch:
                all_results_with_sentiment.append({'title': article['title'], 'url': article['url'], 'sentiment': 'NEUTRAL'})
   
    print("✅ [Engine] Gemini วิเคราะห์ความรู้สึกทั้งหมดสำเร็จ")
    return all_results_with_sentiment



