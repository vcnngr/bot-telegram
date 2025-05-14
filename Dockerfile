FROM python:3.11-slim
WORKDIR /app
COPY bot_telegram_intermediario.py .
RUN pip install flask telethon requests
VOLUME ["/app/session", "/app/logs", "/app/keys"]
EXPOSE 8080
CMD ["python", "bot_telegram_intermediario.py"]