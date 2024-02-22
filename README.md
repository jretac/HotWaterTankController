# Table of contents
1. [HotWaterTankController](#hotwatertankcontroller)
   1. [Requisites](#requisites) 
   2. [Dependencies](#dependencies)
   3. [ConfigurationFile](#configuration-file)
   5. [Logging](#logging)
   6. [Usage](#usage)
2. [Module description](#module-description)
   1. [Device module](#device-module)
   2. [Solar module](#solar-module)
   3. [Hot Water Tank module](#hot-water-tank-module)
3. [Mosquitto Broker](#mosquitto-broker)
4. [Run as a Service](#run-as-a-service)

# HotWaterTankController

HotWaterTankController is a python application to control the power source of a hot water tank, using a 
Shelly Plug S device that can be managed through MQTT, based on data from Huawei Fusion Solar API from a PV plant.

The main goal is to keep the hot water tank switched on the maximum possible time while keeping a balance between 
the generated and consumed energy.  
The default configuration aims a positive money balance. This means that **the hot water tank is switched
on if the value of sold energy is greater than the value of the bought energy for the current month**. The buy and sell prices are set through 
the configuration file, as well as all the connection information for the FusionSolar API and the MQTT connection.

The controller manages the power source for the water tank based on the sell-to-buy energy(kWh) ratio. If this ratio is 
greater than the buy-to-sell energy price(€) ratio, then the power source is switched on. Otherwise, it is switched off.
## Requisites
- [Shelly Plug S device](https://shelly-api-docs.shelly.cloud/gen1/#shelly-plug-plugs)
- [Huawei Fusion Solar account](https://region01eu5.fusionsolar.huawei.com/)
- Any electric hot water tank
- MQTT broker. In this example, [Mosquitto broker](https://mosquitto.org/) is used


## Dependencies

FusionSolarPY
```commandline
pip install fusion-solar-py
```
Paho MQTT Python library
```commandline
pip install paho-mqtt
```

## Configuration file
Parameter values for the `HotWaterTank` class can be read from file *heater_config.ini* configuration file.
This is the template for a configuration file:

```
[DEFAULT]
logging_level = INFO

[HUAWEI]
huawei_user = 
huawei_password = 

[MQTT]
mqtt_user = 
mqtt_password = 
mqtt_broker = 
mqtt_port = 
mqtt_device_id = 
mqtt_keepalive =
mqtt_retain = 
mqtt_qos = 

[ENERGY]
buy_price = 
sell_price = 
```

With such file, the **main** module will create a HotWaterTank instance and start automatically.

## Logging
Each module logs the result of the actions and events. In case the **main** module defines a file logger,
all modules will log to that file too.
In this case, a daily logger is generated and compressed upon day termination. Logs are saved in the log/ directory 
of the project.

## Usage
First, clone the repostory:  
`git clone https://github.com/jretac/HotWaterTankController.git`  

Then, create a virtual environment  
`python -m venv /patg/to/project/venv`

Activate the virtual environment with `source /path/to/project/venv/bin/activate` and install [Dependencies](#dependencies). 


Run the `main` script
```
 cd /path/to/project
 source venv/bin/activate
 python -m main
```

# Module description

## Device module
**device** module contains a single class that represents a Shelly Plug S device, the`PlugDevice` class, 
The constructor of the `PlugDevice` class requires the following parameters:
* **mqtt_user**: *str*
* **mqtt_password**: *str*
* **mqtt_broker**: *str* - broker IP address
* **mqtt_device_id**: *str* - Shelly 1 Plug Id
* **mqtt_port**: *int* - [optional] default 1883
* **mqtt_keepalive**: *int* - [optional] default 60

Method `subscribe_to_device` connects to the MQTT broker and subscribes to topics:
* shellies/shelly_device_id/temperature
* shellies/shelly_device_id/relay/0
* shellies/shelly_device_id/relay/0/power

The QoS is set to 0 by default.

Shelly Plug S can be switched on/off with methods `device_on` and `device_off`. There is also the possibility
to toggle the state of the plug with the `device_toggle` method.  
Methods `connect`, `disconnect` and `is_connected` are used for the MQTT interface.

## Solar module
**solar** module contains 2 classes: `FusionSolarClientExtended` and `PowerDevice`.  

### FusionSolarClientExtended
`FusionSolarClientExtended` is a subclass of the `FusionSolarClient` from the *fusion-solar-py* package.
This subclass overrides the `get_plant_stats` method but still 
keeps compatibility with the original method.  
The two differences with the original mehtod are:
1. New optional input parameter **stat_type**: *str* is accepted. The possible values for this parameter are `day`, 
`month`, `year` and `lifetime`. The default value is `day`, which means that plant data will be 
retrieved for the current day. If *stat_type* = `month`, then plant data will be retrieved for the month on 
the *query_time* parameter. If *stat_type* = `year`, then plant data will be retrieved for the year on 
the *query_time* parameter. If *stat_type* = `lifetime` then the complete lifetime data of the solar power plant is
retrieved.

2. If **query_time**: *int* parameter is not provided, a timestamp will be assigned for the current day. If provided, 
it has to be a POSIX timestamp multiplied by 1000.

### PowerDevice
`PowerDevice` class is a wrapper for the `FusionSolarClientExtended` that simplifies the interaction with
the Huawei Rest API. It takes 2 parameters for the constructor: `user` and `password`.  
Available methods are:
1. `get_inst_pwr`: takes one input, **tstamp**: *time.structTime*. If not provided, current local time will 
be assigned. Returns a dictionary with timestamp in string format, produced power and consumed power.
2. `get_overview`: takes two inputs and returns the plant stats for the selected date and statistic type.
   1. **date**: *datetime.datetime* 
   2. **stat_type**: *str* - The possible values for this parameter are `day`, 
`month`, `year` and `lifetime`. The default value is `day`, which means that plant data will be 
retrieved for the current day. If value is  `month`, then plant data will be retrieved for the month on 
the *date* parameter. If value is `year`, then plant data will be retrieved for the year on 
complete lifetime of the solar power plant.

## Hot Water Tank module
**hot_water_tank** module defines a class named `HotWaterTank`, which controls the water tank power source
based on the produced/consumed energy information.  
Power source is controlled via a `PlugDevice` object, and energy information is collected and managed via 
a `PowerDevice` object.  
The constructor of this class needs the credentials required by the `PowerDevice`  class in order to connect 
to the Huawei Rest API, and the MQTT information for the `PlugDevice`



# Mosquitto Broker
### Installation:
```shell
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto.service
systemctl status mosquitto.service
```
### Broker configuration:
Run
```shell
sudo nano /etc/mosquitto/mosquitto.conf 
```
And add the following lines:
```text
pid_file /var/run/mosquitto/mosquitto.pid

persistence true
persistence_location /var/lib/mosquitto/

log_dest topic
log_dest file /var/log/mosquitto/mosquitto.log

log_type error
log_type warning
log_type notice
log_type information

connection_messages true
log_timestamp true

include_dir /etc/mosquitto/conf.d
```
Now create a listener on por 1883. Run:
```shell
sudo nano /etc/mosquitto/conf.d/listener.conf
```
And add the following lines:
```text
listener 1883
password_file /etc/mosquitto/mosquitto.pwd
protocol mqtt
```

### Adding users
Finally, create a user. Password will be requested after executing the following command:
```shell
sudo mosquitto_passwd -c /etc/mosquitto/mosquitto.pwd testUser
```
Restart service
```shell
sudo systemctl restart mosquitto.service
```

# Run as Service
Create a file with this content:
File name: `hotwatertank-controller.service`
```text
[Unit]
Description=Hot Water Tank controller
After=network.target
Wants=network.target

[Service]
ExecStart=/path/to/project/venv/bin/python /path/to/project/main.py
Restart=on-failure

[Install]
WantedBy=default.target
```
Move the file to folder `/usr/local/lib`
```shell
sudo mkdir /usr/local/lib/HotWaterTank_service
sudo mv /path/to/your/project/main.py /usr/local/lib/HotWaterTankController_service/
sudo chown root:root /usr/local/lib/HotWaterTankController/main.py
sudo chmod 644 /usr/local/lib/HotWaterTankController_service/main.py
```
