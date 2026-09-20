"""Constants for the VENTS Breezy integration."""

from datetime import timedelta

DOMAIN = "vents_breezy"

CARD_URL = "/vents_breezy/vents-breezy-card.js"
CARD_VERSION = "0.2.0"

DEFAULT_NAME = "VENTS Breezy 160-E"
DEFAULT_PASSWORD = "1111"
DEFAULT_PORT = 4000
UPDATE_INTERVAL = timedelta(seconds=30)

PRESET_NIGHT = "night"
PRESET_TURBO = "turbo"
PRESET_MODES = [PRESET_NIGHT, PRESET_TURBO]

AIRFLOW_MODES = ["ventilation", "heat_recovery", "air_supply", "extract"]
