import logging
import async_timeout
import aiohttp
import calendar
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity, DeviceInfo
from .const import DOMAIN, URL_SOLD, URL_INDEX_PERIOD, URL_PLATI, URL_CONTRACT, URL_TRANSMITERE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setarea platformei de senzori prin Config Flow."""
    
    cookies = config_entry.data.get("cookies")
    cod_client = config_entry.data.get("cod_client")
    nr_contract = config_entry.data.get("nr_contract")

    if not cookies or not cod_client:
        _LOGGER.error("Date de configurare lipsă pentru AC Ilfov")
        return

    sensors = [
        ACIlfovSoldSensor(cookies, cod_client, nr_contract),
        ACIlfovIndexSensor(cookies, cod_client),
        ACIlfovContractSensor(cookies, cod_client, nr_contract),
        ACIlfovLastPaymentSensor(cookies, cod_client, nr_contract),
        ACIlfovUltimulIndexSensor(cookies, cod_client, nr_contract)
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
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._cod)},
            name=f"Cont AC Ilfov ({self._cod})",
            manufacturer="Apa Canal Ilfov",
            model="Portal Client EMSYS",
            sw_version="1.2.0",
        )

    @property
    def _headers(self):
        return {
            "Cookie": self._cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*"
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
    def unique_id(self): return f"acilfov_perioada_index_{self._cod}"
    @property
    def icon(self): return "mdi:calendar-clock"

    async def async_update(self):
        url = f"{URL_INDEX_PERIOD}?codClient={self._cod}"
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.get(url, headers=self._headers) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            self._state = data.get("start", "Inactiv")
                            self._attributes["mesaj"] = data.get("response", "")
        except Exception as e: _LOGGER.error("Eroare Perioada Index: %s", e)

class ACIlfovContractSensor(ACIlfovBaseSensor):
    def __init__(self, cookie, cod, contract):
        super().__init__(cookie, cod)
        self._contract = contract

    @property
    def name(self): return "AC Ilfov Detalii Contract"
    @property
    def unique_id(self): return f"acilfov_contract_{self._cod}"
    @property
    def icon(self): return "mdi:file-document-outline"

    async def async_update(self):
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.get(URL_CONTRACT, headers=self._headers) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if data and isinstance(data, list) and len(data) > 0:
                                contract_data = data[0]
                                self._state = contract_data.get("stareContract", "Necunoscut")
                                self._attributes["client"] = contract_data.get("denClient")
                                self._attributes["adresa"] = contract_data.get("adrClient")
                                
                                self._attributes["cod_client"] = self._cod
                                self._attributes["numar_contract"] = self._contract
                                self._attributes["id_contract_sistem"] = contract_data.get("idContract", "")
                                
                                raw_date = contract_data.get("dataIncContract", "")
                                if raw_date and "/Date(" in raw_date:
                                    ts = int(raw_date.replace("/Date(", "").replace(")/", "")) / 1000
                                    self._attributes["data_inceput"] = datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
        except Exception as e: _LOGGER.error("Eroare conexiune Contract: %s", e)

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
        url = URL_PLATI
        now = datetime.utcnow()
        start_date = now - timedelta(days=180)
        date_format = '%a, %d %b %Y %H:%M:%S GMT'
        
        headers = self._headers.copy()
        headers.update({
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "codclient": str(self._cod),
            "nrcontract": str(self._contract),
            "startdate": start_date.strftime(date_format),
            "enddate": now.strftime(date_format)
        })

        payload = {
            "$qd": "false", "$action": "LOAD_RECORDS",
            "$locale": "en", "$ls": "false",
            "$to": "500", "$order": "DATA_PLATA desc"
        }

        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.post(url, headers=headers, data=payload) as resp:
                        if resp.status == 200:
                            await self._parse_data(await resp.json(content_type=None))
        except Exception as e: 
            _LOGGER.error("Eroare conexiune Plata: %s", e)

    async def _parse_data(self, data):
        if data and data.get("records") and len(data["records"]) > 0:
            last_row = data["records"][0].get("row", {})
            self._state = last_row.get("valoarePlata")
            
            raw_date = last_row.get("dataPlata", "")
            if "/Date(" in raw_date:
                ts = int(raw_date.replace("/Date(", "").replace(")/", "")) / 1000
                self._attributes["data_plata"] = datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
            
            self._attributes["document"] = last_row.get("documentPlata")
            self._attributes["metoda"] = last_row.get("canalIncasare")

class ACIlfovUltimulIndexSensor(ACIlfovBaseSensor):
    def __init__(self, cookie, cod, contract):
        super().__init__(cookie, cod)
        self._contract = contract

    @property
    def name(self): return "AC Ilfov Ultimul Index"
    @property
    def unique_id(self): return f"acilfov_ultimul_index_{self._cod}"
    
    @property
    def unit_of_measurement(self): 
        # Afișăm m³ doar dacă avem un număr valid (nu text de eroare)
        return "m³" if isinstance(self._state, (int, float)) else None
        
    @property
    def icon(self): return "mdi:counter"

    async def async_update(self):
        url = URL_TRANSMITERE
        headers = self._headers.copy()
        headers.update({
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "codclient": str(self._cod),
            "nrcontract": str(self._contract)
        })

        payload = {
            "$qd": "false", "$action": "LOAD_RECORDS",
            "$locale": "en", "$ls": "false", "$to": "500"
        }

        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.post(url, headers=headers, data=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if data and data.get("records") and len(data["records"]) > 0:
                                row = data["records"][0].get("row", {})
                                
                                idx = row.get("indexVechi")
                                self._state = idx if idx is not None else 0
                                
                                self._attributes["serie_contor"] = row.get("contor", "Necunoscut")
                                self._attributes["id_contor_instalat"] = row.get("idContorInstalat", "")
                                
                                now = datetime.now()
                                try:
                                    zi_inc = int(row.get("ziInc", 25))
                                except (ValueError, TypeError):
                                    zi_inc = 25
                                    
                                _, last_day = calendar.monthrange(now.year, now.month)
                                self._attributes["zi_deschidere"] = zi_inc
                                self._attributes["zi_inchidere"] = last_day
                                
                                if now.day < zi_inc:
                                    zile_pana_deschidere = zi_inc - now.day
                                    self._attributes["status_fereastra"] = f"Închisă (se deschide în {zile_pana_deschidere} zile)"
                                    self._attributes["zile_ramase"] = 0
                                else:
                                    zile_ramase = (last_day - now.day) + 1
                                    self._attributes["status_fereastra"] = "Deschisă (Poți trimite indexul)"
                                    self._attributes["zile_ramase"] = zile_ramase
                            else:
                                self._state = "Fără istoric"
                                self._attributes["status_fereastra"] = "Nu s-au găsit date"
                        else:
                            self._state = "Eroare API"
        except Exception as e:
            _LOGGER.error("Eroare Ultimul Index: %s", e)
            self._state = "Eroare Conexiune"