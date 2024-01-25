import time
import datetime
import logging
import fusion_solar_py.client as fsc
import fusion_solar_py.exceptions as fsc_exceptions
import requests

solar_logger = logging.getLogger(__name__)


class FusionSolarClientExtended(fsc.FusionSolarClient):
    """
    Subclass of FusionSolarClient that overrides the get_plant_stats method
    to allow querying aggregate data for day, month, year or complete lifetime
    """
    @fsc.logged_in
    def get_plant_stats(self, plant_id: str,
                        query_time: int = round(datetime.datetime.utcnow().timestamp()) * 1000,
                        stat_type: str = 'day') -> dict:
        """
        Queries data for day, month, year or complete lifetime of the plant
        :param plant_id:
        :param query_time: ``unix timestamp * 1000`` of the day. If stat_type = 'day' it can be any timestamp in the day.
            If stat_type = 'month', it can be any timestamp of the month and so on
        :param stat_type: str with the aggregate type for data:
        '``day``' for daily data,
        '``month``' for monthly data,
        '``year``' for yearly data,
        '``lifetime``' for lifetime data,

        :return:
        """
        date = datetime.datetime.fromtimestamp(query_time / 1000)
        if stat_type.lower() == 'day':
            stat_dim = 2   # Day
            date = date - datetime.timedelta(hours=date.hour, minutes=date.minute,
                                             seconds=date.second, microseconds=date.microsecond)
        elif stat_type.lower() == 'month':
            stat_dim = 4   # Month
            date = date - datetime.timedelta(days=date.day - 1, hours=date.hour, minutes=date.minute,
                                             seconds=date.second, microseconds=date.microsecond)
        elif stat_type.lower() == 'year':
            stat_dim = 5   # Year
            date.replace(month=1)
            date = date - datetime.timedelta(days=date.day - 1, hours=date.hour, minutes=date.minute,
                                             seconds=date.second, microseconds=date.microsecond)
        elif stat_type.lower() == 'lifetime':
            stat_dim = 6   # Lifetime
        else:
            stat_dim = 2
            date = date - datetime.timedelta(hours=date.hour, minutes=date.minute,
                                             seconds=date.second, microseconds=date.microsecond)

        url = f'https://{self._huawei_subdomain}.fusionsolar.huawei.com/rest/pvms/web/station/v1/overview/energy-balance'
        params = {
            'stationDn': plant_id,
            'timeDim': stat_dim,
            'queryTime': round(date.timestamp()) * 1000,
            'timeZone': 2,
            'timeZoneStr': 'Europe/Madrid',
            'dateStr': date.strftime('%Y-%m-%d %H:%M:%S'),
            "_": round(time.time() * 1000)
        }
        try:
            r = self._session.get(url=url,
                                  params=params)
            r.raise_for_status()
            plant_data = r.json()
        except requests.exceptions.ConnectionError as e:
            solar_logger.error(e.response)
            return {}

        if not plant_data["success"] or "data" not in plant_data:
            raise fsc_exceptions.FusionSolarException(
                f"Failed to retrieve plant status for {plant_id}"
            )

        # return the plant data
        return plant_data["data"]


class PowerDevice:
    """
    Class representing data from a FusionSolar station
    """
    def __init__(self, user: str, password: str):
        """
        Creates a power / energy data device
        :param user:
        :param password:
        :raise AuthenticationException if credentials are incorrect
        """
        try:
            self.client = FusionSolarClientExtended(user, password)
        except fsc_exceptions.AuthenticationException as except1:
            solar_logger.error(f'Logging error with user: {user} and password: {password}. {except1.args}')
            raise except1
        self.plant_ids = self.client.get_plant_ids()
        self._plant_id = self.plant_ids[0]

    def get_inst_pwr(self, tstamp: time.struct_time = time.localtime()) -> dict:
        """
        Returns a dictionary with requested timestamp string, produced power and used power.
        If no timestamp is provided, data for the current day is returned.
        :param tstamp: time tuple of the requested timestamp
        :return:
        """
        plant_data = self.get_overview(datetime.datetime.fromtimestamp(time.mktime(tstamp)))
        data_idx = tstamp.tm_hour * 60 // 5 + tstamp.tm_min // 5
        if plant_data['productPower'][data_idx] != '--':
            product_pwr = float(plant_data['productPower'][data_idx])
        else:
            product_pwr = 0.0

        if plant_data['usePower'][data_idx] != '--':
            use_power = float(plant_data['usePower'][data_idx])
        else:
            use_power = 0.0
        return {'timestamp': plant_data['xAxis'][data_idx],
                'productPower': product_pwr,
                'usePower': use_power}

    def get_overview(self,
                     date: datetime.datetime = None,
                     stat_type: str = 'day') -> dict:
        """
        Returns all the information for a specific aggregate type
        :param date: any datetime inside the desired time range
        :param stat_type: str with the aggregate type for data:
        '``day``' for daily data,
        '``month``' for monthly data,
        '``year``' for yearly data,
        '``lifetime``' for lifetime data,
        :return:
        """
        self.client._configure_session()
        if date is None:
            date = datetime.datetime.now()
        return self.client.get_plant_stats(self._plant_id,
                                           query_time=round(date.timestamp()) * 1000, stat_type=stat_type)


if __name__ == '__main__':
    def get_tstamp(year: int, month: int, day: int, hour: int, minute: int) -> time.struct_time:
        return time.strptime(f'{year}{month}{day}{hour}{minute}00', '%Y%m%d%H%M%S')

    import configparser
    config = configparser.ConfigParser()
    config.read('heater_config.ini')
    huawei_user = config['HUAWEI']['huawei_user']
    huawei_password = config['HUAWEI']['huawei_password']

    my_data = PowerDevice(huawei_user, huawei_password)
    pwr_stats = my_data.get_inst_pwr()
    print(f'Date: {pwr_stats["timestamp"]}')
    print(f'Current produced power: {pwr_stats["productPower"]} kW')
    print(f'Current consumed power: {pwr_stats["usePower"]} kW')

    request_date = datetime.datetime(2023, 2, 24, 8, 30)
    pwr_hist_stats = my_data.get_inst_pwr(request_date.timetuple())
    print(f'Date: {request_date.isoformat(sep=" ")}')
    print(f'Produced power : {pwr_hist_stats["productPower"]} kW')
    print(f'Consumed power: {pwr_hist_stats["usePower"]} kW')