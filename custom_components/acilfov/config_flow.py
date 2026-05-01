"""Config flow pentru integrarea AC Ilfov."""
import logging
import voluptuous as vol
import aiohttp
import async_timeout

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, BASE_URL

_LOGGER = logging.getLogger(__name__)

# URL-ul exact de login extras de tine
LOGIN_URL = "https://acilfov.emsys.ro/self_utilities/login"
# URL-ul folosit automat de site dupa login pentru a afla contractul
CONTRACTS_URL = f"{BASE_URL}/contract/getListaCodClientContracte"

DATA_SCHEMA = vol.Schema({
    vol.Required("email"): str,
    vol.Required("password"): str,
})

async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validează datele de login și extrage cookie-ul și detaliile clientului."""
    email = data["email"]
    password = data["password"]

    # 1. Pregătim datele pentru trimitere, formatate cum a arătat Payload-ul tau
    payload = {
        "j_username": email,
        "j_password": password
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        # Folosim CookieJar pentru a stoca automat cookie-urile returnate (ex: SELF_UTI_COOKIE)
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as session:
            with async_timeout.timeout(15):
                # Pasul 1: Facem cererea de logare.
                # Allow_redirects=False deoarece ai vazut acel 302 Found. Vrem să prindem răspunsul înainte să ne mute paginile.
                async with session.post(LOGIN_URL, headers=headers, data=payload, allow_redirects=False) as resp:
                    
                    # Verificăm dacă logarea a reușit
                    # Un login invalid returnează 200 (reîncarcă pagina de login cu o eroare).
                    # Un login valid returnează 302 (redirect către cont).
                    if resp.status != 302:
                        _LOGGER.error("Logare eșuată. Status primit: %s", resp.status)
                        raise ValueError("invalid_auth")

            # Extragem cookie-urile rezultate în urma logării
            cookies_dict = session.cookie_jar.filter_cookies(LOGIN_URL)
            cookie_string = "; ".join([f"{key}={morsel.value}" for key, morsel in cookies_dict.items()])
            
            if not cookie_string:
               raise ValueError("Nu s-au putut prelua cookie-urile de sesiune.")

            # Setăm headerul cu noul cookie pentru cererea următoare
            headers["Cookie"] = cookie_string
            # Trebuie să modificăm Content-Type-ul înapoi în ceva standard pentru API-uri
            headers["Accept"] = "application/json, text/plain, */*"

            # Pasul 2: Aflăm codul de client și contractul.
            # Acum că suntem logați, apelăm direct lista de contracte (exact cum face și site-ul)
            with async_timeout.timeout(15):
                async with session.get(CONTRACTS_URL, headers=headers) as resp_contract:
                    if resp_contract.status != 200:
                         raise ValueError(f"Eroare extragere contract: {resp_contract.status}")
                    
                    contracte_data = await resp_contract.json()
                    
                    if not contracte_data or len(contracte_data) == 0:
                         raise ValueError("Nu s-au găsit contracte asociate acestui cont.")
                    
                    # Extragem primul contract găsit
                    cod_client = str(contracte_data[0].get("codClient"))
                    nr_contract = str(contracte_data[0].get("nrContract"))

                    # Returnăm datele structurate frumos pentru a fi salvate în Home Assistant
                    return {
                        "title": email,
                        "cookies": cookie_string,
                        "cod_client": cod_client,
                        "nr_contract": nr_contract
                    }

    except aiohttp.ClientError as err:
        _LOGGER.error("Eroare de conexiune la logare: %s", err)
        raise ConnectionError("cannot_connect")
    except ValueError as val_err:
        raise val_err # Rethrow pentru erorile noastre specifice
    except Exception as exc:
        _LOGGER.error("Eroare neprevăzută la logare: %s", exc)
        raise Exception("unknown")

class ACIlfovConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestionează fluxul de configurare pentru AC Ilfov în UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Primul pas: utilizatorul introduce datele."""
        errors = {}

        if user_input is not None:
            # Verificăm dacă contul a mai fost adăugat (să nu avem duplicate)
            await self.async_set_unique_id(user_input["email"])
            self._abort_if_unique_id_configured()

            try:
                # Încercăm să validăm credențialele
                info = await validate_input(self.hass, user_input)
                
                # Dacă logarea reușește, creăm integrarea
                return self.async_create_entry(title=info["title"], data=info)
            except ValueError as err:
                errors["base"] = str(err) 
            except ConnectionError:
                 errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        # Afișăm formularul
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )