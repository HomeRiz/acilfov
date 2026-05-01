"""Inițializarea integrării AC Ilfov."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setează AC Ilfov dintr-un ConfigEntry (din interfața grafică)."""
    hass.data.setdefault(DOMAIN, {})
    
    # Salvăm datele (cookie-uri, cod client etc.) în memoria HA pentru a fi folosite de senzori
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Încărcăm fișierul sensor.py
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Integrarea AC Ilfov a pornit cu succes!")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarcă integrarea dacă utilizatorul o șterge din interfață."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok