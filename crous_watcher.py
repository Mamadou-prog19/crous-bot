from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from dotenv import load_dotenv
import requests
import json
import os
import time


# =========================
# CONFIGURATION
# =========================

load_dotenv()

VILLE = "Orléans"

URL_RECHERCHE = "https://trouverunlogement.lescrous.fr/"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

FICHIER_VUS = "logements_vus.json"


# =========================
# TELEGRAM
# =========================

def envoyer_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=15
        )

    except Exception as e:
        print("Erreur Telegram :", e)


# =========================
# CHARGEMENT LOGEMENTS VUS
# =========================

if os.path.exists(FICHIER_VUS):

    with open(FICHIER_VUS, "r", encoding="utf-8") as f:
        logements_vus = set(json.load(f))

else:

    logements_vus = set()



def sauvegarder_logements():

    with open(FICHIER_VUS, "w", encoding="utf-8") as f:

        json.dump(
            list(logements_vus),
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================
# NAVIGATEUR
# =========================

def creer_driver():

    options = Options()

    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(
        options=options
    )

    return driver



# =========================
# VERIFICATION CROUS
# =========================

def verifier_logements():

    driver = creer_driver()

    wait = WebDriverWait(driver, 30)


    print("🤖 Vérification CROUS lancée...")


    try:

        driver.get(URL_RECHERCHE)


        ville = wait.until(

            EC.presence_of_element_located(
                (
                    By.ID,
                    "PlaceAutocompletearia-autocomplete-1-input"
                )
            )

        )


        ville.clear()

        ville.send_keys(VILLE)



        suggestion = wait.until(

            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//li[@role='option'][contains(.,'Orléans')]"
                )
            )

        )


        suggestion.click()



        bouton = wait.until(

            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(.,'Lancer une recherche')]"
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

            return



        print("Logements détectés !")



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

                sauvegarder_logements()



                envoyer_telegram(

                    "🚨 NOUVEAU LOGEMENT CROUS ORLÉANS\n\n"
                    + lien

                )


                nouveaux += 1



        if nouveaux == 0:

            print("Pas de nouveau logement.")

        else:

            print(
                nouveaux,
                "nouveau(x) logement(s) détecté(s)."
            )



    except Exception as e:


        print(
            "Erreur :",
            e
        )


        envoyer_telegram(

            "❌ ERREUR BOT CROUS\n\n"
            + str(e)

        )



    finally:


        try:

            driver.quit()

        except:

            pass




# =========================
# LANCEMENT
# =========================

if __name__ == "__main__":

    verifier_logements()