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

    # Adăugăm toți cei 3 senzori în listă
    sensors = [
        ACIlfovSoldSensor(cookies, cod_client, nr_contract),
        ACIlfovIndexSensor(cookies, cod_client),
        ACIlfovLastPaymentSensor(cookies, cod_client)
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
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def _headers(self):
        """Generarea headerelor necesare pentru cereri."""
        return {
            "Cookie": self._cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*"
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
                with async_timeout.timeout(10):
                    async with session.get(url, headers=self._headers) as resp:
                        if resp.status == 200:
                            data = await resp.text()
                            self._state = float(data)
                        else:
                            _LOGGER.error("Eroare Sold: HTTP %s", resp.status)
        except Exception as e:
            _LOGGER.error("Eroare conexiune Sold: %s", e)

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
                with async_timeout.timeout(10):
                    async with session.get(url, headers=self._headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            self._state = data.get("start")
                            self._attributes["mesaj"] = data.get("response")
                        else:
                            _LOGGER.error("Eroare Index: HTTP %s", resp.status)
        except Exception as e:
            _LOGGER.error("Eroare conexiune Index: %s", e)

class ACIlfovLastPaymentSensor(ACIlfovBaseSensor):
    @property
    def name(self): return "AC Ilfov Ultima Plata"
    @property
    def unique_id(self): return f"acilfov_plata_{self._cod}"
    @property
    def unit_of_measurement(self): return "RON"
    @property
    def icon(self): return "mdi:cash-check"

    async def async_update(self):
        # Aici folosim un POST pentru ca Platis e de obicei un endpoint de tabel
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(10):
                    # Încercăm GET mai întâi cum am văzut în screenshot
                    async with session.get(URL_PLATI, headers=self._headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("records"):
                                last_row = data["records"][0]["row"]
                                self._state = last_row.get("valoarePlata")
                                
                                # Extragem si convertim data
                                raw_date = last_row.get("dataPlata", "")
                                if "/Date(" in raw_date:
                                    ts = int(raw_date.replace("/Date(", "").replace(")/", "")) / 1000
                                    self._attributes["data_plata"] = datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
                                
                                self._attributes["document"] = last_row.get("documentPlata")
                                self._attributes["metoda"] = last_row.get("canalIncasare")
                        else:
                            _LOGGER.error("Eroare Plati: HTTP %s", resp.status)
        except Exception as e:
            _LOGGER.error("Eroare conexiune Plati: %s", e)