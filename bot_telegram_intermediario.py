from telethon import TelegramClient, events
import requests
import asyncio
import os
import datetime
from flask import Flask, request, jsonify

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')
webhook_url = os.getenv('WEBHOOK_URL', None)
bot_username = os.getenv('BOT_USERNAME')
session_name = 'session_vcnngr'
LOG_FILE = "/app/logs/bot_interaction.log"
KEYS_FILE = "/app/keys/api_keys.txt"
MASTER_KEY = os.getenv('MASTER_API_KEY')
TIMEOUT_SECONDS = 20

app = Flask(__name__)

def log_message(text):
    timestamp = datetime.datetime.now().isoformat()
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {text}\n")

def rotate_old_logs(log_file, retention_days=30):
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=retention_days)
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        with open(log_file, "w") as f:
            for line in lines:
                if line.startswith("["):
                    try:
                        log_time = datetime.datetime.fromisoformat(line.split("]")[0][1:])
                        if log_time >= cutoff:
                            f.write(line)
                    except:
                        continue
    except FileNotFoundError:
        pass

def load_api_keys():
    if not os.path.exists(KEYS_FILE):
        return set()
    with open(KEYS_FILE, "r") as f:
        return set(line.strip().split(";")[0] for line in f.readlines())

api_keys = load_api_keys()

@app.route("/ask", methods=["POST"])
def ask_bot():
    key = request.headers.get("X-API-KEY")
    if not key or key not in api_keys:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    question = data.get("question")
    if not question:
        return jsonify({"error": "Missing 'question'"}), 400

    answer = asyncio.run(process_question(question))
    return jsonify(answer), 200

@app.route("/healthz", methods=["GET"])
def health_check():
    return "OK", 200

async def process_question(question):
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start(phone_number)
    response_event = asyncio.Event()
    response_data = {"message": None}

    @client.on(events.NewMessage(from_users=bot_username))
    async def handler(event):
        response_data["message"] = event.message.message
        response_event.set()

    log_message(f"Invio: {question}")
    await client.send_message(bot_username, question)

    try:
        await asyncio.wait_for(response_event.wait(), timeout=TIMEOUT_SECONDS)
        log_message(f"Risposta ricevuta: {response_data['message']}")
        return {"question": question, "response": response_data["message"]}
    except asyncio.TimeoutError:
        log_message("Timeout: nessuna risposta.")
        return {"question": question, "response": None, "timeout": True}
    finally:
        await client.disconnect()

if __name__ == "__main__":
    rotate_old_logs(LOG_FILE)
    app.run(host="0.0.0.0", port=8080)
