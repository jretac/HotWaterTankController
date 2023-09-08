# HotWaterTankController

Python controller for a hot water tank power source connected to a remotely controlled a Shelly Plug S device and managed throujgh Huawei Fusion Solar API.

## Dependencies
FusionSolarPY
```commandline
pip install fusion-solar-py
```
Paho MQTT Python library
```commandline
pip install paho-mqtt
```

## Description
### Device module
**device** module contains a single class that represents a Shelly Plug S device, the```PlugDevice``` class, 
The constructor of the ```PlugDevice``` class requires the following parameters:
* **mqtt_user**: *str*
* **mqtt_password**: *str*
* **mqtt_broker**: *str* - broker IP address
* **mqtt_device_id**: *str* - Shelly 1 Plug Id
* **mqtt_port**: *int* - [optional] default 1883
* **mqtt_keepalive**: *int* - [optional] default 60

Method ```subscribe_to_device``` connects to the MQTT broker and subscribes to topics:
* shellies/shelly_device_id/temperature
* shellies/shelly_device_id/relay/0
* shellies/shelly_device_id/relay/0/power

The QoS is set to 0 by default.

Shelly Plug S can be switched on/off with methods ```decive_on``` and ```device_off```. 
There is also the possibility to toggle the state of the plug with the ```device_toggle``` method.

### Solar module
**solar** module contains 2 classes: ```FusionSolarClientExtended``` and ```PowerDevice```.  
```FusionSolarClientExtended``` is a subclass of the ```FusionSolarClient``` from the *fusion-solar-py* module.
This subclass overrides the ```get_plant_stats``` method but still 
keeps compatibility with the original method.  
The two differences with the original mehtod are:
1. New optional input parameter **stat_type**: *str* is accepted. The possible values for this parameter are ```day```, 
```month```, ```year``` and ```lifetime```. The default value is ```day```, which means that plant data will be 
retrieved for the current day. If *stat_type* = ```month```, then plant data will be retrieved for the month on 
the *query_time* parameter. If *stat_type* = ```year```, then plant data will be retrieved for the year on 
the *query_time* parameter. If *stat_type* = ```lifetime``` then the complete lifetime data of the solar power plant is
retrieved.

2. If **query_time**: *int* parameter is not provided, a timestamp will be assigned for the current day. If provided, 
it has to be a POSIX timestamp multiplied by 1000.

```PowerDevice``` class is a wrapper for the ```FusionSolarClientExtended``` that simplifies the interaction with
the Huawei Rest API. It takes 2 parameters for the constructor: ```user``` and ```password```.  
Available methods are:
1. ```get_inst_pwr```: takes one input, **tstamp**: *time.structTime*. If not provided, current local time will 
be assigned.
2. ```get_overview```: takes two inputs and returns the plant stats for the selected date and statistic type.
   1. **date**: *datetime.datetime* 
   2. **stat_type**: *str* - The possible values for this parameter are ```day```, 
```month```, ```year``` and ```lifetime```. The default value is ```day```, which means that plant data will be 
retrieved for the current day. If value is  ```month```, then plant data will be retrieved for the month on 
the *date* parameter. If value is ```year```, then plant data will be retrieved for the year on 
complete lifetime of the solar power plant.

### Hot Water Tank module
**hot_water_tank** module defines a class named ```HotWaterTank```, which controls the water tank power source
based on the produced/consumed energy information.  
Power source is controlled via a ```PlugDevice``` object, and energy information is collected and managed via 
a ```PowerDevice``` object.  
The constructor of this class needs the credentials required by the ```PowerDevice```  class in order to connect 
to the Huawei Rest API, and the MQTT information for the ```PlugDevice```

## Configuration file
Parameter values for the ```HotWaterTank``` class can be read from a *.ini* configuration file.
This is the template for a configuration file:
```commandline
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
```
With such file, the **main** module will create a HotWaterTank instance and start automatically.

## Logging
Each module logs the result of the actions and events. In case the **main** module defines a file logger,
all modules will log to that file too.
In this case, a daily logger is generated and compressed upon day termination. Logs are saved in the log/ directory 
of the project.