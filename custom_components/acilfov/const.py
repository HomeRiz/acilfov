"""Constante pentru integrarea AC Ilfov."""

DOMAIN = "acilfov"
BASE_URL = "https://acilfov.emsys.ro/self_utilities/rest/self"

URL_SOLD = f"{BASE_URL}/facturi/getSoldClient"
URL_INDEX_PERIOD = f"{BASE_URL}/transmitere/verificaPerioada"
URL_PLATI = f"{BASE_URL}/plati/Platis"
URL_CONTRACT = f"{BASE_URL}/contract/getListaCodClientContracte"
URL_TRANSMITERE = f"{BASE_URL}/transmitere/Transmiteres"