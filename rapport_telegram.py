from dotenv import load_dotenv
import requests
import os
import time


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def envoyer_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=15
    )


heure = time.strftime("%d/%m/%Y à %H:%M:%S")


message = (
    "🤖 Rapport Bot CROUS\n\n"
    "✅ Le service fonctionne correctement.\n"
    f"🕒 {heure}"
)


envoyer_telegram(message)

print("Rapport envoyé.")