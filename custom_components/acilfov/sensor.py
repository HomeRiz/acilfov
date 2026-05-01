import logging
import async_timeout
import aiohttp
from homeassistant.helpers.entity import Entity
from .const import URL_SOLD, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    
    # AICI pui valorile copiate din browser
    # Formatul trebuie să fie: "NUME1=VALOARE1; NUME2=VALOARE2"
    my_cookies = "SELF_UTI_COOKIE=WXtaaMmMmLujphIUTjXANorvOJuURJAOjAFOsqHhRWWYsEinhXfOvetDLlab; sl-session=h0rNCaYw9mnrTknRgt4UBA=="
    
    # Datele identificate de tine în tab-ul Network
    cod_client = "37843"
    nr_contract = "79"
    
    async_add_entities([ACIlfovSensor(my_cookies, cod_client, nr_contract)], True)

class ACIlfovSensor(Entity):
    def __init__(self, cookie, cod, contract):
        self._cookie = cookie
        self._cod = cod
        self._contract = contract
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        return "AC Ilfov Sold Curent"

    @property
    def unit_of_measurement(self):
        return "RON"

    @property
    def icon(self):
        return "mdi:water-pump"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        """Preluare date de pe server."""
        headers = {
            "Cookie": self._cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }
        
        # Construim URL-ul cu parametrii de interogare
        url = f"{URL_SOLD}?codClient={self._cod}&nrContract={self._contract}"
        
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.text()
                            # Convertim textul primit (ex: "0" sau "150.5") în număr decimal
                            self._state = float(data)
                        elif response.status == 403:
                            _LOGGER.error("Eroare 403: Cloudflare a blocat cererea. Cookie-urile pot fi expirate.")
                        else:
                            _LOGGER.error("Eroare la accesare AC Ilfov (Status %s)", response.status)
        except Exception as e:
            _LOGGER.error("Eroare la update senzor AC Ilfov: %s", e)