import threading
import logging
import time

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
        self._energy_price_buy = 1
        self._energy_price_sell = 1
        self.energy_device = solar.PowerDevice(user, pwd)
        self.timer = None
        self._timer_period = 300     # Timer event period in seconds [s]
        self._run = False
        self.plug = devices.PlugDevice(**kwargs)
        self._exclusion_time = []
        self._ratio_monthly = None
        self._ratio_daily = None
        self._logger = logging.getLogger('water_tank')
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

        self.ratio_monthly = float(monthly_data['totalOnGridPower']) / float(monthly_data['totalBuyPower'])
        self.ratio_daily = float(daily_data['totalOnGridPower']) / float(daily_data['totalBuyPower'])

        # Check exclusion times
        for i in range(len(self.exclusion_time)):
            if self.exclusion_time[i]['start'] <= time.localtime().tm_hour < self.exclusion_time[i]['end']:
                return False
        return (self.ratio_daily > 1.1 * self.ratio_threshold) or (self.ratio_monthly > self.ratio_threshold)

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
    def ratio_threshold(self):
        return self.energy_price_buy / self.energy_price_sell

    @ratio_threshold.setter
    def ratio_threshold(self, value: float):
        raise ValueError('field `ratio_threshold` cannot be assigned, modify energy prices instead')

    @property
    def ratio_daily(self):
        return self._ratio_daily

    @ratio_daily.setter
    def ratio_daily(self, value: float):
        if value < 0:
            raise ValueError(f'daily ration `ratio_daily` cannot be a negative number')
        else:
            self._ratio_daily = value

    @property
    def ratio_monthly(self):
        return self._ratio_monthly

    @ratio_monthly.setter
    def ratio_monthly(self, value: float):
        if value < 0:
            raise ValueError(f'daily ration `ratio_daily` cannot be a negative number')
        else:
            self._ratio_monthly = value

    @property
    def energy_price_buy(self):
        return self._energy_price_buy

    @energy_price_buy.setter
    def energy_price_buy(self, value: float):
        if value != 0.0:
            self._energy_price_buy = value
            self._logger.info(f'Updated energy buy price to: {value}. New ratio_threshold: {self.ratio_threshold}')

    @property
    def energy_price_sell(self):
        return self._energy_price_sell

    @energy_price_sell.setter
    def energy_price_sell(self, value: float):
        if value != 0.0:
            self._energy_price_sell = value
            self._logger.info(f'Updated energy sell price to: {value}. New ratio: {self.ratio_threshold}')
        else:
            raise ZeroDivisionError('Sell energy price cannot be 0.0')

    @property
    def exclusion_time(self):
        return self._exclusion_time

    @exclusion_time.setter
    def exclusion_time(self, time_intervals: list) -> None:
        if type(time_intervals) is not list:
            time_intervals = [time_intervals]
        for i in range(len(time_intervals)):
            interval = {
                'start': int(time_intervals[i].split('-')[0]),
                'end': int(time_intervals[i].split('-')[1])
                        }
            self._exclusion_time.append(interval)


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
