import threading
import logging
import solar
import devices


class HotWaterTank:
    """
    Class representing a water tank power controller.

    The controller will activate the water tank source power if the sold to
    bought energy ratio is greater than the buy to sell energy price ratio:

    ``sell/buy [in kWh] > buy/sell [in €]``

    Energy data is retrieved through Huawei's FusionSolar API and the power
    source is controlled via a Shelly 1 Plug
    """
    def __init__(self, user: str, pwd: str, **kwargs):
        """
        Creates a HotWaterTank object
        :param user: FusionSolar user
        :param pwd: FuseionSolar password
        :param kwargs: arguments for the MQTT connection
        """
        self._energy_price_buy = 0.16
        self._energy_price_sell = 0.11
        self.energy_device = solar.PowerDevice(user, pwd)
        self.timer = None
        self._timer_period = 300     # Timer event period in seconds [s]
        self._run = False
        self._logger = logging.getLogger('water_tank')
        self.plug = devices.PlugDevice(**kwargs)
        self._logger.info('Creating device')

    def activate_permission(self) -> bool:
        """
        Checks if it is allowed to activate the water tank power source
        :return:
        """
        daily_data = self.energy_device.get_overview()
        monthly_data = self.energy_device.get_overview(stat_type='month')
        if daily_data['totalOnGridPower'] == '--':
            self._logger.warning(f'Not possible to calculate ratio. '
                                 f'Daily onGridPower: {daily_data["totalOnGridPower"]}')
            return False
        if daily_data['totalBuyPower'] == '--':
            self._logger.warning(f'Not possible to calculate ratio. '
                                 f'Daily BuyPower: {daily_data["totalBuyPower"]}')
            return False
        if monthly_data['totalOnGridPower'] == '--':
            self._logger.warning(f'Not possible to calculate ratio. '
                                 f'Monthly onGridPower: {monthly_data["totalOnGridPower"]}')
            return False
        if monthly_data['totalBuyPower'] == '--':
            self._logger.warning(f'Not possible to calculate ratio. '
                                 f'Monthly totalBuyPower: {monthly_data["totalBuyPower"]}')
            return False

        month_ratio = float(monthly_data['totalOnGridPower']) / float(monthly_data['totalBuyPower'])
        day_ratio = float(daily_data['totalOnGridPower']) / float(daily_data['totalBuyPower'])
        return (day_ratio > 1.1 * self.ratio) or (month_ratio > self.ratio)

    def start(self):
        """
        Starts the controller
        :return:
        """
        self._run = True
        self.plug.subscribe_to_device()
        self._loop()

    def stop(self):
        """
        Stops the controller
        :return:
        """
        self._run = False

    def _loop(self):
        if self._run:
            if self.activate_permission():
                self._logger.info(f'Switch on approved.')
                self.plug.device_on()
            else:
                self._logger.info(f'Switch on disapproved.')
                self.plug.device_off()
            self.timer = threading.Timer(self._timer_period, self._loop).start()

    @property
    def ratio(self):
        return self.energy_price_buy / self.energy_price_sell

    @ratio.setter
    def ratio(self, value: float):
        raise ValueError('field `ratio` cannot be assigned, modify energy prices instead')

    @property
    def energy_price_buy(self):
        return self._energy_price_buy

    @energy_price_buy.setter
    def energy_price_buy(self, value: float):
        if value != 0.0:
            self._energy_price_buy = value
            self._logger.info(f'Updated energy buy price to: {value}. New ratio: {self.ratio}')

    @property
    def energy_price_sell(self):
        return self._energy_price_sell

    @energy_price_sell.setter
    def energy_price_sell(self, value: float):
        if value != 0.0:
            self._energy_price_sell = value
            self._logger.info(f'Updated energy sell price to: {value}. New ratio: {self.ratio}')
        else:
            raise ZeroDivisionError('Sell energy price cannot be 0.0')


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('heater_config.ini')

    huawei_user = config['HUAWEI']['huawei_user']
    huawei_password = config['HUAWEI']['huawei_password']
    mqtt_user = config['MQTT']['mqtt_user']
    mqtt_password = config['MQTT']['mqtt_password']
    mqtt_broker = config['MQTT']['mqtt_broker']
    mqtt_port = config['MQTT'].getint('mqtt_port')
    mqtt_device_id = config['MQTT']['mqtt_device_id']
    mqtt_data = {
        'mqtt_user': mqtt_user,
        'mqtt_password': mqtt_password,
        'mqtt_broker': mqtt_broker,
        'mqtt_device_id': mqtt_device_id,
        'mqtt_port': mqtt_port
    }
    controller = HotWaterTank(huawei_user, huawei_password, **mqtt_data)
    controller.start()
