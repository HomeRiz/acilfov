import logging
import async_timeout
import aiohttp
from datetime import datetime
from homeassistant.helpers.entity import Entity
from .const import URL_SOLD, URL_INDEX_PERIOD, URL_PLATI

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    cookies = config.get("cookies")
    cod_client = config.get("cod_client")
    nr_contract = config.get("nr_contract")

    sensors = [
        ACIlfovSoldSensor(cookies, cod_client, nr_contract),
        ACIlfovIndexSensor(cookies, cod_client),
        ACIlfovLastPaymentSensor(cookies, cod_client)
    ]
    async_add_entities(sensors, True)

class ACIlfovBaseSensor(Entity):
    """Clasă de bază pentru senzori."""
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
        return {
            "Cookie": self._cookie,
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

class ACIlfovSoldSensor(ACIlfovBaseSensor):
    """Senzor Sold Curent."""
    @property
    def name(self): return "AC Ilfov Sold Curent"
    @property
    def unit_of_measurement(self): return "RON"

    async def async_update(self):
        url = f"{URL_SOLD}?codClient={self._cod}&nrContract=79" # Folosim contractul tau
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers) as resp:
                    if resp.status == 200:
                        self._state = float(await resp.text())
        except Exception as e: _LOGGER.error("Sold error: %s", e)

class ACIlfovIndexSensor(ACIlfovBaseSensor):
    """Senzor Perioadă Index."""
    @property
    def name(self): return "AC Ilfov Perioada Index"

    async def async_update(self):
        url = f"{URL_INDEX_PERIOD}?codClient={self._cod}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers) as resp:
                    data = await resp.json()
                    self._state = data.get("start")
                    self._attributes["mesaj"] = data.get("response")
        except Exception as e: _LOGGER.error("Index error: %s", e)

class ACIlfovLastPaymentSensor(ACIlfovBaseSensor):
    """Senzor Ultima Plată."""
    @property
    def name(self): return "AC Ilfov Ultima Plata"
    @property
    def unit_of_measurement(self): return "RON"

    async def async_update(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(URL_PLATI, headers=self._headers) as resp:
                    data = await resp.json()
                    if data["records"]:
                        last_row = data["records"][0]["row"]
                        self._state = last_row["valoarePlata"]
                        
                        # Conversie data din format /Date(ms)/
                        raw_date = last_row["dataPlata"]
                        ts = int(raw_date.replace("/Date(", "").replace(")/", "")) / 1000
                        self._attributes["data_plata"] = datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
                        self._attributes["document"] = last_row["documentPlata"]
                        self._attributes["metoda"] = last_row["canalIncasare"]
        except Exception as e: _LOGGER.error("Payment error: %s", e)