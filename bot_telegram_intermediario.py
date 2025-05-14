from telethon import TelegramClient, events
import requests, asyncio, os, datetime, secrets
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string

# Config
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')
webhook_url = os.getenv('WEBHOOK_URL')
bot_username = os.getenv('BOT_USERNAME')
master_key = os.getenv('MASTER_API_KEY')
session_name = 'session_bot_saved'

LOG_FILE = "/app/logs/bot_interaction.log"
AUDIT_LOG = "/app/logs/audit.log"
KEYS_FILE = "/app/keys/api_keys.txt"

app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET", "change-this")

# Logging
def log_message(text):
    timestamp = datetime.datetime.now().isoformat()
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {text}\n")

def audit_log(entry):
    timestamp = datetime.datetime.now().isoformat()
    with open(AUDIT_LOG, "a") as f:
        f.write(f"[{timestamp}] {entry}\n")

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

rotate_old_logs(LOG_FILE)
rotate_old_logs(AUDIT_LOG)

# Key management
def load_api_keys_dict():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, "r") as f:
        return dict(line.strip().split(";", 1) for line in f if ";" in line)

def save_api_keys_dict(keys):
    with open(KEYS_FILE, "w") as f:
        for k, v in keys.items():
            f.write(f"{k};{v}\n")

# HTML template semplificato
dashboard_html = '''
<!DOCTYPE html><html><body>
<h2>API Key Manager</h2>
<a href="/logout">Logout</a>
<form method="post" action="/generate"><input name="note" required><button>Genera</button></form>
<table border=1>
{% for k, v in keys.items() %}
<tr><td>{{k}}</td><td>
<form action="/edit" method="post">
<input type="hidden" name="key" value="{{k}}">
<input name="note" value="{{v}}" required>
<button>Modifica</button></form>
</td><td>
<form method="post" action="/revoke">
<input type="hidden" name="key" value="{{k}}">
<button>Revoca</button></form></td></tr>
{% endfor %}
</table></body></html>
'''

login_html = '''
<form method="post">
<input type="password" name="password" placeholder="Master Key">
<button>Login</button></form>
'''

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST" and request.form.get("password") == master_key:
        session["auth"] = True
        audit_log("Login effettuato")
        return redirect("/dashboard")
    return render_template_string(login_html)

@app.route("/dashboard")
def dashboard():
    if not session.get("auth"): return redirect("/login")
    return render_template_string(dashboard_html, keys=load_api_keys_dict())

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("auth"): return redirect("/login")
    keys = load_api_keys_dict()
    key = secrets.token_hex(32)
    keys[key] = request.form["note"]
    save_api_keys_dict(keys)
    audit_log(f"Chiave generata: {key}")
    return redirect("/dashboard")

@app.route("/edit", methods=["POST"])
def edit():
    if not session.get("auth"): return redirect("/login")
    keys = load_api_keys_dict()
    keys[request.form["key"]] = request.form["note"]
    save_api_keys_dict(keys)
    audit_log(f"Modifica nota chiave: {request.form['key']}")
    return redirect("/dashboard")

@app.route("/revoke", methods=["POST"])
def revoke():
    if not session.get("auth"): return redirect("/login")
    keys = load_api_keys_dict()
    key = request.form["key"]
    if key in keys:
        audit_log(f"Chiave revocata: {key}")
        del keys[key]
    save_api_keys_dict(keys)
    return redirect("/dashboard")

@app.route("/ask", methods=["POST"])
def ask():
    header_key = request.headers.get("X-API-KEY")
    keys = load_api_keys_dict()
    if not header_key or header_key not in keys:
        return jsonify({"error": "Unauthorized"}), 401
    question = request.json.get("question")
    asyncio.run(send_and_receive(question))
    return jsonify({"status": "sent"})

async def send_and_receive(question):
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start(phone_number)
    result = {"message": None}
    ev = asyncio.Event()

    @client.on(events.NewMessage(from_users=bot_username))
    async def handler(event):
        result["message"] = event.raw_text
        ev.set()

    await client.send_message(bot_username, question)
    try:
        await asyncio.wait_for(ev.wait(), timeout=20)
        requests.post(webhook_url, json={"question": question, "response": result["message"]})
    except:
        requests.post(webhook_url, json={"question": question, "response": None, "timeout": True})
    await client.disconnect()

if __name__ == "__main__":
    os.makedirs("/app/logs", exist_ok=True)
    os.makedirs("/app/keys", exist_ok=True)
    app.run(host="0.0.0.0", port=8080)
