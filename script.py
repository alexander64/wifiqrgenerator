# =====================================
# Versione: 1.6
# Script: wifi_qr_with_logo.py
# Descrizione: Genera un QR code Wi-Fi compatibile con logo.
#              Può essere standard o artistico puntinato.
#              Logo scelto automaticamente da ./logo/
#              Output in ./output/YYYY-MM-DD_HH-MM-SS/
# =====================================

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import CircleModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask
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


def generate_wifi_qr(ssid: str, password: str, style: str = "standard", output_filename: str = "wifi_qr.png"):
    """
    Genera un QR code per rete Wi-Fi con logo al centro.
    
    Args:
        ssid (str): Nome rete Wi-Fi (SSID)
        password (str): Password Wi-Fi
        style (str): "standard" o "artistico"
        output_filename (str): Nome file finale dentro ./output/
    """

    # --- Percorsi base ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_dir = os.path.join(base_dir, "logo")
    output_root = os.path.join(base_dir, "output")

    # --- Trova logo ---
    logo_path = find_logo(logo_dir)

    # --- Crea cartella datata ---
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

    # --- Selezione stile ---
    if style == "artistico":
        qr_img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=CircleModuleDrawer(),  # moduli circolari (puntinato)
            color_mask=RadialGradiantColorMask(
                back_color=(255, 255, 255),
                center_color=(10, 10, 10),
                edge_color=(60, 60, 60),
            ),
        ).convert("RGB")
    else:
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
    print(f"✅ QR Wi-Fi '{style}' generato con successo: {output_path}")


if __name__ == "__main__":
    print("=== Generatore QR Wi-Fi con logo (v1.6) ===")
    ssid = input("Inserisci SSID Wi-Fi: ")
    password = input("Inserisci password Wi-Fi: ")
    print("\nScegli tipo QR:")
    print("1 - Standard (massima compatibilità)")
    print("2 - Artistico (puntinato, tipo Snapchat)")
    choice = input("Scelta [1/2]: ").strip()

    style = "artistico" if choice == "2" else "standard"

    try:
        generate_wifi_qr(ssid, password, style)
    except Exception as e:
        print(str(e))
        sys.exit(1)
