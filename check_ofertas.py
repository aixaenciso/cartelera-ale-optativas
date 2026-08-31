"""
Revisa la Cartelera Virtual de ALE/Optativas de Económicas UNICEN
y avisa por mail cuando aparece una oferta nueva.
"""

import json
import os
import smtplib
import sys
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

URL = "https://www.econ.unicen.edu.ar/alumnos/ale/ofertas-ale-y-optativas"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_ofertas.json")


def fetch_ofertas():
    """Descarga la página y extrae las ofertas publicadas."""
    resp = requests.get(
        URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ChequeoOfertasALE/1.0)"},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    ofertas = []
    # Busca encabezados h2, h3 o h4 en la página
    for tag in soup.find_all(["h2", "h3", "h4"]):
        text = tag.get_text(strip=True)
        # Filtramos textos muy cortos o títulos del menú/pie de página
        if text and len(text) > 10 and "Navegación" not in text and "Buscador" not in text:
            ofertas.append({"id": text, "title": text})

    return ofertas


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(ids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, ensure_ascii=False, indent=2)


def send_email(new_ofertas):
    user = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    to = os.environ["EMAIL_TO"]

    lines = [
        "Se publicaron nuevas ofertas en la Cartelera Virtual (ALE / Optativas) de Económicas UNICEN:",
        "",
    ]
    for o in new_ofertas:
        lines.append(f"- {o['title']}")
    lines.append("")
    lines.append(f"Anotate rápido, los cupos son limitados: {URL}")
    body = "\n".join(lines)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"🔔 {len(new_ofertas)} nueva(s) oferta(s) ALE/Optativa en la cartelera"
    msg["From"] = user
    msg["To"] = to

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [to], msg.as_string())


def main():
    seen = load_seen()
    ofertas = fetch_ofertas()

    if not ofertas:
        print("ADVERTENCIA: no se detectó ninguna oferta en la página.")
        sys.exit(0)

    current_ids = {o["id"] for o in ofertas}

    if not seen:
        save_seen(current_ids)
        print(f"Primera ejecución: se guardaron {len(current_ids)} ofertas como línea base.")
        return

    nuevas = [o for o in ofertas if o["id"] not in seen]

    if nuevas:
        print(f"Se encontraron {len(nuevas)} oferta(s) nueva(s): {[o['id'] for o in nuevas]}")
        send_email(nuevas)
        save_seen(seen | current_ids)
    else:
        print("Sin novedades.")
        save_seen(current_ids)


if __name__ == "__main__":
    main()
