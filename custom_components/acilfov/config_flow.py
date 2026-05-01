import logging
import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema pentru formular: cere adresa de email și parola
DATA_SCHEMA = vol.Schema({
    vol.Required("email"): str,
    vol.Required("password"): str,
})

async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Aici vom face logarea reală pe site-ul AC Ilfov."""
    
    # --- ZONĂ INCOMPLETĂ ---
    # Aici trebuie să adăugăm apelul POST către URL-ul de login.
    # Avem nevoie să știm:
    # 1. URL-ul exact de autentificare.
    # 2. Cum trebuie trimise datele (ex: JSON sau Form-Data).
    # 3. Cum extragem cod_client și nr_contract din răspuns.
    
    # Vom ridica o eroare intenționat până primim datele de la F12
    raise ValueError("Lipsește logica de autentificare")

    # Structura finală pe care va trebui să o returnăm după logare:
    # return {
    #     "title": data["email"],
    #     "cookies": "cookie_extras_din_rasuns",
    #     "cod_client": "cod_extras_din_raspuns",
    #     "nr_contract": "contract_extras_din_raspuns"
    # }

class ACIlfovConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestionează fluxul de configurare pentru AC Ilfov în UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Primul pas: utilizatorul introduce datele."""
        errors = {}

        if user_input is not None:
            try:
                # Validăm datele (încercăm să ne logăm)
                info = await validate_input(self.hass, user_input)
                
                # Dacă logarea reușește, creăm integrarea
                return self.async_create_entry(title=info["title"], data=info)
            except ValueError:
                # Arată eroarea din strings.json (invalid_auth sau cannot_connect)
                errors["base"] = "invalid_auth" 
            except Exception:
                _LOGGER.exception("Eroare neașteptată la logare")
                errors["base"] = "unknown"

        # Afișăm formularul
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )