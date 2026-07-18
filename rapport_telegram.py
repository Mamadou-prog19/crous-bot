from dotenv import load_dotenv
import requests
import os
import json
import time


load_dotenv()


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

FICHIER_STATUS = "status.json"


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


def lire_status():

    if os.path.exists(FICHIER_STATUS):

        with open(
            FICHIER_STATUS,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)


    return {
        "statut": "INCONNU",
        "dernier_controle": "Jamais",
        "logements_trouves": 0
    }



status = lire_status()


message = (
    "🤖 Rapport Bot CROUS\n\n"
    f"📌 Statut : {status['statut']}\n\n"
    f"🕒 Dernier contrôle :\n"
    f"{status['dernier_controle']}\n\n"
    f"🏠 Logements détectés : "
    f"{status['logements_trouves']}"
)


envoyer_telegram(message)


print("Rapport envoyé.")