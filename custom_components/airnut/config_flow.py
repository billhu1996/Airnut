import re
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN,
    CONF_IP,
    CONF_NIGHT_START_HOUR,
    CONF_NIGHT_END_HOUR,
    CONF_IS_NIGHT_UPDATE,
    DEFAULT_NIGHT_START_HOUR,
    DEFAULT_NIGHT_END_HOUR,
    DEFAULT_IS_NIGHT_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

IP_REGEX = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')


def _build_schema(defaults=None):
    """Build the data/options schema with optional defaults."""
    return vol.Schema({
        vol.Required(CONF_IP, default=defaults.get(CONF_IP, "") if defaults else ""): str,
        vol.Optional(CONF_NIGHT_START_HOUR, default=defaults.get(CONF_NIGHT_START_HOUR, DEFAULT_NIGHT_START_HOUR) if defaults else DEFAULT_NIGHT_START_HOUR): str,
        vol.Optional(CONF_NIGHT_END_HOUR, default=defaults.get(CONF_NIGHT_END_HOUR, DEFAULT_NIGHT_END_HOUR) if defaults else DEFAULT_NIGHT_END_HOUR): str,
        vol.Optional(CONF_IS_NIGHT_UPDATE, default=defaults.get(CONF_IS_NIGHT_UPDATE, DEFAULT_IS_NIGHT_UPDATE) if defaults else DEFAULT_IS_NIGHT_UPDATE): bool,
    })


class AirnutConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                ip = user_input[CONF_IP]
                if IP_REGEX.match(ip):
                    await self.async_set_unique_id(f"airnut_{ip.replace('.', '_')}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Airnut {ip}",
                        data=user_input,
                    )
                else:
                    errors[CONF_IP] = "invalid_ip"
            except config_entries.AlreadyConfigured:
                errors["base"] = "already_configured"
            except Exception as e:
                _LOGGER.error("Config flow error: %s", e)
                errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                ip = user_input[CONF_IP]
                if IP_REGEX.match(ip):
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data=user_input,
                    )
                    return self.async_create_entry(
                        title=f"Airnut {ip}",
                        data=user_input,
                    )
                else:
                    errors[CONF_IP] = "invalid_ip"
            except Exception as e:
                _LOGGER.error("Reconfigure flow error: %s", e)
                errors["base"] = "unknown_error"

        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_build_schema(current_data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AirnutOptionsFlow()


class AirnutOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                ip = user_input[CONF_IP]
                if IP_REGEX.match(ip):
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data=user_input,
                    )
                    return self.async_create_entry(title="", data={})
                else:
                    errors[CONF_IP] = "invalid_ip"
            except Exception as e:
                _LOGGER.error("Options flow error: %s", e)
                errors["base"] = "unknown_error"

        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(current_data),
            errors=errors,
        )
