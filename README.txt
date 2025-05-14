=== TELEGRAM BOT INTERMEDIARIO (DOCKER + TELETHON) ===

1. REGISTRA un'app su https://my.telegram.org
   - Ottieni api_id e api_hash

2. COSTRUISCI IL CONTAINER:
   docker build -t telegram-bot-intermediario .

3. ESEGUI IL CONTAINER con variabili personalizzate:
   docker run -it --rm \
     -e API_ID=123456 \
     -e API_HASH=abc123yourhash \
     -e PHONE_NUMBER=+39XXXXXXXXXX \
     -v $(pwd)/session:/app/session \
     telegram-bot-intermediario

NOTE:
- La prima volta ti verrà chiesto un codice Telegram
- I dati di sessione sono salvati nella cartella "session"

