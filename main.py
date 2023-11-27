import logging
import logging.handlers
import shutil
import gzip
import os
import sys

import hot_water_tank as hwt


def namer(name):
    return name + ".gz"


def rotator(source, destination):
    with open(source, 'rb') as f_in:
        with gzip.open(destination, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(source)


if __name__ == '__main__':
    # READ CONFIGURATION FILE
    import configparser
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'heater_config.ini'))

    huawei_user = config['HUAWEI']['huawei_user']
    huawei_password = config['HUAWEI']['huawei_password']

    mqtt_data = {
        'mqtt_user': config['MQTT']['mqtt_user'],
        'mqtt_password': config['MQTT']['mqtt_password'],
        'mqtt_broker': config['MQTT']['mqtt_broker'],
        'mqtt_device_id': config['MQTT']['mqtt_device_id'],
        'mqtt_port': config['MQTT'].getint('mqtt_port'),
        'mqtt_retain': config['MQTT'].getboolean('mqtt_retain'),
        'mqtt_qos': config['MQTT'].getint('mqtt_qos')
    }

    energy_buy_price = config['ENERGY'].getfloat('buy_price')
    energy_sell_price = config['ENERGY'].getfloat('sell_price')
    exclusion_time = config['ENERGY']['exclusion_time']
    logging_level = config['DEFAULT']['logging_level']

    # CONFIGURE LOGGING LEVEL
    if logging_level == 'DEBUG':
        logging_level = logging.DEBUG
    if logging_level == 'INFO':
        logging_level = logging.INFO
    if logging_level == 'ERROR':
        logging_level = logging.ERROR

    # CREATE LOGGER

    venv_bin = os.path.split(sys.executable)[0]
    venv = os.path.split(venv_bin)[0]
    project = os.path.split(venv)[0]
    log_dir = os.path.join(project, 'log')
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)

    rh_1 = logging.handlers.RotatingFileHandler(os.path.join(log_dir, 'HWTC_backup.log'),
                                                maxBytes=1024 * 1024,
                                                backupCount=50)
    rh_2 = logging.handlers.TimedRotatingFileHandler(os.path.join(log_dir, 'HWTC_daily.log'),
                                                     when='D',
                                                     interval=1,
                                                     backupCount=50)
    rh_1.rotator = rotator
    rh_1.namer = namer
    rh_2.rotator = rotator
    rh_2.namer = namer

    logging.basicConfig(
        format='%(asctime)s | %(name)-10s | %(levelname)-10s | %(message)s',
        level=logging_level,
        datefmt='%Y/%m/%d %H:%M:%S',
        handlers=[rh_1, rh_2])

    # RUN APP
    controller = hwt.HotWaterTank(huawei_user, huawei_password, **mqtt_data)
    controller.energy_price_buy = energy_buy_price
    controller.energy_price_sell = energy_sell_price
    controller.exclusion_time = exclusion_time
    controller.start()
