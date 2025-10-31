# =====================================
# Versione: 2.3
# Script: wifi_qr_with_logo.py
# Descrizione:
#   - Genera QR Wi-Fi (standard o puntinato) con logo (SENZA ombra).
#   - Opzionalmente compila il PDF statico: sostituisce SOLO SSID, password e QR.
#   - Cerca i valori esistenti nel template PDF per sovrascriverli nelle posizioni corrette.
#   - SSID e password CENTRATI nella colonna destra della tabella.
#   - QR più grande (145x145 punti).
#   Struttura:
#       static/
#           logo/logo.png (o .ico)   ← un solo file
#           template.pdf              ← il PDF da compilare
#       output/YYYY-MM-DD_HH-MM-SS/
# =====================================

import os
import sys
import io
from datetime import datetime

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import CircleModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask
from PIL import Image

import fitz  # PyMuPDF


# ---------------------------
#  UTIL
# ---------------------------

def ensure_single_logo(logo_dir: str) -> str:
    if not os.path.isdir(logo_dir):
        raise FileNotFoundError(f"Cartella logo non trovata: {logo_dir}")
    logos = [f for f in os.listdir(logo_dir) if f.lower().endswith((".png", ".ico"))]
    if len(logos) == 0:
        raise FileNotFoundError(f"Nessun logo (.png o .ico) in {logo_dir}")
    if len(logos) > 1:
        raise ValueError(f"Trovati più loghi in {logo_dir}. Lascia un solo file.")
    return os.path.join(logo_dir, logos[0])


def generate_qr_image(ssid: str, password: str, style: str, logo_path: str) -> Image.Image:
    """Genera un QR standard o puntinato, con logo al centro, SENZA ombra."""
    payload = f"WIFI:T:WPA;S:{ssid};P:{password};;"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    if style == "artistico":
        qr_img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=CircleModuleDrawer(),
            color_mask=RadialGradiantColorMask(
                back_color=(255, 255, 255),
                center_color=(0, 0, 0),
                edge_color=(40, 40, 40),
            ),
        ).convert("RGBA")
    else:
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    # Applica logo al centro (max 20% del lato)
    logo = Image.open(logo_path).convert("RGBA")
    w, h = qr_img.size
    logo_max = int(min(w, h) * 0.20)
    logo.thumbnail((logo_max, logo_max))
    lx = (w - logo.width) // 2
    ly = (h - logo.height) // 2
    qr_img.paste(logo, (lx, ly), logo)
    return qr_img


# ---------------------------
#  PDF FILLING (ancore testuali)
# ---------------------------

def _find_anchor_bbox(page: fitz.Page, text: str):
    """Trova il rettangolo della prima occorrenza di 'text' (case-sensitive)."""
    hits = page.search_for(text)
    return hits[0] if hits else None


def fill_pdf(template_path: str, out_pdf_path: str, ssid: str, password: str, qr_img: Image.Image):
    """
    Compila il template:
      - scrive SSID accanto a 'Nome della rete'
      - scrive Password accanto a 'Password'
      - copre l'area QR dedicata e inserisce il nuovo QR
    Non modifica nient'altro.
    """
    doc = fitz.open(template_path)
    page = doc[0]

    # --- Ancore testuali ---
    anchor_ssid = _find_anchor_bbox(page, "Nome della rete")
    anchor_pwd  = _find_anchor_bbox(page, "Password")
    anchor_qr   = _find_anchor_bbox(page, "INQUADRARE IL QR CODE")

    if not (anchor_ssid and anchor_pwd and anchor_qr):
        doc.close()
        missing = []
        if not anchor_ssid: missing.append("Nome della rete")
        if not anchor_pwd:  missing.append("Password")
        if not anchor_qr:   missing.append("INQUADRARE IL QR CODE")
        raise RuntimeError(f"Ancora(e) non trovata(e) nel template: {', '.join(missing)}")

    # --- Trova le posizioni REALI dei valori da sostituire ---
    # Cerchiamo direttamente i valori esistenti nel template per sovrascriverli
    anchor_ssid_value = _find_anchor_bbox(page, "ZNR Ospiti")
    anchor_pwd_value  = _find_anchor_bbox(page, "Edoras-2346")

    # Se non troviamo i valori, usiamo posizioni relative alle etichette
    if anchor_ssid_value:
        ssid_x = anchor_ssid_value.x0
        ssid_y = anchor_ssid_value.y0 + 14  # y0 + altezza tipica carattere 12pt
    else:
        ssid_x = anchor_ssid.x1 + 90  # offset verso la colonna destra della tabella
        ssid_y = anchor_ssid.y0 + 14

    if anchor_pwd_value:
        pwd_x = anchor_pwd_value.x0
        pwd_y = anchor_pwd_value.y0 + 14  # y0 + altezza tipica carattere 12pt
    else:
        pwd_x  = anchor_pwd.x1 + 100
        pwd_y  = anchor_pwd.y0 + 14

    # Area QR: cerchiamo il QR esistente o usiamo posizione sotto l'ancora
    # Il QR nel template è a circa 128x128 punti, lo ingrandiamo un po'
    qr_side = 145  # lato QR in punti (più grande di prima)
    # Centra il QR sotto l'ancora
    anchor_center_x = (anchor_qr.x0 + anchor_qr.x1) / 2
    qr_x = anchor_center_x - (qr_side / 2)
    qr_y = anchor_qr.y1 + 15  # sotto l'ancora, con margine ridotto per compensare dimensione maggiore

    # --- Prepara stream immagine QR ---
    qr_buf = io.BytesIO()
    # salviamo come PNG, PyMuPDF lo embedda bene
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    pix = fitz.Pixmap(qr_buf)

    # --- Rimuovi i valori esistenti usando redact (rimozione permanente) ---
    white = (1, 1, 1)

    # Coordinate della colonna destra della tabella (per pulire tutta la cella)
    table_col_right_left = 293.04
    table_col_right_right = 510.24

    if anchor_ssid_value:
        # Redact (rimuovi) tutta la cella SSID (non solo il vecchio valore)
        page.add_redact_annot(fitz.Rect(table_col_right_left + 5, anchor_ssid_value.y0 - 2,
                                        table_col_right_right - 5, anchor_ssid_value.y1 + 2),
                              fill=white)

    if anchor_pwd_value:
        # Redact (rimuovi) tutta la cella Password
        page.add_redact_annot(fitz.Rect(table_col_right_left + 5, anchor_pwd_value.y0 - 2,
                                        table_col_right_right - 5, anchor_pwd_value.y1 + 2),
                              fill=white)

    # Cerca e rimuovi il QR esistente (tutte le immagini nella zona del QR)
    page.add_redact_annot(fitz.Rect(qr_x - 5, qr_y - 5, qr_x + qr_side + 5, qr_y + qr_side + 5),
                          fill=white)

    # Applica tutte le redaction
    page.apply_redactions()

    # Se non abbiamo trovato i valori nel template, copri le aree generiche
    if not anchor_ssid_value or not anchor_pwd_value:
        shape = page.new_shape()
        if not anchor_ssid_value:
            shape.draw_rect(fitz.Rect(ssid_x - 2, ssid_y - 14, ssid_x + 200, ssid_y + 4))
            shape.finish(fill=white, color=white)
        if not anchor_pwd_value:
            shape.draw_rect(fitz.Rect(pwd_x - 2, pwd_y - 14, pwd_x + 200, pwd_y + 4))
            shape.finish(fill=white, color=white)
        shape.commit()

    # --- Testi centrati nella tabella (font: usa font di default del PDF; dimensione 12) ---
    fontname = "helv"
    fontsize = 12

    # Coordinate fisse della tabella (analizzate dal template)
    # La colonna destra va da x=293.04 a x=510.24
    table_col_right_left = 293.04
    table_col_right_right = 510.24
    table_col_right_center = (table_col_right_left + table_col_right_right) / 2  # 401.64

    # Calcola larghezza effettiva del testo per centrarlo
    # Usa PyMuPDF per misurare la larghezza esatta
    ssid_width = fitz.get_text_length(ssid, fontname=fontname, fontsize=fontsize)
    pwd_width = fitz.get_text_length(password, fontname=fontname, fontsize=fontsize)

    # Posiziona il testo centrato nella cella
    ssid_x = table_col_right_center - (ssid_width / 2)
    pwd_x = table_col_right_center - (pwd_width / 2)

    page.insert_text((ssid_x, ssid_y), ssid, fontname=fontname, fontsize=fontsize, fill=(0, 0, 0))
    page.insert_text((pwd_x,  pwd_y),  password, fontname=fontname, fontsize=fontsize, fill=(0, 0, 0))

    # --- Inserisci immagine QR nella box pulita ---
    page.insert_image(fitz.Rect(qr_x, qr_y, qr_x + qr_side, qr_y + qr_side), stream=qr_buf.getvalue())

    # Salva
    doc.save(out_pdf_path)
    doc.close()


# ---------------------------
#  MAIN
# ---------------------------

if __name__ == "__main__":
    print("=== Generatore QR + compilatore PDF (v2.3) ===")
    ssid = input("SSID Wi-Fi: ").strip()
    password = input("Password Wi-Fi: ").strip()

    print("\nTipo QR:")
    print("1 - Standard")
    print("2 - Artistico (puntinato)")
    style = "artistico" if input("Scelta [1/2]: ").strip() == "2" else "standard"

    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")
    logo_dir = os.path.join(static_dir, "logo")
    template_pdf = os.path.join(static_dir, "template.pdf")

    # output datato
    out_root = os.path.join(base_dir, "output")
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = os.path.join(out_root, ts)
    os.makedirs(out_dir, exist_ok=True)

    # logo
    logo_path = ensure_single_logo(logo_dir)

    # genera QR e salva PNG
    qr_img = generate_qr_image(ssid, password, style, logo_path)
    qr_png_path = os.path.join(out_dir, "wifi_qr.png")
    qr_img.convert("RGB").save(qr_png_path, "PNG")
    print(f"QR generato: {qr_png_path}")

    # chiedi se creare PDF
    make_pdf = input("Generare anche il PDF compilato? [s/n]: ").strip().lower() == "s"
    if make_pdf:
        if not os.path.exists(template_pdf):
            print(f"Template PDF non trovato: {template_pdf}")
            sys.exit(1)
        out_pdf = os.path.join(out_dir, "wifi_compilato.pdf")
        try:
            fill_pdf(template_pdf, out_pdf, ssid, password, qr_img.convert("RGB"))
            print(f"PDF compilato: {out_pdf}")
        except Exception as e:
            print(f"Errore compilazione PDF: {e}")
            sys.exit(1)

    print("Fine.")
