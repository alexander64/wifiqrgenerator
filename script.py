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
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich import box
from rich.padding import Padding

import questionary
from questionary import Style
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.widgets import RadioList
from prompt_toolkit.formatted_text import HTML

console = Console()

# Stile questionary per abbinarsi a Rich
custom_style = Style([
    ('qmark', 'fg:yellow bold'),
    ('question', 'fg:white bold'),
    ('answer', 'fg:green bold'),
    ('pointer', 'fg:yellow bold'),
    ('highlighted', 'fg:yellow bold'),
    ('selected', 'fg:green'),
    ('separator', 'fg:white'),
    ('instruction', 'fg:white dim'),
])


def ask_yes_no(question: str, default: bool = False) -> bool:
    """
    Chiede Sì/No con navigazione frecce + shortcut nascosti s/y/n
    SENZA numeri mostrati
    """
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.shortcuts import radiolist_dialog
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.styles import Style as PTStyle

    # Stato della selezione
    class State:
        selected = 1 if not default else 0  # 0=Sì, 1=No

    # Key bindings
    kb = KeyBindings()

    @kb.add('up')
    @kb.add('k')
    def move_up(event):
        State.selected = max(0, State.selected - 1)

    @kb.add('down')
    @kb.add('j')
    def move_down(event):
        State.selected = min(1, State.selected + 1)

    @kb.add('enter')
    def accept(event):
        event.app.exit(result=State.selected == 0)

    # Shortcut nascosti
    @kb.add('s')
    @kb.add('y')
    def select_yes(event):
        event.app.exit(result=True)

    @kb.add('n')
    def select_no(event):
        event.app.exit(result=False)

    @kb.add('c-c')  # Ctrl-C per uscire
    def exit(event):
        event.app.exit(result=False)

    def get_text():
        """Genera il testo formattato per il prompt"""
        lines = [('class:question', f'>> {question}\n')]

        # Opzione Sì
        if State.selected == 0:
            lines.append(('class:selected', '  → Sì\n'))
        else:
            lines.append(('', '    Sì\n'))

        # Opzione No
        if State.selected == 1:
            lines.append(('class:selected', '  → No\n'))
        else:
            lines.append(('', '    No\n'))

        return FormattedText(lines)

    # Layout
    text_window = Window(
        content=FormattedTextControl(get_text),
        dont_extend_height=True
    )

    root_container = HSplit([text_window])
    layout = Layout(root_container)

    # Stile
    style = PTStyle.from_dict({
        'question': '#ffffff bold',
        'selected': '#ffff00 bold',
    })

    # App
    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
    )

    return app.run()


# ---------------------------
#  UTIL
# ---------------------------

def get_dominant_color(image_path: str) -> str:
    """Estrae il colore dominante dal logo per usarlo nell'ASCII art."""
    try:
        img = Image.open(image_path)
        img = img.convert("RGB")
        img = img.resize((50, 50))  # Ridimensiona per velocità

        pixels = img.getdata()
        pixel_count = {}

        for pixel in pixels:
            # Ignora pixel troppo chiari (bianchi/trasparenti)
            if sum(pixel) < 700:  # Non bianco
                pixel_count[pixel] = pixel_count.get(pixel, 0) + 1

        if not pixel_count:
            return "bright_white"

        # Trova colore più frequente
        dominant = max(pixel_count, key=pixel_count.get)
        r, g, b = dominant

        # Converti in colore Rich
        # Se è blu predominante
        if b > r and b > g:
            return "blue"
        # Se è rosso predominante
        elif r > g and r > b:
            return "red"
        # Se è verde predominante
        elif g > r and g > b:
            return "green"
        # Se è giallo
        elif r > 150 and g > 150 and b < 100:
            return "yellow"
        # Se è scuro
        elif r < 100 and g < 100 and b < 100:
            return "bright_black"
        else:
            return "white"
    except:
        return "white"


def image_to_ascii(image_path: str, width: int = 25) -> tuple:
    """Converte un'immagine in ASCII art compatta. Ritorna (ascii_art, color)."""
    try:
        # ASCII characters dal più scuro al più chiaro
        ASCII_CHARS = ["@", "#", "%", "*", "+", ":", ".", " "]

        img = Image.open(image_path)

        # Ottieni colore dominante
        color = get_dominant_color(image_path)

        # Converti in scala di grigi
        img = img.convert("L")

        # Ridimensiona mantenendo aspect ratio
        aspect_ratio = img.height / img.width
        new_height = int(width * aspect_ratio * 0.45)
        img = img.resize((width, new_height))

        # Converti pixel in ASCII
        pixels = img.getdata()
        ascii_str = ""
        for i, pixel in enumerate(pixels):
            ascii_str += ASCII_CHARS[min(pixel // 32, len(ASCII_CHARS) - 1)]
            if (i + 1) % width == 0:
                ascii_str += "\n"

        return ascii_str.rstrip(), color
    except Exception:
        return None, "white"


def show_header(logo_path: str = None):
    """Mostra l'header professionale ed elegante con logo compatto."""
    from rich.align import Align

    # Header con logo piccolo ed elegante
    header_parts = []

    # Logo ASCII piccolo con colore del logo originale
    if logo_path and os.path.exists(logo_path):
        result = image_to_ascii(logo_path, width=20)
        if result[0]:
            ascii_logo, logo_color = result
            # Rendi le @ più scure usando bold
            logo_text = Text()
            for char in ascii_logo:
                if char == '@':
                    logo_text.append(char, style=f"bold {logo_color}")
                elif char == '#':
                    logo_text.append(char, style=f"{logo_color}")
                else:
                    logo_text.append(char, style=f"dim {logo_color}")
            header_parts.append(logo_text)

    # Titolo in grigio chiaro
    title = Text()
    title.append("\n" if header_parts else "", style="")
    title.append("WiFi QR Code Generator", style="bold white")
    title.append(" v2.4", style="bright_black")
    header_parts.append(title)

    # Separatore grigio
    sep = Text("-" * 45, style="bright_black")
    header_parts.append(sep)

    console.print("\n")
    for part in header_parts:
        console.print(Align.center(part))
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



def clean_env_vars():
    """Rimuove le variabili d'ambiente WiFi dalla sessione corrente."""
    if "WIFI_SSID" in os.environ:
        del os.environ["WIFI_SSID"]
    if "WIFI_PASSWORD" in os.environ:
        del os.environ["WIFI_PASSWORD"]


if __name__ == "__main__":
    console.clear()
    load_dotenv()

    # Setup percorsi
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")
    logo_dir = os.path.join(static_dir, "logo")
    template_pdf = os.path.join(static_dir, "template.pdf")

    # Carica logo
    try:
        logo_path = ensure_single_logo(logo_dir)
    except Exception as e:
        console.print(f"[red bold]✗ Errore logo:[/red bold] {e}")
        sys.exit(1)

    # Mostra header con logo convertito in ASCII art
    show_header(logo_path)

    # Carica SSID e Password da .env (o None)
    ssid = os.getenv("WIFI_SSID")
    password = os.getenv("WIFI_PASSWORD")

    # Traccia cosa viene da env per mostrare opzioni override
    has_env_ssid = ssid is not None
    has_env_password = password is not None

    console.print()

    # Chiedi SSID con default se da env
    if has_env_ssid:
        new_ssid = Prompt.ask(f"[white]SSID[/white]", default=ssid).strip()
        if new_ssid != ssid:
            ssid = new_ssid
            os.environ["WIFI_SSID"] = new_ssid
    else:
        ssid = Prompt.ask("[white]SSID (nome rete)[/white]").strip()

    # Chiedi Password con possibilità di override se da env
    if has_env_password:
        console.print(f"[dim white]Password attuale: {password} (da .env)[/dim white]")
        new_password = Prompt.ask("[white]Password[/white] [dim](invio per mantenere)[/dim]", default="").strip()
        if new_password:
            password = new_password
            os.environ["WIFI_PASSWORD"] = new_password
    else:
        password = Prompt.ask("[white]Password WiFi[/white]").strip()

    console.print()

    # Mostra menu e ottieni scelta
    while True:
        choice = questionary.select(
            "Cosa vuoi fare?",
            choices=[
                questionary.Choice("QR Standard - QR code classico con moduli quadrati", value="standard"),
                questionary.Choice("QR Artistico - QR code con moduli circolari e gradiente", value="artistico"),
                questionary.Separator(),
                questionary.Choice("Esci", value="exit"),
                questionary.Choice("Esci e pulisci variabili env", value="exit_clean"),
            ],
            style=custom_style,
            qmark=">>",
            pointer="→"
        ).ask()

        # Gestione uscita
        if choice == "exit":
            console.print("\n[yellow]Arrivederci![/yellow]\n")
            sys.exit(0)

        # Gestione uscita con pulizia env
        if choice == "exit_clean":
            clean_env_vars()
            console.print("\n[yellow]Variabili env pulite. Arrivederci![/yellow]\n")
            sys.exit(0)

        # Determina stile QR
        style = choice
        style_name = "Standard" if choice == "standard" else "Artistico"

        # Output directory
        out_root = os.path.join(base_dir, "output")
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_dir = os.path.join(out_root, ts)
        os.makedirs(out_dir, exist_ok=True)

        # Genera QR
        console.print()
        with console.status(f"[bold white]>> Generazione QR code {style}...[/bold white]", spinner="dots"):
            qr_img = generate_qr_image(ssid, password, style, logo_path)
            qr_png_path = os.path.join(out_dir, "wifi_qr.png")
            qr_img.convert("RGB").save(qr_png_path, "PNG")

        console.print(f"[green bold][OK][/green bold] QR Code generato: [white]{qr_png_path}[/white]\n")

        # Chiedi PDF - usa frecce + shortcut nascosti
        make_pdf = ask_yes_no("Generare anche il PDF compilato?", default=False)

        if make_pdf:
            if not os.path.exists(template_pdf):
                console.print(f"[red bold][ERRORE][/red bold] Template PDF non trovato: {template_pdf}\n")
            else:
                out_pdf = os.path.join(out_dir, "wifi_compilato.pdf")

                with console.status("[bold white]>> Compilazione PDF...[/bold white]", spinner="dots"):
                    try:
                        fill_pdf(template_pdf, out_pdf, ssid, password, qr_img.convert("RGB"))
                        console.print(f"[green bold][OK][/green bold] PDF compilato: [white]{out_pdf}[/white]\n")
                    except Exception as e:
                        console.print(f"[red bold][ERRORE][/red bold] Compilazione PDF: {e}\n")

        # Riepilogo
        from rich.align import Align
        summary = Table(show_header=False, box=box.SIMPLE, border_style="green", padding=(0, 2))
        summary.add_column(style="green bold", width=15)
        summary.add_column(style="white", width=50)
        summary.add_row("SSID:", ssid)
        summary.add_row("Stile:", style_name)
        summary.add_row("Output:", out_dir)

        console.print(Align.center(Panel(summary, title="[green bold]>> COMPLETATO <<", border_style="green")))
        console.print()

        # Chiedi se continuare - usa frecce + shortcut nascosti
        if not ask_yes_no("Generare un altro QR code?", default=False):
            console.print("\n[yellow]Arrivederci![/yellow]\n")
            break
