# WiFi QR Code Generator

Generatore automatico di QR code WiFi con logo personalizzato e sistema intelligente di compilazione PDF. Progettato per studi professionali che vogliono fornire ai clienti un modo elegante per connettersi alla rete Wi-Fi ospiti.

## Caratteristiche

- **Generazione QR Code WiFi**: Crea QR code nel formato standard compatibile con Android e iOS
- **Due stili grafici**:
  - **Standard**: QR code classico nero su bianco
  - **Artistico**: QR code puntinato con gradiente radiale per un aspetto più professionale
- **Logo personalizzato**: Inserisce automaticamente il tuo logo al centro del QR (20% della dimensione)
- **Compilazione PDF intelligente**:
  - Cerca automaticamente i valori esistenti nel template PDF
  - Sostituisce solo SSID, password e QR code
  - Preserva completamente il resto del layout e della grafica
  - Usa la funzione di redaction per rimuovere completamente i vecchi valori
- **Output organizzato**: Salva i file in cartelle con timestamp per tenere traccia delle generazioni

## Struttura del Progetto

```
wifiqrcodegenerator/
├── script.py              # Script principale (v2.1)
├── requirements.txt       # Dipendenze Python
├── static/
│   ├── logo/
│   │   └── logo.ico      # Il tuo logo (PNG o ICO - un solo file!)
│   └── template.pdf      # Template PDF da compilare (opzionale)
└── output/
    └── YYYY-MM-DD_HH-MM-SS/
        ├── wifi_qr.png   # QR code generato
        └── wifi_compilato.pdf  # PDF compilato (se richiesto)
```

## Requisiti

- Python 3.7+
- Le seguenti librerie Python (vedi `requirements.txt`):
  - `qrcode[pil]`: Generazione QR code con supporto immagini
  - `Pillow`: Manipolazione e composizione immagini
  - `PyMuPDF`: Lettura e modifica PDF
  - `python-dotenv`: Caricamento configurazione da file .env

## Installazione

1. Clona o scarica questo repository

2. Crea un ambiente virtuale (consigliato):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# oppure
source venv/bin/activate  # Linux/Mac
```

3. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

4. Prepara i file necessari:
   - Inserisci il tuo logo in `static/logo/` (solo un file, .png o .ico)
   - Se vuoi usare la funzione PDF, inserisci il template in `static/template.pdf`

5. (Opzionale) Configura le credenziali WiFi:
   - Copia `.env.example` in `.env`
   - Inserisci SSID e/o password nel file `.env`
   - Se configurati, non verranno chiesti durante l'esecuzione

## Utilizzo

### Metodo 1: Esecuzione interattiva

Esegui lo script:

```bash
python script.py
```

Lo script ti chiederà:

1. **SSID Wi-Fi**: Il nome della tua rete wireless (se non specificato in `.env`)
2. **Password Wi-Fi**: La password della rete (se non specificata in `.env`)
3. **Tipo QR**:
   - `1` per QR standard (quadrati neri)
   - `2` per QR artistico (puntinato con gradiente)
4. **Generare PDF**: `s` per generare anche il PDF compilato, `n` per solo QR

### Metodo 2: Configurazione con file .env

Per evitare di inserire SSID e password ogni volta:

1. Copia il file `.env.example` in `.env`:
   ```bash
   cp .env.example .env
   ```

2. Modifica `.env` e inserisci le tue credenziali:
   ```
   WIFI_SSID=NomeRete
   WIFI_PASSWORD=PasswordRete
   ```

3. Esegui lo script - SSID e password verranno letti dal file `.env`:
   ```bash
   python script.py
   ```

### Esempio di Sessione

**Senza .env (chiede tutto):**
```
=== Generatore QR + compilatore PDF (v2.3) ===
SSID Wi-Fi: MiaRete
Password Wi-Fi: Password123!

Tipo QR:
1 - Standard
2 - Artistico (puntinato)
Scelta [1/2]: 2

QR generato: output/2025-10-31_15-30-45/wifi_qr.png
Generare anche il PDF compilato? [s/n]: s
PDF compilato: output/2025-10-31_15-30-45/wifi_compilato.pdf
Fine.
```

**Con .env configurato (legge da file):**
```
=== Generatore QR + compilatore PDF (v2.3) ===
SSID Wi-Fi: MiaRete (da .env)
Password Wi-Fi: ************ (da .env)

Tipo QR:
1 - Standard
2 - Artistico (puntinato)
Scelta [1/2]: 2

QR generato: output/2025-10-31_15-30-45/wifi_qr.png
Generare anche il PDF compilato? [s/n]: s
PDF compilato: output/2025-10-31_15-30-45/wifi_compilato.pdf
Fine.
```

## Come Funziona

### Generazione QR Code (script.py:44-78)

Lo script genera un QR code nel formato standard WiFi:
```
WIFI:T:WPA;S:<SSID>;P:<PASSWORD>;;
```

- Usa `ERROR_CORRECT_H` (30% di correzione errori) per permettere l'inserimento del logo
- Ridimensiona il logo esattamente al 20% del lato del QR per garantire leggibilità
- Applica il logo al centro con trasparenza (RGBA)
- Supporta due stili: standard (quadrati) e artistico (CircleModuleDrawer con gradiente radiale)

### Compilazione PDF Intelligente (script.py:90-217)

Il sistema usa un approccio intelligente a 3 fasi:

**Fase 1: Ricerca delle posizioni (script.py:102-141)**
1. Cerca le ancore testuali nel template:
   - "Nome della rete" e "Password" (etichette della tabella)
   - "INQUADRARE IL QR CODE" (area QR)
2. **IMPORTANTE**: Cerca anche i valori esistenti ("ZNR Ospiti", "Edoras-2346")
3. Usa le coordinate dei valori esistenti per l'allineamento verticale

**Fase 2: Rimozione valori vecchi (script.py:150-171)**
1. Analizza la struttura della tabella (bordo sinistro: 102.72, divisore: 293.04, bordo destro: 510.24)
2. Usa `page.add_redact_annot()` per marcare **tutta la cella** (non solo il vecchio valore)
3. Rimuove permanentemente con `page.apply_redactions()` garantendo rimozione completa

**Fase 3: Inserimento nuovi valori con centratura (script.py:183-203)**
1. Calcola il centro della colonna destra: (293.04 + 510.24) / 2 = **401.64 punti**
2. Usa `fitz.get_text_length()` per misurare esattamente la larghezza del nuovo testo
3. Centra perfettamente il testo: `x = centro_colonna - (larghezza_testo / 2)`
4. Inserisce il QR (145x145 punti) centrato sotto "INQUADRARE IL QR CODE"
5. Mantiene intatto tutto il resto del layout originale

### Validazioni

- **Logo singolo** (script.py:33-41): Verifica che ci sia esattamente un file logo nella cartella
- **Ancore presenti** (script.py:106-112): Controlla che il template PDF contenga tutte le ancore necessarie
- **Gestione errori**: Messaggi chiari in caso di file mancanti o template non valido

## Personalizzazione

### Modificare le dimensioni del QR nel PDF

Nel file `script.py:137`, modifica:
```python
qr_side = 145  # lato QR in punti (72 punti = 1 pollice)
```
**Nota**: 145 punti = ~5.1 cm (2.01 pollici). Modifica solo se il tuo template ha un'area QR diversa.

### Cambiare la percentuale del logo nel QR

Nel file `script.py:72`, modifica:
```python
logo_max = int(min(w, h) * 0.20)  # 20% del lato del QR
```
**Attenzione**: Non superare il 30% o il QR potrebbe non essere leggibile.

### Cambiare i colori del QR artistico

Nel file `script.py:60-64`, modifica i parametri di `RadialGradiantColorMask`:
```python
color_mask=RadialGradiantColorMask(
    back_color=(255, 255, 255),  # Bianco
    center_color=(0, 0, 0),      # Nero al centro
    edge_color=(40, 40, 40),     # Grigio scuro ai bordi
)
```

### Usare un template PDF diverso

Il sistema è progettato per funzionare con qualsiasi template PDF che contiene:

1. **Valori SSID e Password esistenti**: Il sistema li cerca e sostituisce
   - Se usi il template fornito, i valori sono "ZNR Ospiti" e "Edoras-2346"
   - Per altri template, modifica script.py:117-118 con i tuoi valori di default

2. **Ancore testuali** (opzionali ma consigliate):
   - "Nome della rete" - per trovare l'area SSID
   - "Password" - per trovare l'area password
   - "INQUADRARE IL QR CODE" - per posizionare il QR

3. **Layout**: Il sistema preserva completamente il resto del PDF (loghi, testo, formattazione)

## Versione

**v2.3** - Ultima versione stabile

Novità v2.3:
- **NUOVA FUNZIONALITÀ**: Supporto file `.env` per configurare SSID e password
  - Se specificate nel `.env`, non vengono chieste durante l'esecuzione
  - File `.env.example` fornito come template
  - La password viene mascherata nell'output per sicurezza
- **MIGLIORAMENTO**: SSID e password ora sono **perfettamente centrati** nella colonna destra della tabella
- **MIGLIORAMENTO**: QR code più grande (145x145 punti invece di 128x128)
- Usa `fitz.get_text_length()` per calcolare la larghezza esatta del testo e centrarlo con precisione assoluta
- Pulisce tutta la cella della tabella (non solo il vecchio valore) per evitare sovrapposizioni
- Aggiunta dipendenza `python-dotenv` per gestione file .env

Miglioramenti v2.2 (rispetto alla v2.1):
- **FIX**: Posizionamento corretto di SSID e password nel template PDF
- **FIX**: Il sistema cerca i valori esistenti nel template ("ZNR Ospiti", "Edoras-2346") e li sostituisce
- **FIX**: Usa la funzione `redact` di PyMuPDF per rimozione permanente dei vecchi valori
- **FIX**: QR code centrato correttamente sotto "INQUADRARE IL QR CODE"
- Supporto per template con layout personalizzato

## Licenza

Questo progetto è fornito così com'è, libero per uso personale e commerciale.

## Note Tecniche

- Il QR code usa il formato `WIFI:T:WPA` compatibile con Android e iOS
- L'alta correzione errori (ERROR_CORRECT_H) permette di coprire fino al 30% del QR con il logo (impostato al 20% di default)
- Il sistema cerca automaticamente i valori nel template PDF per posizionamento preciso
- Usa PyMuPDF `redact` per rimozione permanente dei vecchi valori (non solo copertura visiva)
- Le coordinate PDF sono in punti (72 DPI: 72 punti = 1 pollice, 28.35 punti = 1 cm)
- Gli output sono in formato RGB per massima compatibilità
- Il template di esempio è per "Studio ZNR notai" ma è completamente personalizzabile

## Troubleshooting

**Errore: "Nessun logo (.png o .ico) in static/logo"**
- Verifica che il file logo esista nella cartella `static/logo/`
- Assicurati che abbia estensione `.png` o `.ico`
- Il logo può essere in qualsiasi formato, verrà convertito automaticamente

**Errore: "Trovati più loghi in static/logo"**
- Lascia solo un file logo nella cartella
- Il sistema accetta un solo logo per evitare ambiguità

**Errore: "Ancora(e) non trovata(e) nel template"**
- Verifica che il template PDF contenga esattamente i testi:
  - "Nome della rete"
  - "Password"
  - "INQUADRARE IL QR CODE"
- **Nota**: Il sistema cerca anche i valori esistenti nel template per la sostituzione automatica

**Il QR non si legge**
- Verifica che SSID e password siano corretti
- Prova a ridurre la dimensione del logo (modifica il 20% in script.py:72)
- Usa lo stile standard invece di artistico
- Assicurati che ci sia buon contrasto (sfondo chiaro, QR scuro)

**I vecchi valori sono ancora visibili nel PDF**
- **Questo non dovrebbe succedere in v2.2**
- Verifica di aver aggiornato lo script all'ultima versione
- Il sistema usa `redact` che rimuove permanentemente i vecchi valori

**Il posizionamento nel PDF è sbagliato**
- **Risolto in v2.2**: Il sistema ora cerca i valori esistenti nel template
- Se usi un template diverso da quello fornito, modifica i valori di ricerca in script.py:117-118
- Il sistema cerca "ZNR Ospiti" e "Edoras-2346" per default

**I testi non sono centrati nella tabella**
- **Risolto in v2.3**: Il sistema ora centra perfettamente SSID e password usando `fitz.get_text_length()`
- Se usi un template diverso con una tabella di dimensioni diverse, modifica le coordinate in script.py:154-155:
  - `table_col_right_left = 293.04` (bordo sinistro colonna destra)
  - `table_col_right_right = 510.24` (bordo destro colonna destra)
