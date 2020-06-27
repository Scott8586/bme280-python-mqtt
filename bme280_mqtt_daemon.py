#!/usr/bin/env python3
"""
Python script for reading a BME280 sensor on a raspberry pi and reporting back via MQTT
"""

# pylint: disable=no-member
# pylint: disable=unused-argument

import time
import datetime
import platform
#import math # needed only for detailed sealavel pressure calculation
import json
import os
import signal
import sys

import argparse
import configparser
import daemon
from daemon import pidfile
import paho.mqtt.client as mqtt

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

# Python library for the BME280 temperature, pressure and humidity sensor
import bme280

MQTT_INI = "/etc/mqtt.ini"
MQTT_SEC = "bme280"

SEALEVEL_MIN = -999

class Options(object):
    
    def __init__(self):
        self.toffset = 0
        self.hoffset = 0
        self.poffset = 0
        self.topic = ""
        self.elevation = SEALEVEL_MIN
        self.format = "flat"

def receive_signal(signal_number, frame):
    """function to attach to a signal handler, and simply exit
    """

    print('Received signal: ', signal_number)
    sys.exit(0)


def on_connect(client, userdata, flags, return_code):
    """function to mark the connection to a MQTT server
    """

    if return_code != 0:
        print("Connected with result code: ", str(return_code))


def publish_mqtt(client, sensor, options, file_handle):
    """Publish the sensor data to mqtt, in either flat, or JSON format
    """
    
    topic_temp  = options.topic + '/' + 'bme680-temperature'
    topic_hum   = options.topic + '/' + 'bme680-humidity'
    topic_press = options.topic + '/' + 'bme680-pressure'
    topic_press_S = options.topic + '/' + 'bme680-sealevel-pressure'
    
    hum = sensor.get_humidity() + options.hoffset

    temp_C = sensor.get_temperature()
    temp_F = 9.0/5.0 * temp_C + 32 + options.toffset
    temp_K = temp_C + 273.15

    press_A = sensor.get_pressure() + options.poffset

    # https://www.sandhurstweather.org.uk/barometric.pdf
    if options.elevation > SEALEVEL_MIN:
        # option one: Sea Level Pressure = Station Pressure / e ** -elevation / (temperature x 29.263)
        #press_S = press_A / math.exp( - elevation / (temp_K * 29.263))
        # option two: Sea Level Pressure = Station Pressure + (elevation/9.2)
        press_S = press_A + (options.elevation/9.2)
    else:
        press_S = press_A

    curr_datetime = datetime.datetime.now()
    
    if args.verbose:
        str_datetime = curr_datetime.strftime("%Y-%m-%d %H:%M:%S")
        print("{0}: temperature: {1:.1f} F, humidity: {2:.1f} %RH, pressure: {3:.2f} hPa, sealevel: {4:.2f} hPa".
            format(str_datetime, temp_F, hum, press_A, press_S), file=file_handle)
        file_handle.flush()

    if options.format == "flat":
        temperature = str(round(temp_F, 1))
        humidity = str(round(hum, 1))
        pressure = str(round(press_A, 2))
        pressure_sealevel = str(round(press_S, 2))
    
        client.publish(topic_temp, temperature)
        client.publish(topic_hum, humidity)
        client.publish(topic_press, pressure)
        
        if options.elevation > SEALEVEL_MIN:
            client.publish(topic_press_S, pressure_sealevel)
                    
    else:
        data = {}
        data['humidity'] = round(hum, 1)
        data['temperature'] = round(temp_F, 1)
        data['pressure'] = round(press_A, 2)
        if options.elevation > SEALEVEL_MIN:
            data['sealevel'] = round(press_S, 2)
        data['timestamp'] = curr_datetime.replace(microsecond=0).isoformat()

        #json_data = json.dumps(data)
        client.publish(options.topic, json.dumps(data))

def start_daemon(args):
    """function to start daemon in context, if requested
    """

    context = daemon.DaemonContext(
        working_directory='/var/tmp',
        umask=0o002,
        pidfile=pidfile.TimeoutPIDLockFile(args.pid_file),
        )

    context.signal_map = {
        signal.SIGHUP: receive_signal,
        signal.SIGINT: receive_signal,
        signal.SIGQUIT: receive_signal,
        signal.SIGTERM: receive_signal,
    }

    with context:
        start_bme280_sensor(args)


def start_bme280_sensor(args):
    """Main program function, parse arguments, read configuration,
    setup client, listen for messages"""

    i2c_address = bme280.I2C_ADDRESS_GND # 0x76, alt is 0x77

    options = Options()
    
    if args.daemon:
        file_handle = open(args.log_file, "w")
    else:
        file_handle = sys.stdout

    client = mqtt.Client(args.clientid)

    mqtt_conf = configparser.ConfigParser()
    mqtt_conf.read(args.config)

    options.topic = mqtt_conf.get(args.section, 'topic')

    if mqtt_conf.has_option(args.section, 'address'):
        i2c_address = int(mqtt_conf.get(args.section, 'address'), 0)

    if mqtt_conf.has_option(args.section, 'toffset'):
        options.toffset = float(mqtt_conf.get(args.section, 'toffset'))

    if mqtt_conf.has_option(args.section, 'hoffset'):
        options.hoffset = float(mqtt_conf.get(args.section, 'hoffset'))

    if mqtt_conf.has_option(args.section, 'poffset'):
        options.poffset = float(mqtt_conf.get(args.section, 'poffset'))

    if mqtt_conf.has_option(args.section, 'elevation'):
        options.elevation = float(mqtt_conf.get(args.section, 'elevation'))

    if mqtt_conf.has_option(args.section, 'format'):
        options.format = mqtt_conf.get(args.section, 'format')

    if (mqtt_conf.has_option(args.section, 'username') and
            mqtt_conf.has_option(args.section, 'password')):
        username = mqtt_conf.get(args.section, 'username')
        password = mqtt_conf.get(args.section, 'password')
        client.username_pw_set(username=username, password=password)

    host = mqtt_conf.get(args.section, 'host')
    port = int(mqtt_conf.get(args.section, 'port'))

    client.on_connect = on_connect
    client.connect(host, port, 60)
    client.loop_start()

    # Initialise the BME280
    bus = SMBus(1)

    sensor = bme280.BME280(i2c_addr=i2c_address, i2c_dev=bus)

    if args.verbose:
        curr_datetime = datetime.datetime.now()
        str_datetime = curr_datetime.strftime("%Y-%m-%d %H:%M:%S")
        print("{0}: pid: {1:d} bme280 sensor started on 0x{2:x}, toffset: {3:0.1f} F, hoffset: {4:0.1f} %, poffset: {5:0.2f} hPa".
              format(str_datetime, os.getpid(), i2c_address, options.toffset, options.hoffset, options.poffset), file=file_handle)
        file_handle.flush()

    while True:
        curr_time = time.time()
        my_time = int(round(curr_time))

        if my_time % 60 == 0:
            publish_mqtt(client, sensor, options, file_handle)
 
        time.sleep(1)

if __name__ == '__main__':

    #myhost = socket.gethostname().split('.', 1)[0]
    myhost = platform.node()
    mypid  = os.getpid()
    clientId = myhost + '-' + str(mypid)

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--config', default=MQTT_INI, help="configuration file")
    parser.add_argument('-d', '--daemon', action='store_true', help="run as daemon")
    parser.add_argument('-p', '--pid-file', default='/var/run/bme280_mqtt.pid')
    parser.add_argument('-l', '--log-file', default='/var/log/bme280_mqtt.log')
    parser.add_argument('-i', '--clientid', default=clientId, help="clientId for MQTT connection")
    parser.add_argument('-s', '--section', default=MQTT_SEC, help="configuration file section")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose messages")

    args = parser.parse_args()

    if args.daemon:
        start_daemon(args)
    else:
        start_bme280_sensor(args)
