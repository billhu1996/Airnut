""" Constants """
# Base component constants
DOMAIN = "airnut"
VERSION = "2.1.0"
ISSUE_URL = "https://github.com/billhu1996/Airnut/issues"
ATTRIBUTION = ""

# Configuration
CONF_IP = "ip"
CONF_NIGHT_START_HOUR = "night_start_hour"
CONF_NIGHT_END_HOUR = "night_end_hour"
CONF_IS_NIGHT_UPDATE = "is_night_update"

ATTR_TEMPERATURE = "temperature"
ATTR_HUMIDITY = "humidity"
ATTR_PM25 = "pm25"
ATTR_CO2 = "co2"
ATTR_VOLUME = "volume"
ATTR_TIME = "time"

# Unit
MEASUREMENT_UNITE_DICT = {
    ATTR_TEMPERATURE: "°C",
    ATTR_HUMIDITY: "%",
    ATTR_PM25: "ug/m³",
    ATTR_CO2: "ppm",
}

SENSOR_TYPES = [ATTR_TEMPERATURE, ATTR_HUMIDITY, ATTR_PM25, ATTR_CO2]

# Defaults
DEFAULT_SCAN_INTERVAL = 600
DEFAULT_NIGHT_START_HOUR = "22:00"
DEFAULT_NIGHT_END_HOUR = "08:00"
DEFAULT_IS_NIGHT_UPDATE = True

# Weather mock data
# Weather codes map to voice files on SD card:
# 0=sunny, 1=cloudy, 2=overcast, 3=shower, 4=thunder_shower,
# 5=hail, 6=sleet, 7=rain, 8=snow, 9=fog, 10=haze
MOCK_WEATHER_DATA = {
    "p": "get_weather",
    "city": "深圳",
    "weather_d": 0,
    "weather_n": 1,
    "d_w_l": 1,
    "d_w_d": "晴",
    "n_w_l": 2,
    "n_w_d": "多云",
    "lunar": "初一",
    "is_day": 1,
}
