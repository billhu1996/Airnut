"""
Support for Airnut Air Detector M1 plant sensor.
Developer by billhu
192.168.123.4 apn.airnut.com
"""
import logging
import datetime
import json
import re
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
    """Set up the Airnut M1 sensor."""
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
    """Implementing the Airnut M1 sensor."""

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
        
    def objectToJsonData(self, object):
        return json.dumps(object).encode('utf-8')
    
    def jsonStringToObject(self, data):
        try:
            return json.loads(data)
        except:
            return None

    def update(self):
        """
        Update current conditions.
        """
        hour = datetime.datetime.now().hour
        if hour > 22 or hour < 7:
            return
        
        login_msg = {"type": "client", "socket_id": 19085, "result": 0, "p": "log_in"}
        check_msg = {"sendback_appserver": 100000007,"param": {"socket_id": 100000007,"type": 1,"check_key": "s_get19085"},"p": "get","type": "control","check_key": "s_get19085"}
        for sockA in self._connection_list:
            if sockA is self.sock:
                continue
            else:
                try:
                    sockA.send(self.objectToJsonData(check_msg))
                    # _LOGGER.info('AirnutSensor send a checkMessage to %s', sockA.getpeername())
                    break
                except OSError as e:
                    _LOGGER.warning(
                        "AirnutSensor Force send a heartbeat got %s. Closing socket", e)
                    try:
                        sockA.shutdown(2)
                        sockA.close()
                    except OSError:
                        pass
                    self._connection_list.remove(sockA)
                    continue
        read_sockets, write_sockets, error_sockets = select.select(self._connection_list, [], [], 0)
        if len(self._connection_list) == 1:
            self.iClientEmptyLogCount += 1
            if self.iClientEmptyLogCount == 13:
                _LOGGER.warning("AirnutSensor Client list is empty")
                self.iClientEmptyLogCount = 0
                return None
        else:
            self.iClientEmptyLogCount = 0

        volume_state = 0
        volume = self._hass.states.get('input_number.airnut_1s_volume')
        if volume is not None:
            volume_state = min(max(int(float(volume.state)), 0), 100)
        if self._state_attrs[ATTR_VOLUME] != volume_state:
            send_msg = {"sendback_appserver": 100000007,"param": {"volume": volume_state,"socket_id": 100000007,"check_key": "s_set_volume19085"},"volume": volume_state,"p": "set_volume","type": "control","check_key": "s_set_volume19085"}
        else:
            send_msg = None
        volume_msg = {"sendback_appserver": 100000007,"param": {"volume": 0,"socket_id": 100000007,"check_key": "s_set_volume19085"},"volume": 0,"p": "set_volume","type": "control","check_key": "s_set_volume19085"}

        for sock in read_sockets:
            if sock is self.sock:
                _LOGGER.warning(
                    "AirnutSensor going to accept new connection")
                try:
                    sockfd, addr = self.sock.accept()
                    sockfd.settimeout(5)
                    self._connection_list.append(sockfd)
                    _LOGGER.warning("AirnutSensor Client (%s, %s) connected" % addr)
                    try:
                        # _LOGGER.warning("AirnutSensor 1")
                        # sockfd.send(self.objectToJsonData(login_msg))
                        _LOGGER.warning("AirnutSensor 2")
                        sockfd.send(self.objectToJsonData(volume_msg))
                        sockfd.send(self.objectToJsonData(check_msg))
                        _LOGGER.warning("AirnutSensor 3")
                        # _LOGGER.info('AirnutSensor send a checkMessage to %s', sockA.getpeername())
                    except OSError as e:
                        _LOGGER.warning("AirnutSensor Client error 1 %s", e)
                        sock.shutdown(2)
                        sock.close()
                        self._connection_list.remove(sockfd)
                        continue
                except OSError:
                    _LOGGER.warning("AirnutSensor Client accept failed")
                    continue
            else:
                data = None
                try:
                    # _LOGGER.debug("AirnutSensor Processing Client %s", sock.getpeername())
                    data = sock.recv(1024)
                    _LOGGER.debug("AirnutSensor Receive data %s", data)                    
                except OSError as e:
                    _LOGGER.warning("AirnutSensor Processing Client error 2 %s", e)
                    continue
#                if send_msg is not None:
#                    try:
#                        self.sock.send(self.objectToJsonData(send_msg))
#                    except OSError as e:
#                        _LOGGER.warning("AirnutSensor Client error 3 %s", e)
#                        sock.shutdown(2)
#                        sock.close()
#                        self._connection_list.remove(sock)
#                        continue
                if data:
                    datas = data.decode('utf-8').split("\n\r")
                    for singleData in datas:
                        jsonData = self.jsonStringToObject(singleData)
                        if jsonData is not None and jsonData["p"] == "post":
                            self._state_attrs = {
                                ATTR_PM25: int(jsonData["param"]["indoor"]["pm25"]),
                                ATTR_TEMPERATURE: format(float(jsonData["param"]["indoor"]["t"]), '.1f'),
                                ATTR_HUMIDITY: format(float(jsonData["param"]["indoor"]["h"]), '.1f'),
                                ATTR_CO2: int(jsonData["param"]["indoor"]["co2"]),
    #                            ATTR_HCHO: format(float(jsonData['hcho']) / 1000, '.2f'),
                                ATTR_VOLUME: volume_state,
                                ATTR_TIME: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
#                else:
#                    _LOGGER.warning("AirnutSensor Client offline, closing")
#                    sock.shutdown(2)
#                    sock.close()
#                    self._connection_list.remove(sock)
#                    continue
