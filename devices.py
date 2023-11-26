import socket

import paho.mqtt.client as mqtt
import logging
import time


class PlugDevice:
    def __init__(self, mqtt_user: str,
                 mqtt_password: str,
                 mqtt_broker: str,
                 mqtt_device_id: str,
                 mqtt_port: int = 1883,
                 mqtt_keepalive: int = 60,
                 mqtt_retain: bool = False,
                 mqtt_qos: int = 0):
        """
        Creates a plug device with an MQTT client to control a Shelly 1 Plug
        :param mqtt_user:
        :param mqtt_password:
        :param mqtt_broker: broker IP address
        :param mqtt_device_id: Shelly 1 Plug Id
        :param mqtt_port: default 1883
        """
        self.mqtt_user = mqtt_user
        self.mqtt_pwd = mqtt_password
        self.mqtt_broker_url = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_device_id = mqtt_device_id
        self.mqtt_keepalive = mqtt_keepalive
        self.mqtt_retain = mqtt_retain
        self._mqtt_qos = mqtt_qos
        self.temperature = None
        self.state = None
        self.power = None
        self._log_interval = 300
        self._subscription_tstamps = {}
        self._last_connect_rc = None
        self.mqtt_client = mqtt.Client('plug_controller')
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self._logger = logging.getLogger(__name__)

    def connect(self) -> int:
        """
        Connects the plug device to the MQTT broker. In case of error, description is logged to main logger.
        It only needs to be called once
        :return: MQTT error code, check devices.mqtt.MQTT_ERR_... for more details
        """
        if self.is_connected():
            return mqtt.MQTT_ERR_SUCCESS
        self._logger.info(f'Connecting to mqtt broker: {self.mqtt_broker_url} with user: {self.mqtt_user}')

        self.mqtt_client.username_pw_set(self.mqtt_user, self.mqtt_pwd)
        try:
            self.mqtt_client.connect(self.mqtt_broker_url, self.mqtt_port, self.mqtt_keepalive)
        except socket.timeout as excpt:
            self._logger.error(f'Could not connect to broker: {excpt.args[0]}')
            return mqtt.MQTT_ERR_NO_CONN
        except ConnectionRefusedError as excpt:
            self._logger.error(f'Connection refused from broker. Reason: {excpt.args[0]}')
            return mqtt.MQTT_ERR_CONN_REFUSED

        self.mqtt_client.loop_start()
        return mqtt.MQTT_ERR_SUCCESS

    def disconnect(self):
        self._logger.info(f'Disconnecting from mqtt broker: {self.mqtt_broker_url} with user: {self.mqtt_user}')
        self.mqtt_client.disconnect()

    def is_connected(self):
        return self.mqtt_client.is_connected()

    def device_on(self):
        self.connect()
        if self.state == 'off' or self.state is None:
            self._logger.info('Sending Device ON')
            self.mqtt_client.publish(f'shellies/{self.mqtt_device_id}/relay/0/command', 'on')

    def device_off(self):
        self.connect()
        if self.state == 'on' or self.state is None:
            self._logger.info('Sending Device OFF')
            self.mqtt_client.publish(f'shellies/{self.mqtt_device_id}/relay/0/command', 'off')

    def device_toggle(self):
        self.connect()
        self._logger.info('Sending Device TOGGLE')
        self.mqtt_client.publish(f'shellies/{self.mqtt_device_id}/relay/0/command', 'toggle')

    def subscribe_to_device(self):
        self.connect()
        topic_list = [(f'shellies/{self.mqtt_device_id}/temperature', self._mqtt_qos),
                      (f'shellies/{self.mqtt_device_id}/relay/0/power', self._mqtt_qos),
                      (f'shellies/{self.mqtt_device_id}/relay/0', self._mqtt_qos),
                      (f'plug/data', self._mqtt_qos),
                      (f'plug/data/info', self._mqtt_qos)]
        (result, mid) = self.mqtt_client.subscribe(topic_list)
        if result == mqtt.MQTT_ERR_SUCCESS:
            for topic in topic_list:
                self._subscription_tstamps[topic[0]] = time.time()
            self._logger.info(f'Subscribed to topics successful')
        else:
            self._logger.error(f'Subscription failed: MQTT client not connected')

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 5:
            # mqtt library returns rc = 5 even when credentials are incorrect
            self._logger.error(f'Connection result: {mqtt.connack_string(4)}')
            self._last_connect_rc = 4
        else:
            self._logger.info(f'Connection result: {mqtt.connack_string(rc)}')
        self._last_connect_rc = rc

    def _on_message(self, client, userdata, message: mqtt.MQTTMessage):
        if 'temperature' == message.topic.lstrip(f'shellies/{self.mqtt_device_id}/'):
            self.temperature = message.payload.decode()
        if 'relay/0' == message.topic.lstrip(f'shellies/{self.mqtt_device_id}/'):
            self.state = message.payload.decode()
        if'relay/0/power' == message.topic.lstrip(f'shellies/{self.mqtt_device_id}/'):
            self.power = message.payload.decode()
        if'plug/data' == message.topic:
            self.mqtt_client.publish('plug/data/info', self.__str__(), self._mqtt_qos, retain=True)

        if time.time() - self._subscription_tstamps[message.topic] > self._log_interval:
            self._logger.debug(f'Received message on topic: {message.topic} and data: {message.payload.decode()}')
            self._subscription_tstamps[message.topic] = time.time()

    def __str__(self):
        return f'time: {time.asctime()}, state: {self.state}, power: {self.power}, temperature: {self.temperature}'


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('heater_config.ini')

    logging.basicConfig(
        format='%(asctime)s | %(name)-10s | %(levelname)-10s | %(message)s',
        level=logging.INFO,
        datefmt='%Y/%d/%m %H:%M:%S')

    mqtt_data = {
        'mqtt_user': config['MQTT']['mqtt_user'],
        'mqtt_password': config['MQTT']['mqtt_password'],
        'mqtt_broker': config['MQTT']['mqtt_broker'],
        'mqtt_device_id': config['MQTT']['mqtt_device_id'],
        'mqtt_port': config['MQTT'].getint('mqtt_port'),
        'mqtt_retain': config['MQTT'].getboolean('mqtt_retain'),
        'mqtt_qos': config['MQTT'].getint('mqtt_qos')
    }
    plug = PlugDevice(**mqtt_data)


