""" Constants """
# Base component constants
DOMAIN = "airnut"
VERSION = "1.0.1"
ISSUE_URL = "https://github.com/billhu1996/Airnut/issues"
ATTRIBUTION = ""

# Configuration
ATTR_TEMPERATURE = "temperature"
ATTR_HUMIDITY = "humidity"
ATTR_PM25 = "pm25"
ATTR_CO2 = "co2"
ATTR_VOLUME = "volume"
ATTR_TIME = "time"

#Unit
MEASUREMENT_UNITE_DICT = {
    ATTR_TEMPERATURE: "°C",
    ATTR_HUMIDITY: "%",
    ATTR_PM25: "ug/m³",
    ATTR_CO2: "ppm",
}

# Defaults
DEFAULT_SCAN_INTERVAL = 600
