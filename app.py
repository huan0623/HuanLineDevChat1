#=====python library=====
import tempfile, os
import datetime
import time
import traceback
import openai
from gtts import gTTS

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
#=====python library=====

# api key: CHANNEL_ACCESS_TOKEN/ CHANNEL_SECRET/ OPENAI_API_KEY
app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key Init Setting
openai.api_key = os.getenv('OPENAI_API_KEY')

# 接收: open ai 回應訊息的物件
def GPT_response(text):
    # 創建回應List
    messages = [
        {"role": "system", "content": "This is an ai chat bot assistant."},
        {"role": "user", "content": text}
    ]
    # 接收回應
    response = openai.ChatCompletion.create(model="gpt-4o-mini", messages=messages, temperature=0.5, max_tokens=1000)
    print(response)
    # 重組回應
    answer = response['choices'][0]['message']['content'].replace('。','')
    return answer
# 將文本轉換為語音並返回文件路徑
def text_to_speech(text):
    tts = gTTS(text=text, lang='zh')
    audio_file_path = os.path.join(static_tmp_path, 'response.mp3')
    tts.save(audio_file_path)
    return audio_file_path

# 監聽: 所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# 通知: 回應的資訊處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        if msg.startswith("語音回覆:"):
            # after get prompt include 語音
            text_to_convert = msg[len("語音回覆:"):].strip()
            GPT_answer = GPT_response(text_to_convert)
            audio_file_path = text_to_speech(GPT_answer)
            with open(audio_file_path, 'rb') as audio_file:
                line_bot_api.reply_message(event.reply_token, AudioSendMessage(audio_file))
        else:
            GPT_answer = GPT_response(msg)
            print(GPT_answer)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
    except:
        print(traceback.format_exc())
        line_bot_api.reply_message(event.reply_token, TextSendMessage('你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息'))
        

# 通知: POST
@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


# 通知: 回應加入時的歡迎訊息
@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
        
        
# app default Entrance
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)