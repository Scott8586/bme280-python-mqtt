## bme280-python-mqtt
Daemon for bme280 sensor reporting through MQTT

This code uses the [Pimoroni bme280-python](https://github.com/pimoroni/bme280-python) python code to scan the BME280 sensor, and report the results over MQTT.

The daemon uses configparser() to read an .ini style file to get information on the MQTT server to contact.
It is also possible to set the i2c address for the sensor, and provide measurement offsets.
If elevation is provided (in meters), a sealevel measure is calculated and provided in the MQTT feed.

A systemd service file is also included and is part of the install process in the Makefile.

The following configuration yaml could be used with Home Assistant:

```
sensor:
 - platform: mqtt
    state_topic: 'environment/den/bme280-temperature'
    unit_of_measurement: '°F'
    name: 'Den Temperature'
  - platform: mqtt
    state_topic: 'environment/den/bme280-humidity'
    unit_of_measurement: '% RH'
    name: 'Den Humidity'    
  - platform: mqtt
    state_topic: 'environment/den/bme280-pressure'
    unit_of_measurement: 'hPa'
    name: 'Den Pressure'
  - platform: mqtt
    state_topic: 'environment/den/bme280-sealevel-pressure'
    unit_of_measurement: 'hPa'
    name: 'Den Sealevel Pressure'
```

And for lovelace display:

```
cards:
  - entities:
      - entity: sensor.den_temperature
      - entity: sensor.den_humidity
      - entity: sensor.den_pressure
      - entity: sensor.den_sealevel_pressure
    title: Den BME280
    type: entities
```


