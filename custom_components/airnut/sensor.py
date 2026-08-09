"""
Support for Airnut 1S plant sensor.
Developer by billhu
192.168.123.4 apn.airnut.com
"""
import logging
import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    CONF_IP,
    ATTR_TEMPERATURE,
    ATTR_HUMIDITY,
    ATTR_PM25,
    ATTR_CO2,
    ATTR_TIME,
    MEASUREMENT_UNITE_DICT,
    SENSOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensor platform."""
    server = hass.data[DOMAIN]["server"]
    ip = entry.data[CONF_IP]

    entities = []
    for sensor_type in SENSOR_TYPES:
        entities.append(AirnutSensor(entry, server, ip, sensor_type))

    async_add_entities(entities, update_before_add=True)


class AirnutSensor(SensorEntity):
    """Implementing the Airnut 1S sensor."""

    _attr_should_poll = True

    def __init__(self, config_entry, server, ip, sensor_type):
        """Initialize the sensor."""
        self.config_entry = config_entry
        self._server = server
        self._ip = ip
        self._sensor_type = sensor_type

        ip_clean = ip.replace(".", "_")
        self._attr_unique_id = f"airnut_{ip_clean}_{sensor_type}"
        self._attr_translation_key = sensor_type
        self._attr_has_entity_name = True
        self._attr_native_unit_of_measurement = MEASUREMENT_UNITE_DICT[sensor_type]
        self._attr_native_value = None
        self._attr_extra_state_attributes = {
            sensor_type: None,
            ATTR_TIME: None,
        }
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, ip_clean)},
            name=f"Airnut 1S ({ip})",
            manufacturer="Airnut",
            model="1S",
        )

    async def async_update(self):
        """Update the sensor data."""
        await self.hass.async_add_executor_job(self._server.update)
        try:
            data = self._server.get_data(self._ip)
            self._attr_native_value = data[self._sensor_type]
            self._attr_extra_state_attributes[self._sensor_type] = self._attr_native_value
            self._attr_extra_state_attributes[ATTR_TIME] = data[ATTR_TIME]
        except Exception:
            _LOGGER.info("AirnutSensor get data error with ip %s", self._ip)
            return
