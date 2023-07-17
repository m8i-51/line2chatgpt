import json
import os
from shutil import ExecError
import time
import uuid
import openai
import boto3
import requests
import logging
from boto3.dynamodb.conditions import Key
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    ImageMessage,
    ImageSendMessage,
)
from pyshorteners import Shortener

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
formatter = logging.Formatter(
    "[%(levelname)s]\t%(asctime)s.%(msecs)dZ\t%(filename)s\tlineno:%(lineno)d\t%(message)s\n",
    "%Y-%m-%dT%H:%M:%S",
)
logger.setLevel(logging.INFO)
for handler in logger.handlers:
    handler.setFormatter(formatter)

# 環境変数から必要な情報を取得
OPENAI_API_KEY = os.environ["OPENAI_SECRETKEY"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
DEEPL_SECRETKEY = os.environ["DEEPL_SECRETKEY"]

openai.api_key = OPENAI_API_KEY
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

DEFAULT_ROLE = {
    "role": "system",
    "content": """あなたは次の回答から以下の設定に基づいたキャラクターなりきってロールプレイし、私と会話して下さい。
    あなたの名前：
    あなたの年齢：
    あなたの誕生日：
    あなたの血液型：
    あなたの住んでいるところ：
    あなたの性別：
    あなたの職業：
    あなたの言葉使い：
    あなたの性格：
    あなたの一人称：
    """,
}


def webhook(event, context):
    logger.info("lambda call")
    signature = event["headers"].get("x-line-signature") or event["headers"].get(
        "X-Line-Signature"
    )
    body = event["body"]

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return {"statusCode": 400, "body": json.dumps({"message": "Invalid signature"})}

    return {"statusCode": 200, "body": json.dumps({"message": "OK"})}


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    send_timestamp = int(time.time() * 1000)
    user_id = event.source.user_id
    user_message = event.message.text
    user_message_obj = {"role": "user", "content": user_message}
    # 履歴の取得
    message_history = get_message_history(user_id)
    # 履歴の順序を変えて最新のメッセージを追加
    messages = [
        {"role": item["message"]["role"], "content": item["message"]["content"]}
        for item in reversed(message_history)
    ]
    messages.append(user_message_obj)
    post_messages = []
    post_messages.append(DEFAULT_ROLE)
    for message in messages:
        post_messages.append(message)
    if event.source.type == "group":
        if (
            "**さん" in user_message
            or "**くん" in user_message
            or "**ちゃん" in user_message
        ):
            pass
        else:
            return
    if "画像生成" in user_message or "画像を生成" in user_message or "画像の生成" in user_message:
        try:
            deeplAuthStr = "DeepL-Auth-Key " + DEEPL_SECRETKEY
            headers = {"Authorization": deeplAuthStr}
            payload = {"text": user_message, "source_lang": "JA", "target_lang": "EN"}
            deeplAPI = "https://api-free.deepl.com/v2/translate"
            response = requests.post(
                deeplAPI, headers=headers, data=payload, timeout=(5.5, 15.0)
            )
            responseText = response.json()
            jaKey = responseText["translations"][0]["text"]
        except Exception as e:
            logger.error(f"Error output Image: {e}")
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="ちょっと英訳苦手で、、、")
            )
            return
        try:
            openai_response = openai.Image.create(
                # promptに、画像を生成するキーワードを入れる。
                prompt=jaKey,
                n=1,
                size="1024x1024",
            )
            # dalleAPIからの結果を取得（辞書型）
            ai_message = openai_response["data"][0]["url"]
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ちょっと調子が悪いみたい、、、"),
            )
            return
        ai_message_obj = {"role": "assistant", "content": ai_message}
        receive_timestamp = int(time.time() * 1000)
        # LINEへの返答
        s = Shortener()
        short_url = s.tinyurl.short(ai_message)
        try:
            line_bot_api.reply_message(
                event.reply_token,
                ImageSendMessage(
                    original_content_url=short_url, preview_image_url=short_url
                ),
            )
        except LineBotApiError as e:
            logger.error(f"Error Linebot API: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="画像生成の調子が悪いみたい、、、"),
            )
            return

    else:
        try:
            openai_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k", messages=post_messages, request_timeout=40
            )
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ちょっと調子が悪いみたい、、、"),
            )
            return
        # レスポンスの取得
        ai_message = openai_response.choices[0].message.content
        ai_message_obj = {"role": "assistant", "content": ai_message}
        receive_timestamp = int(time.time() * 1000)
        # LINEへの返答
        try:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=ai_message)
            )
        except LineBotApiError as e:
            logger.error(f"Error Linebot API: {e}")
            return

    # ユーザー発言の保存
    try:
        save_message_to_history(user_id, user_message_obj, send_timestamp)
    except Exception as e:
        logger.error(f"Error save user message: {e}")
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="あなたの言ってたこと忘れちゃった★")
        )
        return
    # AI発言の保存
    try:
        save_message_to_history(user_id, ai_message_obj, receive_timestamp)
    except Exception as e:
        logger.error(f"Error save AI message: {e}")
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="自分が何言ってたか忘れちゃったw")
        )
    logger.info("lambda end")


def get_message_history(user_id, limit=10):
    response = table.query(
        KeyConditionExpression=Key("user_id").eq(user_id),
        Limit=limit,
        ScanIndexForward=False,
    )
    return response["Items"]


def save_message_to_history(user_id, message, timestamp):
    table.put_item(
        Item={"user_id": user_id, "timestamp": timestamp, "message": message}
    )
