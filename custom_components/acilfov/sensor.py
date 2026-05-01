import logging
import async_timeout
import aiohttp
from datetime import datetime
from homeassistant.helpers.entity import Entity
from .const import DOMAIN, URL_SOLD, URL_INDEX_PERIOD, URL_PLATI

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setarea platformei de senzori."""
    cookies = config.get("cookies")
    cod_client = config.get("cod_client")
    nr_contract = config.get("nr_contract")

    if not cookies or not cod_client:
        _LOGGER.error("Date de configurare lipsă în configuration.yaml pentru AC Ilfov")
        return

    # Adăugăm toți cei 3 senzori
    sensors = [
        ACIlfovSoldSensor(cookies, cod_client, nr_contract),
        ACIlfovIndexSensor(cookies, cod_client),
        ACIlfovLastPaymentSensor(cookies, cod_client, nr_contract)
    ]
    async_add_entities(sensors, True)

class ACIlfovBaseSensor(Entity):
    """Clasă de bază comună pentru senzorii AC Ilfov."""
    def __init__(self, cookie, cod):
        self._cookie = cookie
        self._cod = cod
        self._state = None
        self._attributes = {}

    @property
    def state(self): return self._state

    @property
    def extra_state_attributes(self): return self._attributes

    @property
    def _headers(self):
        """Generarea headerelor necesare pentru cereri."""
        return {
            "Cookie": self._cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8"
        }

class ACIlfovSoldSensor(ACIlfovBaseSensor):
    def __init__(self, cookie, cod, contract):
        super().__init__(cookie, cod)
        self._contract = contract

    @property
    def name(self): return "AC Ilfov Sold Curent"
    @property
    def unique_id(self): return f"acilfov_sold_{self._cod}"
    @property
    def unit_of_measurement(self): return "RON"
    @property
    def icon(self): return "mdi:water-pump"

    async def async_update(self):
        url = f"{URL_SOLD}?codClient={self._cod}&nrContract={self._contract}"
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.get(url, headers=self._headers) as resp:
                        if resp.status == 200:
                            self._state = float(await resp.text())
        except Exception as e: _LOGGER.error("Eroare Sold: %s", e)

class ACIlfovIndexSensor(ACIlfovBaseSensor):
    @property
    def name(self): return "AC Ilfov Perioada Index"
    @property
    def unique_id(self): return f"acilfov_index_{self._cod}"
    @property
    def icon(self): return "mdi:calendar-clock"

    async def async_update(self):
        url = f"{URL_INDEX_PERIOD}?codClient={self._cod}"
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.get(url, headers=self._headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            self._state = data.get("start")
                            self._attributes["mesaj"] = data.get("response")
        except Exception as e: _LOGGER.error("Eroare Index: %s", e)

class ACIlfovLastPaymentSensor(ACIlfovBaseSensor):
    def __init__(self, cookie, cod, contract):
        super().__init__(cookie, cod)
        self._contract = contract

    @property
    def name(self): return "AC Ilfov Ultima Plata"
    @property
    def unique_id(self): return f"acilfov_plata_{self._cod}"
    @property
    def unit_of_measurement(self): return "RON"
    @property
    def icon(self): return "mdi:cash-check"

    async def async_update(self):
        # Folosim URL-ul simplu pentru Plati, asa cum a fost extras initial
        url = URL_PLATI
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    # Încercăm metoda GET
                    async with session.get(url, headers=self._headers) as resp:
                        if resp.status == 200:
                            await self._parse_data(await resp.json())
                        else:
                            # Dacă eșuează, înregistrăm eroarea de la server în log-uri
                            err_text = await resp.text()
                            _LOGGER.error("Eroare GET Plati HTTP %s: %s", resp.status, err_text[:250])
                            
                            # Fallback pe POST cu un body gol
                            async with session.post(url, headers=self._headers, json={}) as resp2:
                                if resp2.status == 200:
                                    await self._parse_data(await resp2.json())
                                else:
                                    err_text2 = await resp2.text()
                                    _LOGGER.error("Eroare POST Plati HTTP %s: %s", resp2.status, err_text2[:250])
        except Exception as e: 
            _LOGGER.error("Eroare conexiune Plata: %s", e)

    async def _parse_data(self, data):
        """Metodă separată pentru a citi JSON-ul dacă cererea a avut succes."""
        # Verificăm dacă JSON-ul are secțiunea "records" și dacă nu este goală
        if data and data.get("records") and len(data["records"]) > 0:
            last_row = data["records"][0].get("row", {})
            self._state = last_row.get("valoarePlata")
            
            raw_date = last_row.get("dataPlata", "")
            if "/Date(" in raw_date:
                ts = int(raw_date.replace("/Date(", "").replace(")/", "")) / 1000
                self._attributes["data_plata"] = datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
            
            self._attributes["document"] = last_row.get("documentPlata")
            self._attributes["metoda"] = last_row.get("canalIncasare")
        else:
            _LOGGER.error("Plati: Serverul a răspuns cu OK, dar lista de plăți este goală.")