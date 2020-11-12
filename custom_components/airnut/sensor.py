"""
Support for Airnut 1S plant sensor.
Developer by billhu
192.168.123.4 apn.airnut.com
"""
import logging
import datetime
import json
import select
import voluptuous as vol
from socket import socket, AF_INET, SOCK_STREAM
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_NAME)


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = datetime.timedelta(seconds=600)
DEFAULT_NAME = 'Airnut 1S'

ATTR_TEMPERATURE = 'temperature'
ATTR_HUMIDITY = 'humidity'
ATTR_PM25 = 'pm25'
ATTR_CO2 = 'co2'
ATTR_HCHO = 'hcho'
ATTR_VOLUME = 'volume'
ATTR_TIME = 'time'
CONNECTION_LIST = []

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Airnut 1S sensor."""
    _LOGGER.info("AirnutSensor setup_platform")

    name = config.get(CONF_NAME)
    connection_list = CONNECTION_LIST
    sock = socket(AF_INET, SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.bind(("0.0.0.0", 10511))
        sock.listen(5)
    except OSError as e:
        _LOGGER.warning("AirnutSensor server got %s", e)
        pass

    connection_list.append(sock)
    _LOGGER.warning("AirnutSensor server started on port 10511")

    devs = []

    devs.append(AirnutSensor(
        hass, connection_list, sock, name))

    add_devices(devs)


class AirnutSensor(Entity):
    """Implementing the Airnut 1S sensor."""

    def __init__(self, hass, connection_list, sock, name):
        """Initialize the sensor."""
        _LOGGER.info("AirnutSensor __init__")
        self.iClientEmptyLogCount = 0
        self._hass = hass
        self._connection_list = connection_list
        self.sock = sock
        self._name = name
        self._state = None
        self.data = []
        self._state_attrs = {
            ATTR_PM25: None,
            ATTR_TEMPERATURE: None,
            ATTR_HUMIDITY: None,
            ATTR_CO2: None,
            ATTR_HCHO: None,
            ATTR_VOLUME: 0,
        }
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state_attrs[ATTR_CO2]

    @property
    def state_attributes(self):
        """Return the state of the sensor."""
        return self._state_attrs

    def shutdown(self, event):
        """Signal shutdown of sock."""
        _LOGGER.debug("AirnutSensor Sock close")
        self.sock.shutdown(2)
        self.sock.close()

    def update(self):
        """Update current conditions."""
