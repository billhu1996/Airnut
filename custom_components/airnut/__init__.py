"""Airnut Platform"""

import logging
import datetime
import json
import select
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_IP,
    CONF_NIGHT_START_HOUR,
    CONF_NIGHT_END_HOUR,
    CONF_IS_NIGHT_UPDATE,
    ATTR_TEMPERATURE,
    ATTR_HUMIDITY,
    ATTR_PM25,
    ATTR_CO2,
    ATTR_TIME,
    DEFAULT_SCAN_INTERVAL,
    MOCK_WEATHER_DATA,
)

_LOGGER = logging.getLogger(__name__)

HOST_IP = "0.0.0.0"
ZERO_TIME = datetime.datetime.fromtimestamp(0)

ip_data_dict = {}
socket_ip_dict = {}


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up platform using YAML (legacy)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Airnut from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.warning("Setting up Airnut integration with IP: %s", entry.data.get(CONF_IP))

    # Use shared socket server if already exists
    if "server" in hass.data[DOMAIN] and hass.data[DOMAIN]["server"] is not None:
        _LOGGER.warning("Reusing existing shared socket server")
        server = hass.data[DOMAIN]["server"]
    else:
        night_start_hour = entry.data.get(CONF_NIGHT_START_HOUR, "22:00")
        night_end_hour = entry.data.get(CONF_NIGHT_END_HOUR, "08:00")
        is_night_update = entry.data.get(CONF_IS_NIGHT_UPDATE, True)

        server = AirnutSocketServer(
            night_start_hour, night_end_hour, is_night_update,
            datetime.timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        hass.data[DOMAIN]["server"] = server

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])

    # Only unload server if this is the last entry
    if DOMAIN in hass.data and "server" in hass.data[DOMAIN]:
        entries = hass.config_entries.async_entries(DOMAIN)
        if len(entries) <= 1:
            _LOGGER.warning("Last Airnut entry unloaded, shutting down socket server")
            await hass.async_add_executor_job(hass.data[DOMAIN]["server"].unload)
            del hass.data[DOMAIN]["server"]
        else:
            _LOGGER.warning("Other Airnut entries still active, keeping socket server")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


class AirnutSocketServer:

    def __init__(self, night_start_hour, night_end_hour, is_night_update, scan_interval):
        self._lastUpdateTime = ZERO_TIME
        self._night_start_hour = night_start_hour
        self._night_end_hour = night_end_hour
        self._is_night_update = is_night_update
        self._scan_interval = scan_interval
        self._bind_ok = False

        self._socketServer = socket(AF_INET, SOCK_STREAM)
        self._socketServer.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self._socketServer.settimeout(1.0)
        try:
            self._socketServer.bind((HOST_IP, 10511))
            self._socketServer.listen(5)
            self._bind_ok = True
        except OSError as e:
            _LOGGER.error("Socket server bind failed: %s", e)
            return

        global socket_ip_dict
        socket_ip_dict[self._socketServer] = HOST_IP

        _LOGGER.debug("socket Server loaded")

    def get_state(self):
        return "new"

    def object_to_json_data(self, object):
        return json.dumps(object).encode('utf-8') + b'\n\r'

    def json_string_to_object(self, data):
        try:
            return json.loads(data)
        except:
            return None

    def update(self):
        global socket_ip_dict
        if not self._bind_ok:
            _LOGGER.warning("Socket server not bound, skipping update")
            return True
        _LOGGER.warning("update() called, checking sockets... (clients: %d)", len(socket_ip_dict))

        read_sockets, write_sockets, error_sockets = select.select(list(socket_ip_dict.keys()), [], [], 0)

        self.deal_error_sockets(error_sockets)
        self.deal_read_sockets(read_sockets)

        now_time = datetime.datetime.now()
        if now_time - self._lastUpdateTime < self._scan_interval:
            return True

        self._lastUpdateTime = now_time

        now_time_str = datetime.datetime.now().strftime("%H%M")
        if isinstance(self._night_start_hour, str):
            night_start = self._night_start_hour
            night_end = self._night_end_hour
        else:
            night_start = self._night_start_hour.strftime("%H%M")
            night_end = self._night_end_hour.strftime("%H%M")

        if (self._is_night_update is False) and \
           (night_start <= now_time_str <= night_end or
            night_start > night_end and (now_time_str >= night_start or now_time_str <= night_end)):
            return True

        self.deal_write_sockets(list(socket_ip_dict.keys()))

        return True

    def deal_error_sockets(self, error_sockets):
        global socket_ip_dict
        for sock in error_sockets:
            try:
                sock.close()
            except Exception:
                pass
            if sock in socket_ip_dict:
                del socket_ip_dict[sock]

    def deal_read_sockets(self, read_sockets):
        volume_msg = {"sendback_appserver": 100000007, "param": {"volume": 0, "socket_id": 100000007, "check_key": "s_set_volume19085"}, "volume": 0, "p": "set_volume", "type": "control", "check_key": "s_set_volume19085"}
        check_msg = {"sendback_appserver": 100000007, "param": {"socket_id": 100000007, "type": 1, "check_key": "s_get19085"}, "p": "get", "type": "control", "check_key": "s_get19085"}
        weather_msg = MOCK_WEATHER_DATA
        global ip_data_dict
        for sock in read_sockets:
            if sock == self._socketServer:
                _LOGGER.warning("going to accept new connection")
                try:
                    sockfd, (host, _) = sock.accept()
                    socket_ip_dict[sockfd] = host
                    _LOGGER.warning("Client (%s) connected", socket_ip_dict[sockfd])
                    try:
                        sockfd.send(self.object_to_json_data(volume_msg))
                        sockfd.send(self.object_to_json_data(check_msg))
                    except OSError as e:
                        _LOGGER.error("Client error 1 %s", e)
                        sockfd.shutdown(2)
                        sockfd.close()
                        del socket_ip_dict[sockfd]
                        continue
    
                except OSError:
                    _LOGGER.warning("Client accept failed")
                    continue
            else:
                originData = None
                try:
                    originData = sock.recv(1024)
                    _LOGGER.warning("Receive originData %s", originData)
                except OSError as e:
                    _LOGGER.warning("Processing client error 2 %s", e)
                    continue
                if originData:
                    datas = originData.decode('utf-8').split("\n\r")
                    for singleData in datas:
                        jsonData = self.json_string_to_object(singleData)
                        if jsonData is None:
                            continue
                        p_value = jsonData.get("p")
                        if p_value == "log_in":
                            sock.send(self.object_to_json_data({"type": "client", "socket_id": 18567, "result": 0, "p": "log_in"}))
                            _LOGGER.warning("MCU login received, responded with login OK")
                        elif p_value == "post":
                            try:
                                ip_data_dict[socket_ip_dict[sock]] = {
                                    ATTR_PM25: int(jsonData["param"]["indoor"]["pm25"]),
                                    ATTR_TEMPERATURE: format(float(jsonData["param"]["indoor"]["t"]), '.1f'),
                                    ATTR_HUMIDITY: format(float(jsonData["param"]["indoor"]["h"]), '.1f'),
                                    ATTR_CO2: int(jsonData["param"]["indoor"]["co2"]),
                                    ATTR_TIME: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                }
                                _LOGGER.warning("ip_data_dict %s", ip_data_dict)
                            except (KeyError, ValueError) as e:
                                _LOGGER.warning("Failed to parse post data: %s", e)
                        elif p_value == "get_weather":
                            _LOGGER.warning("MCU requested weather data, sending mock response")
                            sock.send(self.object_to_json_data(weather_msg))
                        else:
                            _LOGGER.warning("Received unknown p='%s': %s", p_value, singleData[:100])

    def deal_write_sockets(self, write_sockets):
        global socket_ip_dict
        check_msg = {"sendback_appserver": 100000007, "param": {"socket_id": 100000007, "type": 1, "check_key": "s_get19085"}, "p": "get", "type": "control", "check_key": "s_get19085"}
        for sock in write_sockets:
            if sock == self._socketServer:
                continue
            try:
                sock.send(self.object_to_json_data(check_msg))
            except:
                try:
                    sock.close()
                except Exception:
                    pass
                if sock in socket_ip_dict:
                    del socket_ip_dict[sock]

    def get_data(self, ip):
        try:
            global ip_data_dict
            return ip_data_dict[ip]
        except:
            return {}

    def unload(self):
        """Signal shutdown of sock and clean up all resources."""
        _LOGGER.info("AirnutSensor Sock close")
        global socket_ip_dict

        # Close and clean up all client sockets
        for sock in list(socket_ip_dict.keys()):
            if sock != self._socketServer:
                try:
                    sock.close()
                except Exception:
                    pass
            if sock in socket_ip_dict:
                del socket_ip_dict[sock]

        # Close the server socket
        if self._bind_ok:
            try:
                self._socketServer.shutdown(2)
            except OSError:
                pass
            try:
                self._socketServer.close()
            except OSError:
                pass
            self._bind_ok = False

        _LOGGER.info("AirnutSensor Sock closed, all resources cleaned up")
