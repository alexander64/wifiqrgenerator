# =====================================
# Versione: 2.4
# Script: wifi_qr_with_logo.py
# Descrizione:
#   - Genera QR Wi-Fi (standard o puntinato) con logo (SENZA ombra).
#   - Opzionalmente compila il PDF statico: sostituisce SOLO SSID, password e QR.
#   - Cerca i valori esistenti nel template PDF per sovrascriverli nelle posizioni corrette.
#   - SSID e password CENTRATI nella colonna destra della tabella.
#   - QR più grande (145x145 punti).
#   - Interfaccia CLI elegante con Rich.
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
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich import box
from rich.padding import Padding

console = Console()


# ---------------------------
#  UTIL
# ---------------------------

def show_header(logo_path: str = None):
    """Mostra l'header professionale dell'applicazione."""
    # Crea header elegante
    title_text = Text("\n  WiFi QR Code Generator  \n", style="bold cyan", justify="center")
    title_text.append("         v2.4         \n\n", style="yellow")
    title_text.append("  Genera QR Code WiFi professionali  ", style="dim italic")

    header_panel = Panel(
        title_text,
        box=box.DOUBLE,
        border_style="bright_cyan",
        padding=(1, 2)
    )

    console.print(header_panel)
    console.print()

    # Se c'è un logo, mostra un messaggio
    if logo_path and os.path.exists(logo_path):
        logo_name = os.path.basename(logo_path)
        logo_info = Table(show_header=False, box=None, padding=(0, 1))
        logo_info.add_column(style="dim")
        logo_info.add_column(style="cyan")
        logo_info.add_row("Logo personalizzato:", logo_name)
        console.print(Padding(logo_info, (0, 2)))
        console.print()


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
    console.clear()

    # Carica variabili da .env se presente
    load_dotenv()

    # Carica logo per mostrarlo nell'header
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")
    logo_dir = os.path.join(static_dir, "logo")

    try:
        logo_path = ensure_single_logo(logo_dir)
    except Exception:
        logo_path = None

    # Mostra header elegante con logo
    show_header(logo_path)

    # Mostra pannello configurazione
    config_table = Table(show_header=False, box=None, padding=(0, 1))
    config_table.add_column(style="cyan bold", width=15)
    config_table.add_column(style="white")

    # Leggi SSID da .env se specificato, altrimenti chiedi
    ssid = os.getenv("WIFI_SSID")
    if ssid:
        config_table.add_row("SSID WiFi:", f"{ssid} [dim](da .env)[/dim]")
    else:
        console.print(Panel("Configurazione Rete WiFi", border_style="cyan", box=box.ROUNDED))
        ssid = Prompt.ask("[cyan bold]SSID WiFi[/cyan bold]").strip()

    # Leggi Password da .env se specificato, altrimenti chiedi
    password = os.getenv("WIFI_PASSWORD")
    if password:
        config_table.add_row("Password:", f"{'•' * len(password)} [dim](da .env)[/dim]")
    else:
        password = Prompt.ask("[cyan bold]Password WiFi[/cyan bold]", password=True).strip()

    # Mostra configurazione se caricata da .env
    if os.getenv("WIFI_SSID") or os.getenv("WIFI_PASSWORD"):
        console.print(Panel(config_table, title="Configurazione", border_style="green", box=box.ROUNDED))
        console.print()

    # Selezione tipo QR con tabella
    qr_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 2))
    qr_table.add_column("Opzione", style="cyan bold", justify="center")
    qr_table.add_column("Tipo QR", style="white")
    qr_table.add_column("Descrizione", style="dim")
    qr_table.add_row("1", "Standard", "QR code classico con moduli quadrati")
    qr_table.add_row("2", "Artistico", "QR code con moduli circolari e gradiente")

    console.print(Panel(qr_table, title="Seleziona Stile QR Code", border_style="cyan", box=box.ROUNDED))
    style_choice = Prompt.ask("[cyan bold]Scelta[/cyan bold]", choices=["1", "2"], default="1")
    style = "artistico" if style_choice == "2" else "standard"

    template_pdf = os.path.join(static_dir, "template.pdf")

    # Verifica che il logo sia stato caricato correttamente
    if not logo_path:
        console.print(f"[red bold]✗[/red bold] Errore: Logo non trovato in {logo_dir}")
        sys.exit(1)

    # output datato
    out_root = os.path.join(base_dir, "output")
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = os.path.join(out_root, ts)
    os.makedirs(out_dir, exist_ok=True)

    # genera QR e salva PNG
    console.print()
    with console.status(f"[cyan bold]Generazione QR code ({style})...[/cyan bold]", spinner="dots"):
        qr_img = generate_qr_image(ssid, password, style, logo_path)
        qr_png_path = os.path.join(out_dir, "wifi_qr.png")
        qr_img.convert("RGB").save(qr_png_path, "PNG")

    console.print(f"[green bold]✓[/green bold] QR Code generato: [cyan]{qr_png_path}[/cyan]")

    # chiedi se creare PDF
    console.print()
    make_pdf = Confirm.ask("[cyan bold]Generare anche il PDF compilato?[/cyan bold]", default=False)

    if make_pdf:
        if not os.path.exists(template_pdf):
            console.print(f"[red bold]✗[/red bold] Template PDF non trovato: {template_pdf}")
            sys.exit(1)

        out_pdf = os.path.join(out_dir, "wifi_compilato.pdf")

        with console.status("[cyan bold]Compilazione PDF...[/cyan bold]", spinner="dots"):
            try:
                fill_pdf(template_pdf, out_pdf, ssid, password, qr_img.convert("RGB"))
            except Exception as e:
                console.print(f"[red bold]✗[/red bold] Errore compilazione PDF: {e}")
                sys.exit(1)

        console.print(f"[green bold]✓[/green bold] PDF compilato: [cyan]{out_pdf}[/cyan]")

    # Riepilogo finale
    console.print()
    summary = Table(show_header=False, box=box.ROUNDED, border_style="green", padding=(0, 2))
    summary.add_column(style="green bold", width=12)
    summary.add_column(style="white")
    summary.add_row("SSID:", ssid)
    summary.add_row("Stile QR:", style.capitalize())
    summary.add_row("Output:", out_dir)

    console.print(Panel(summary, title="[green bold]✓ Completato[/green bold]", border_style="green"))
    console.print()
