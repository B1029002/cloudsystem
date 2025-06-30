import os
import json
import requests
from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
)
from linebot.models import ImageMessage
from PIL import Image
import pytesseract
from io import BytesIO

load_dotenv()

app = Flask(__name__)

# LINE & myai168 設定
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
MYAI168_DEV_KEY = os.getenv('MYAI168_DEV_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 使用者 session 記憶區
user_sessions = {}  # user_id → {mode, session_sn, state, last_text}

# 圖文選單：模式選擇 Flex Message
def send_mode_selector(user_id, reply_token):
    flex_contents = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{"type": "text", "text": "請選擇模式", "weight": "bold", "size": "lg"}]
        },
        "body": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "action": {"type": "message", "label": "翻譯", "text": "/mode translate"},
                    "margin": "md"
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {"type": "message", "label": "查詢", "text": "/mode query"},
                    "margin": "md"
                }
            ]
        }
    }
    flex_message = FlexSendMessage(alt_text="請選擇模式", contents=flex_contents)
    line_bot_api.reply_message(reply_token, flex_message)

# 主處理函式：翻譯或查詢
def process_user_input(user_id, user_input):
    mode = user_sessions[user_id].get("mode", "translate")
    url = "https://www.myai168.com/cgu/aieasypay/module/ai-168/chat"

    # 查詢模式
    if mode == "query":
        prompt = f"你是一位知識助手，請簡短清楚地回答下列問題：\n{user_input}"
        session_sn = "0"
        user_sessions[user_id].update({
            "session_sn": session_sn,
            "state": "waiting_text",
            "last_text": ""
        })

    # 翻譯模式（多輪對話）
    else:
        session = user_sessions[user_id]
        session_sn = session.get("session_sn", "0")
        state = session.get("state", "waiting_text")
        last_text = session.get("last_text", "")

        if state == "waiting_text":
            prompt = (
                "你是一位語言學專家，請不要翻譯，"
                "請你只回覆：「你希望我將這句話翻譯成哪一種語言？」"
                f"\n\n使用者的句子：{user_input}"
            )
            session["last_text"] = user_input
            session["state"] = "waiting_lang"

        elif state == "waiting_lang":
            target_lang = user_input.strip()

            # 要求輸入內容需包含「文」或「語」字樣，才判定為語言
            if "文" not in target_lang and "語" not in target_lang:
                return "請輸入有效語言名稱，例如：英文、日文、法語等。請再試一次。"

            source_text = last_text
            prompt = (
                f"你是一位語言專家，請將下列每一個詞彙**強制**翻譯成「{target_lang}」，"
                f"即使是品牌、地名或人名，也請盡可能翻譯出對應的意思或音譯，不得保留原文或跳過。"
                f"\n\n使用者句子：{source_text}"
            )
            session["state"] = "waiting_text"
            session["last_text"] = ""
            user_sessions[user_id] = session



    # 呼叫 myai168 API
    form_data = {
        "module": (None, "ai-172"),
        "dev_key": (None, MYAI168_DEV_KEY),
        "input": (None, prompt),
        "search_internet": (None, "false"),
        "search_url": (None, "www.myai168.com"),
        "session_sn": (None, session_sn)
    }

    try:
        response = requests.post(url, files=form_data)
        response.raise_for_status()

        # 擷取 session_sn
        for line in response.text.splitlines():
            if "session_sn" in line:
                try:
                    session_obj = json.loads(line.replace("data:", "").strip())
                    new_sn = session_obj.get("session_sn")
                    if new_sn:
                        user_sessions[user_id]["session_sn"] = str(new_sn)
                except:
                    pass

        # 整理回覆
        full_reply = ""
        for line in response.text.splitlines():
            if line.startswith("data:"):
                content = line[5:].strip()
                if content == "[DONE]":
                    break
                try:
                    chunk = json.loads(content)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    new_content = delta.get("content", "")
                    if new_content and "思考中" not in new_content:
                        full_reply += new_content
                except:
                    continue

        return full_reply.strip() if full_reply else "無法取得回應內容"

    except Exception as e:
        return f"發生錯誤：{str(e)}"

# LINE Webhook 接收入口
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理使用者文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_text = event.message.text.strip()

    # 模式設定指令處理
    if user_text.startswith("/mode"):
        selected = user_text.replace("/mode", "").strip()
        if selected in ["translate", "query"]:
            user_sessions[user_id] = {
                "mode": selected,
                "session_sn": "0",
                "state": "waiting_text",
                "last_text": ""
            }
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"已切換至「{selected}」模式，請輸入內容開始。")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="模式無效，請重新選擇。")
            )
        return

    # 使用者說「切換模式」→ 顯示 Flex 選單
    if user_text in ["切換模式", "我要選單", "選單", "更換模式"]:
        send_mode_selector(user_id, event.reply_token)
        return

    # 尚未選擇模式 → 顯示選單
    if user_id not in user_sessions or "mode" not in user_sessions[user_id]:
        send_mode_selector(user_id, event.reply_token)
        return

    # 處理翻譯或查詢
    response = process_user_input(user_id, user_text)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response)
    )

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id

    # 取得圖片內容
    message_content = line_bot_api.get_message_content(event.message.id)
    image_bytes = BytesIO(message_content.content)

    # 使用 PIL 開啟圖片並進行 OCR
    try:
        image = Image.open(image_bytes)
        extracted_text = pytesseract.image_to_string(image, lang='eng+chi_tra')  # 同時支援中英文

        if not extracted_text.strip():
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="圖片中未偵測到文字，請重新拍照再試一次。")
            )
            return

        user_sessions[user_id] = {
            "mode": "translate",
            "session_sn": "0",
            "state": "waiting_lang",
            "last_text": extracted_text
        }

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="圖片文字擷取成功，請問您希望翻譯成哪一種語言？")
        )

    except Exception as e:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"發生錯誤：{str(e)}")
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
