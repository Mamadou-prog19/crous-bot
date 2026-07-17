from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import requests
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

# =========================
# PARAMÈTRES
# =========================

VILLE = "Orléans"
URL_RECHERCHE = "https://trouverunlogement.lescrous.fr/"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

FICHIER_VUS = "logements_vus.json"

# =========================
# Chargement des logements déjà vus
# =========================

if os.path.exists(FICHIER_VUS):
    with open(FICHIER_VUS, "r", encoding="utf-8") as f:
        logements_vus = set(json.load(f))
else:
    logements_vus = set()

# =========================
# TELEGRAM
# =========================

def envoyer_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=15,
    )

def envoyer_photo(path):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"

    with open(path, "rb") as photo:

        requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID
            },
            files={
                "photo": photo
            },
            timeout=30,
        )

# =========================
# Selenium
# =========================

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

driver.set_page_load_timeout(60)

wait = WebDriverWait(driver, 30)

print("Robot lancé...")

while True:

    try:

        driver.get(URL_RECHERCHE)

        # site saturé
        if "TROP NOMBREUX" in driver.page_source.upper():

            print("Site saturé... nouvel essai dans 2 minutes.")

            time.sleep(120)

            continue

        ville = wait.until(
            EC.presence_of_element_located(
                (
                    By.ID,
                    "PlaceAutocompletearia-autocomplete-1-input",
                )
            )
        )

        ville.clear()

        ville.send_keys(VILLE)

        suggestion = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//li[@role='option'][contains(.,'Orléans')]",
                )
            )
        )

        suggestion.click()

        bouton = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(.,'Lancer une recherche')]",
                )
            )
        )

        bouton.click()

        time.sleep(5)

        page = driver.page_source

        if (
            "Aucun logement trouvé" in page
            or
            "0 logement trouvé" in page
        ):

            print("Aucun logement.")

            time.sleep(120)

            driver.refresh()

            continue
        print("Des logements sont présents !")

        annonces = driver.find_elements(
            By.XPATH,
            "//a[@href]"
        )

        nouveaux = 0

        for annonce in annonces:

            lien = annonce.get_attribute("href")

            if (
                lien
                and
                "/tools/45/" in lien
                and
                lien not in logements_vus
            ):

                logements_vus.add(lien)

                with open(
                    FICHIER_VUS,
                    "w",
                    encoding="utf-8",
                ) as f:

                    json.dump(
                        list(logements_vus),
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

                driver.save_screenshot("nouveau_logement.png")

                message = (
                    "🚨 NOUVEAU LOGEMENT CROUS À ORLÉANS\n\n"
                    f"{lien}"
                )

                envoyer_telegram(message)
                envoyer_photo("nouveau_logement.png")
                bip()
                popup()

                nouveaux += 1

        if nouveaux == 0:
            print("Pas de nouveau logement.")
        else:
            print(f"{nouveaux} nouveau(x) logement(s) détecté(s).")

        time.sleep(30)

    except Exception as e:

        print("Erreur :", e)

        try:
            driver.quit()
        except:
            pass

        time.sleep(30)

        driver = webdriver.Edge(service=service)
        driver.set_page_load_timeout(60)
        wait = WebDriverWait(driver, 30)