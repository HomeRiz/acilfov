# AC Ilfov — Integrare Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.x%2B-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Integrare custom pentru [Home Assistant](https://www.home-assistant.io/) care monitorizează contul tău de utilități **Apă Canal Ilfov** (platforma EMSYS).

Deoarece portalul folosește un sistem de securitate anti-bot avansat (Cloudflare Turnstile), autentificarea clasică cu utilizator și parolă din scripturi este blocată. Această integrare folosește o abordare stabilă bazată pe **Cookie de Sesiune**, ocolind complet Cloudflare-ul și aducând datele direct în dashboard-ul tău.

---

## Ce face integrarea

- **Sold Curent** — suma datorată la zi (în RON)
- **Perioada Index** — data de început a perioadei de transmitere a indexului și statusul (activ/inactiv)
- **Detalii Contract** — statusul contractului, adresa punctului de consum și data începerii
- **Ultima Plată** — valoarea ultimei plăți înregistrate, data acesteia și metoda de plată
- **Bypass Securitate** — folosește direct cookie-ul din browser pentru a naviga nedetectat prin Cloudflare
- **Device Registry** — grupează automat toți senzorii sub un singur dispozitiv pentru o gestionare simplă în interfața Home Assistant

---

## Sursa datelor

Datele vin prin interogarea directă a portalului clienți EMSYS (`acilfov.emsys.ro`), care expune endpoint-uri REST pentru:

| Endpoint | Descriere |
|----------|-----------|
| `/rest/self/contract/getSoldClient` | Sold curent datorat |
| `/rest/self/transmitere/Transmiteres/getPerioadaActiva` | Status perioadă citire index |
| `/rest/self/contract/getListaCodClientContracte` | Detalii despre contract și client |
| `/rest/self/istoricPlati/Platis/getList` | Arhiva și statusul ultimei plăți |

Autentificarea se face furnizând un Cookie valid obținut anterior din browser-ul utilizatorului.

---

## Instalare

### HACS (recomandat)

1. Deschide HACS în Home Assistant
2. Click pe cele 3 puncte (⋮) din colțul dreapta sus → **Custom repositories**
3. Adaugă URL-ul repository-ului tău (ex: `https://github.com/HomeRiz/acilfov`)
4. Categorie: **Integration**
5. Click **Add** → găsește „AC Ilfov" → **Install**
6. Restartează Home Assistant

### Manual

1. Copiază folderul `custom_components/acilfov/` în directorul `config/custom_components/` din Home Assistant
2. Restartează Home Assistant

---

## Configurare

### Pasul 1 — Obținerea datelor de autentificare (Cookie)

Pentru a trece de bariera Cloudflare, trebuie să te loghezi manual o singură dată din browser:
1. Deschide browserul (ex: Chrome) pe PC și navighează la [Portalul AC Ilfov](https://acilfov.emsys.ro/self_utilities/).
2. Loghează-te normal cu adresa de email și parola ta.
3. Apasă tasta **`F12`** pentru a deschide Developer Tools.
4. Mergi la tab-ul **`Network`** (Rețea) și dă un **Refresh** (F5) paginii.
5. Dă click pe prima cerere din listă (ex: `index.html`).
6. În panoul din dreapta, mergi la **`Headers`** -> **`Request Headers`**.
7. Caută linia **`cookie:`** și copiază absolut tot textul de după două puncte (ex: `sl-session=...; SELF_UTI_COOKIE=...`).

*Notă: Codul de Client și Numărul de Contract le găsești afișate în portal sau pe orice factură fizică.*

### Pasul 2 — Adaugă integrarea

1. **Setări** → **Dispozitive și Servicii** → **Adaugă Integrare**
2. Caută „**AC Ilfov**"
3. Completează formularul:

| Câmp | Descriere | Implicit |
|------|-----------|----------|
| **Cookies** | Textul lung extras din browser (F12) | — |
| **Cod Client** | Codul tău de client (Ex: 1234) | — |
| **Număr Contract** | Numărul contractului tău (Ex: 20) | — |

---

## Entități create

Integrarea creează un **device** „Cont AC Ilfov (CodClient)" cu următorii senzori:

### Senzori de bază

| Entitate | Descriere | Valoare principală |
|----------|-----------|-------------------|
| `Sold Curent` | Suma datorată la zi | Valoarea în RON |
| `Perioada Index` | Status transmitere index | Data de început |
| `Detalii Contract` | Stare contract curent | ACTIV / INACTIV |
| `Ultima Plata` | Valoarea celei mai recente plăți | Valoarea în RON |

---

### Senzor: Sold Curent

**Valoare principală**: suma de plată curentă

**Atribute**:
```yaml
unit_of_measurement: "RON"
icon: "mdi:water-pump"
```

### Senzor: Perioada Index

**Valoare principală**: data de început a perioadei (ex: 2026-05-20)

**Atribute**:
```yaml
mesaj: "Perioada de transmitere nu este activă"
icon: "mdi:calendar-clock"
```

### Senzor: Detalii Contract

**Valoare principală**: ACTIV

**Atribute**:
```yaml
client: "Nume Prenume"
adresa: "STR. PRINCIPALA NR 1, ILFOV"
numar_contract: "79"
data_inceput: "15-08-2023"
icon: "mdi:file-document-outline"
```

### Senzor: Ultima Plata

**Valoare principală**: suma ultimei plăți (ex: 89.50)

**Atribute**:
```yaml
data_plata: "02-05-2026"
document: "CHITANTA-12345"
metoda: "Plata Online"
unit_of_measurement: "RON"
icon: "mdi:cash-check"
```

---

## Exemple de automatizări

### Notificare Factură Nouă (Soldul crește)
```yaml
automation:
  - alias: "Notificare Factură Nouă Apă"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ac_ilfov_sold_curent
        above: 0
    action:
      - service: notify.mobile_app_telefonul_meu
        data:
          title: "Factură nouă Apă Canal Ilfov!"
          message: >
            A fost emisă o factură nouă. Soldul tău curent este de {{ states('sensor.ac_ilfov_sold_curent') }} RON.
```

### Notificare Transmitere Index

```yaml
automation:
  - alias: "Notificare Transmitere Index Apă"
    trigger:
      - platform: state
        entity_id: sensor.ac_ilfov_perioada_index
    condition:
      - condition: template
        value_template: >
          {{ 'activă' in state_attr('sensor.ac_ilfov_perioada_index', 'mesaj') | lower }}
    action:
      - service: notify.mobile_app_telefonul_meu
        data:
          title: "E timpul pentru Index!"
          message: "Perioada de transmitere a indexului AC Ilfov a început."
```

---

## Structura fișierelor

```text
custom_components/acilfov/
├── __init__.py          # Setup-ul integrării și înregistrarea platformelor (Device Registry)
├── config_flow.py       # Fereastra de UI pentru introducerea datelor (Cookies)
├── const.py             # Constante și URL-uri API EMSYS
├── manifest.json        # Metadata integrării
├── sensor.py            # Logica de extragere a datelor (REST API)
├── strings.json         # Traducerile pentru interfața grafică
└── brand/
    ├── icon.png         # Pictogramă integrare
    └── logo.png         # Logo integrare
```

---

## Cerințe

- **Home Assistant** 2024.x sau mai nou
- **Cont Apă Canal Ilfov** valid pe platforma EMSYS
- Date extrase manual: **Cookie**, **Cod Client** și **Nr. Contract**

---

## Limitări cunoscute

1. **Cloudflare Turnstile** — Platforma EMSYS este protejată sever împotriva scripturilor automate. Din acest motiv, autentificarea directă cu *User* și *Parolă* nu este suportată, integrarea bazându-se pe Cookie-ul extras manual din browser.
2. **Expirarea Cookie-ului** — De regulă, cookie-ul de sesiune (`SELF_UTI_COOKIE`) are o durată de viață foarte lungă. Dacă senzorii devin indisponibili, va trebui să te loghezi din nou în browser, să obții noul cookie și să re-adaugi integrarea.
3. **O singură instanță per Cod Client** — Sistemul folosește Codul de Client ca ID unic.

---

## Contribuții

Contribuțiile sunt binevenite! Simte-te liber să trimiți un pull request sau să raportezi probleme.

---

## Suport

Dacă îți place această integrare, oferă-i un ⭐ pe GitHub!

## Licență

MIT