import requests
import json
import google.generativeai as genai
import re
import time

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
    print(f"Engine: Fetching data for keyword: '{keyword}'...")

    try:
        response = requests.get(url)
        data = response.json()

        if data['status'] == 'ok':
            articles_raw = data.get('articles', [])
            articles = [
                {'title': article['title'], 'url': article['url']}
                for article in articles_raw if article.get('title') and article.get('url')
            ]
            print(f"Engine: Fetch successful. Got {len(articles)} articles.")
            return articles
        else:
            print(f"Engine: API Error: {data.get('message')}")
            return []

    except Exception as e:
        print(f"Engine: Connection error: {e}")
        return []

def analyze_sentiment_with_gemini(articles, model):
    """
    ฟังก์ชันวิเคราะห์ความรู้สึกด้วย Gemini API ที่มีการแบ่งข้อมูลเป็นชุดเล็กๆ (Batching)
    """
    print("\nEngine: Sending data to Gemini AI for analysis...")

    if not articles:
        return []
    
    # ===== บรรทัดที่แก้ไข: จำกัดจำนวนข่าวที่จะวิเคราะห์ =====
    # เพื่อป้องกัน Timeout เราจะวิเคราะห์แค่ 20 ข่าวล่าสุดเท่านั้น
    articles_to_analyze = articles[:20]
    print(f"   -> Analyzing the latest {len(articles_to_analyze)} articles to prevent timeout.")
    # ===================================================

    BATCH_SIZE = 20
    all_results_with_sentiment = []
    
    for i in range(0, len(articles_to_analyze), BATCH_SIZE):
        batch = articles_to_analyze[i:i + BATCH_SIZE]
        print(f"...Processing batch {i//BATCH_SIZE + 1}")

        headlines_text = "\n".join([f"{idx+1}. {article['title']}" for idx, article in enumerate(batch)])

        prompt = f"""
        Analyze the sentiment of the following Thai news headlines, considering the context of public relations and brand image.
        Classify each headline as only 'POSITIVE', 'NEGATIVE', or 'NEUTRAL'.

        Please respond ONLY with a valid JSON Array in this format: [{{"id": 1, "sentiment": "SENTIMENT_LABEL"}}, {{"id": 2, "sentiment": "SENTIMENT_LABEL"}}, ...]

        Headlines to analyze:
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
                raise ValueError("No JSON found in AI response")

            time.sleep(1)

        except Exception as e:
            print(f"Engine: Error during batch analysis: {e}")
            for article in batch:
                all_results_with_sentiment.append({'title': article['title'], 'url': article['url'], 'sentiment': 'NEUTRAL'})
    
    # เพิ่มข่าวที่เหลือ (ที่ไม่ได้วิเคราะห์) เข้าไปในผลลัพธ์โดยให้เป็น NEUTRAL
    remaining_articles = articles[20:]
    for article in remaining_articles:
        all_results_with_sentiment.append({'title': article['title'], 'url': article['url'], 'sentiment': 'NEUTRAL'})

    print("Engine: Gemini sentiment analysis finished.")
    return all_results_with_sentiment
