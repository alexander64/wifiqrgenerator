# =====================================
# Versione: 1.4
# Script: wifi_qr_with_logo.py
# Descrizione: Genera un QR code Wi-Fi compatibile con logo centrale.
#              Il logo (.png o .ico) viene scelto automaticamente da ./logo/
#              Ogni QR viene salvato in ./output/YYYY-MM-DD_HH-MM-SS/
# =====================================

import qrcode
from PIL import Image
import os
import sys
from datetime import datetime


def find_logo(logo_dir: str) -> str:
    """Cerca automaticamente un logo .png o .ico nella cartella specificata."""
    if not os.path.exists(logo_dir):
        raise FileNotFoundError(f"❌ Cartella logo non trovata: {logo_dir}")

    valid_ext = (".png", ".ico")
    logos = [f for f in os.listdir(logo_dir) if f.lower().endswith(valid_ext)]

    if len(logos) == 0:
        raise FileNotFoundError(f"❌ Nessun logo (.png o .ico) trovato in {logo_dir}")
    if len(logos) > 1:
        raise ValueError(f"❌ Più di un logo trovato in {logo_dir}. Lascia solo un file (.png o .ico)")

    return os.path.join(logo_dir, logos[0])


def generate_wifi_qr(ssid: str, password: str, output_filename: str = "wifi_qr.png"):
    """
    Genera un QR code per rete Wi-Fi con logo al centro e lo salva in una cartella datata.
    
    Args:
        ssid (str): Nome rete Wi-Fi (SSID)
        password (str): Password Wi-Fi
        output_filename (str): Nome file QR finale
    """

    # --- Percorsi base ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_dir = os.path.join(base_dir, "logo")
    output_root = os.path.join(base_dir, "output")

    # --- Trova logo ---
    logo_path = find_logo(logo_dir)

    # --- Crea cartella datata (solo data e ora) ---
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(output_root, date_str)
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, output_filename)

    # --- Formato QR Wi-Fi ---
    wifi_data = f"WIFI:T:WPA;S:{ssid};P:{password};;"

    # --- Generazione QR ---
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(wifi_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # --- Aggiunta logo ---
    logo = Image.open(logo_path)
    qr_width, qr_height = qr_img.size
    logo_size = int(qr_width * 0.2)
    logo.thumbnail((logo_size, logo_size))

    x = (qr_width - logo.size[0]) // 2
    y = (qr_height - logo.size[1]) // 2
    qr_img.paste(logo, (x, y), mask=logo if logo.mode == "RGBA" else None)

    # --- Salva QR finale ---
    qr_img.save(output_path)
    print(f"✅ QR code Wi-Fi generato con successo: {output_path}")


if __name__ == "__main__":
    print("=== Generatore QR Wi-Fi con logo (v1.4) ===")
    ssid = input("Inserisci SSID Wi-Fi: ")
    password = input("Inserisci password Wi-Fi: ")

    try:
        generate_wifi_qr(ssid, password)
    except Exception as e:
        print(str(e))
        sys.exit(1)
