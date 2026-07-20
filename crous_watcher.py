"""Surveille les logements CROUS pour plusieurs lieux et alerte via Telegram.

Les secrets TELEGRAM_TOKEN et CHAT_ID doivent être définis dans .env en local
ou dans les secrets GitHub Actions.
"""

from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


load_dotenv()

URL_RECHERCHE = "https://trouverunlogement.lescrous.fr/"

# `saisie` est ce qui est tapé dans le champ. `suggestion` identifie le choix
# à cliquer dans la liste, sans construire un XPath fragile avec une apostrophe.
RECHERCHES = [
    {"nom": "Orléans", "saisie": "Orléans", "suggestion": "Orléans"},
    {
        "nom": "Polytech Orléans",
        "saisie": "Polytech Orléans",
        "suggestion": "Polytech Orléans",
    },
    {
        "nom": "Université d'Orléans - Campus de la Source",
        "saisie": "Université d'Orléans - Campus de la Source",
        "suggestion": "Université d'Orléans - Campus de la Source",
    },
    {"nom": "Angers", "saisie": "Angers", "suggestion": "Angers"},
]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_DIR = Path(__file__).resolve().parent
FICHIER_VUS = BASE_DIR / "logements_vus.json"
FICHIER_STATUS = BASE_DIR / "status.json"


def envoyer_telegram(message: str) -> None:
    """Envoie une alerte Telegram sans empêcher le contrôle de se terminer."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Configuration Telegram manquante : TELEGRAM_TOKEN ou CHAT_ID.")
        return

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message},
            timeout=20,
        )
        if not response.ok:
            print("Erreur Telegram :", response.text)
    except requests.RequestException as error:
        print("Erreur Telegram :", error)


def charger_logements_vus() -> set[str]:
    if not FICHIER_VUS.exists():
        return set()

    try:
        with FICHIER_VUS.open("r", encoding="utf-8") as fichier:
            contenu = json.load(fichier)
        return set(contenu) if isinstance(contenu, list) else set()
    except (OSError, json.JSONDecodeError) as error:
        print("Impossible de lire logements_vus.json :", error)
        return set()


def sauvegarder_logements_vus(logements_vus: set[str]) -> None:
    with FICHIER_VUS.open("w", encoding="utf-8") as fichier:
        json.dump(sorted(logements_vus), fichier, ensure_ascii=False, indent=2)


def mettre_a_jour_status(
    logements_trouves: int,
    statut: str = "OK",
    recherches_effectuees: list[str] | None = None,
) -> None:
    status = {
        "dernier_controle": time.strftime("%d/%m/%Y %H:%M:%S"),
        "logements_trouves": logements_trouves,
        "statut": statut,
        "recherches_effectuees": recherches_effectuees or [],
    }
    with FICHIER_STATUS.open("w", encoding="utf-8") as fichier:
        json.dump(status, fichier, ensure_ascii=False, indent=2)


def creer_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1200")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


def choisir_suggestion(driver: webdriver.Chrome, wait: WebDriverWait, texte: str) -> None:
    """Clique la suggestion correspondant au lieu, sans XPath interpolé fragile."""
    options = wait.until(
        EC.presence_of_all_elements_located((By.XPATH, "//li[@role='option']"))
    )

    texte_normalise = " ".join(texte.casefold().split())
    for option in options:
        option_texte = " ".join(option.text.casefold().split())
        if option_texte == texte_normalise or option_texte.startswith(texte_normalise + ","):
            driver.execute_script("arguments[0].click();", option)
            return

    propositions = ", ".join(option.text for option in options if option.text)
    raise RuntimeError(f"Suggestion introuvable pour « {texte} ». Propositions : {propositions}")


def rechercher_logements(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    recherche: dict[str, str],
) -> list[str]:
    nom = recherche["nom"]
    print(f"Recherche : {nom}")

    driver.get(URL_RECHERCHE)
    ville = wait.until(
        EC.presence_of_element_located((By.ID, "PlaceAutocompletearia-autocomplete-1-input"))
    )
    ville.clear()
    ville.send_keys(recherche["saisie"])
    choisir_suggestion(driver, wait, recherche["suggestion"])

    bouton = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Lancer une recherche')]")
        )
    )
    bouton.click()

    time.sleep(5)
    page = driver.page_source
    if "Aucun logement trouvé" in page or "0 logement trouvé" in page:
        print(f"Aucun logement pour : {nom}")
        return []

    liens = []
    for annonce in driver.find_elements(By.XPATH, "//a[@href]"):
        lien = annonce.get_attribute("href")
        if lien and "/tools/" in lien:
            liens.append(lien)

    return list(dict.fromkeys(liens))


def verifier_logements() -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_TOKEN ou CHAT_ID manquant dans .env / GitHub Secrets.")

    driver = None
    recherches_effectuees: list[str] = []
    nouveaux = 0

    print("Verification CROUS lancee...")
    try:
        driver = creer_driver()
        wait = WebDriverWait(driver, 30)
        logements_vus = charger_logements_vus()

        for recherche in RECHERCHES:
            recherches_effectuees.append(recherche["nom"])
            liens = rechercher_logements(driver, wait, recherche)

            for lien in liens:
                if lien in logements_vus:
                    continue

                logements_vus.add(lien)
                sauvegarder_logements_vus(logements_vus)
                envoyer_telegram(
                    "NOUVEAU LOGEMENT CROUS\n\n"
                    f"Lieu : {recherche['nom']}\n\n"
                    f"Lien :\n{lien}"
                )
                nouveaux += 1

        if nouveaux == 0:
            print("Pas de nouveau logement.")
        else:
            print(f"{nouveaux} nouveau(x) logement(s) detecte(s).")

        mettre_a_jour_status(nouveaux, "OK", recherches_effectuees)

    except Exception:
        details = traceback.format_exc()
        print(details)
        mettre_a_jour_status(0, "ERREUR", recherches_effectuees)

        # Telegram accepte au plus 4096 caractères ; on conserve le début utile.
        envoyer_telegram("ERREUR BOT CROUS\n\n" + details[:3500])

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    verifier_logements()
