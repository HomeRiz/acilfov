"""Inițializarea integrării AC Ilfov."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Lista platformelor pe care le suportă integrarea (momentan doar senzori)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setează AC Ilfov dintr-un ConfigEntry (din interfața grafică)."""
    
    # Creăm spațiul de stocare în hass.data dacă nu există
    hass.data.setdefault(DOMAIN, {})
    
    # Salvăm datele (cookie-uri, cod client etc.) pentru a fi folosite de senzori
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Această linie trimite comanda către sensor.py să încarce entitățile
    # și le asociază automat cu acest Config Entry (pentru a apărea în UI)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Integrarea AC Ilfov a pornit cu succes pentru contul: %s", entry.title)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarcă integrarea (curățenie la ștergere sau restart)."""
    
    # Descarcă platformele (senzorii)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Dacă descărcarea a reușit, ștergem și datele din memorie
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unload_ok