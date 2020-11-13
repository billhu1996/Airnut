"""Airnut Platform"""

import logging
import datetime
import json
import select
import voluptuous as vol
from socket import socket, AF_INET, SOCK_STREAM

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_SCAN_INTERVAL,
)

from .const import (
    DOMAIN,
    ATTR_TEMPERATURE,
    ATTR_HUMIDITY,
    ATTR_PM25,
    ATTR_CO2,
    ATTR_VOLUME,
    ATTR_TIME,
)

CONF_NIGHT_START_HOUR = "night_start_hour"
CONF_NIGHT_END_HOUR = "night_end_hour"
CONF_NIGHT_UPDATE = "night_update"
HOST_IP = "0.0.0.0"

SCAN_INTERVAL = datetime.timedelta(seconds=600)
ZERO_TIME = datetime.datetime.fromtimestamp(0)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_NIGHT_START_HOUR, default=ZERO_TIME): cv.datetime,
                vol.Optional(CONF_NIGHT_END_HOUR, default=ZERO_TIME): cv.datetime,
                vol.Optional(CONF_NIGHT_UPDATE, default=True): cv.boolean,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)

ip_data_dict = {}
socket_ip_dict = {}

def setup(hass, config):
    """Set up platform using YAML."""
    night_start_hour = config[DOMAIN].get(CONF_NIGHT_START_HOUR)
    night_end_hour = config[DOMAIN].get(CONF_NIGHT_END_HOUR)
    is_night_update = config[DOMAIN].get(CONF_NIGHT_UPDATE)
    scan_interval = config[DOMAIN].get(CONF_SCAN_INTERVAL)
    
    server =  AirnutSocketServer(night_start_hour, night_end_hour, is_night_update, scan_interval)

    hass.data[DOMAIN] = {
        'server': server
    }
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")

class AirnutSocketServer:

    def __init__(self, night_start_hour, night_end_hour, is_night_update, scan_interval):
        self._lastUpdateTime = ZERO_TIME
        self.night_start_hour = night_start_hour.strftime("%H%M%S")
        self.night_end_hour = night_end_hour.strftime("%H%M%S")
        self.is_night_update = is_night_update
        self.scan_interval = scan_interval

        socketServer = socket(AF_INET, SOCK_STREAM)
        socketServer.settimeout(5)
        try:
            socketServer.bind((HOST_IP, 10511))
            socketServer.listen(5)
        except OSError as e:
            _LOGGER.error("server got %s", e)
            pass

        global socket_ip_dict
        socket_ip_dict[socketServer] = HOST_IP

        _LOGGER.debug("socket Server loaded")
        self.update()

    def get_state(self):
        return "new"

    def object_to_json_data(self, object):
        return json.dumps(object).encode('utf-8')

    def json_string_to_object(self, data):
        try:
            return json.loads(data)
        except:
            return None

    def update(self):
        global socket_ip_dict

        read_sockets, write_sockets, error_sockets = select.select(socket_ip_dict.keys(), [], [], 0)

        self.deal_error_sockets(error_sockets)
        self.deal_read_sockets(read_sockets)

        now_time = datetime.datetime.now()
        if now_time - self._lastUpdateTime > self.scan_interval:
            return

        now_time_str = datetime.datetime.now().strftime("%H%M%S")
        if ((self.is_night_update is True) and
            (self.night_start_hour < now_time_str or self.night_end_hour > now_time_str)):
            return

        self.deal_write_sockets(write_sockets)

        return True
    
    def deal_error_sockets(self, error_sockets):
        global socket_ip_dict
        for sock in error_sockets:
            del socket_ip_dict[sock]
    
    def deal_read_sockets(self, read_sockets):
        volume_msg = {"sendback_appserver": 100000007,"param": {"volume": 0,"socket_id": 100000007,"check_key": "s_set_volume19085"},"volume": 0,"p": "set_volume","type": "control","check_key": "s_set_volume19085"}
        check_msg = {"sendback_appserver": 100000007,"param": {"socket_id": 100000007,"type": 1,"check_key": "s_get19085"},"p": "get","type": "control","check_key": "s_get19085"}
        for sock in read_sockets:
            if socket_ip_dict[sock] == HOST_IP:
                _LOGGER.info("going to accept new connection")
                try:
                    sockfd, addr = self.sock.accept()
                    sockfd.settimeout(5)
                    socket_ip_dict[sockfd] = addr
                    _LOGGER.info("Client (%s) connected", addr)
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
                    _LOGGER.debug("Receive originData %s", originData)
                except OSError as e:
                    _LOGGER.warning("Processing Client error 2 %s", e)
                    continue
                if originData:
                    datas = originData.decode('utf-8').split("\n\r")
                    for singleData in datas:
                        jsonData = self.json_string_to_object(singleData)
                        if (jsonData is not None and
                            jsonData["p"] == "post"):
                            global ip_data_dict
                            ip_data_dict[socket_ip_dict[sock]] = {
                                ATTR_PM25: int(jsonData["param"]["indoor"]["pm25"]),
                                ATTR_TEMPERATURE: format(float(jsonData["param"]["indoor"]["t"]), '.1f'),
                                ATTR_HUMIDITY: format(float(jsonData["param"]["indoor"]["h"]), '.1f'),
                                ATTR_CO2: int(jsonData["param"]["indoor"]["co2"]),
                                ATTR_TIME: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }

    def deal_write_sockets(self, write_sockets):
        global socket_ip_dict
        check_msg = {"sendback_appserver": 100000007,"param": {"socket_id": 100000007,"type": 1,"check_key": "s_get19085"},"p": "get","type": "control","check_key": "s_get19085"}
        for sock in write_sockets:
            if socket_ip_dict[sock] == HOST_IP:
                continue
            sockfd.send(self.object_to_json_data(check_msg))


    def get_data(self, ip):
        try:
            global ip_data_dict
            return ip_data_dict[ip]
        except:
            return {}
