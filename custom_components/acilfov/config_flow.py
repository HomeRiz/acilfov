"""Config flow pentru integrarea AC Ilfov."""
import logging
import voluptuous as vol
import aiohttp
import async_timeout

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, BASE_URL

_LOGGER = logging.getLogger(__name__)

URL_CONTRACT = f"{BASE_URL}/contract/getListaCodClientContracte"

# Schema cere acum Cookie, Cod și Contract (în loc de Email/Parolă)
DATA_SCHEMA = vol.Schema({
    vol.Required("cookies"): str,
    vol.Required("cod_client"): str,
    vol.Required("nr_contract"): str,
})

async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validează datele verificând dacă putem accesa API-ul cu acest cookie."""
    headers = {
        "Cookie": data["cookies"],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    try:
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(15):
                # Facem un apel de test către lista de contracte folosind cookie-ul tău
                async with session.get(URL_CONTRACT, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Eroare la validare cookie. Status: %s", resp.status)
                        raise ValueError("invalid_auth")

                    contracte_data = await resp.json()
                    
                    if not contracte_data or len(contracte_data) == 0:
                        raise ValueError("invalid_auth")

                    # Extragem numele clientului pentru a-l pune frumos ca titlu în HA
                    client_name = contracte_data[0].get("denClient", "Client AC Ilfov")
                    
                    return {
                        "title": f"{client_name} ({data['cod_client']})",
                        "cookies": data["cookies"],
                        "cod_client": data["cod_client"],
                        "nr_contract": data["nr_contract"]
                    }

    except aiohttp.ClientError:
        raise ConnectionError("cannot_connect")
    except ValueError as val_err:
        raise val_err
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
            # Setează ID-ul unic pe baza codului de client
            await self.async_set_unique_id(user_input["cod_client"])
            self._abort_if_unique_id_configured()

            try:
                # Testează cookie-ul
                info = await validate_input(self.hass, user_input)
                
                # Crează integrarea!
                return self.async_create_entry(title=info["title"], data=info)
            except ValueError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        # Afișăm formularul cu cele 3 câmpuri
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )