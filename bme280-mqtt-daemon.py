#!/usr/bin/env python3

import time
import datetime
import argparse
import configparser
import RPi.GPIO as GPIO
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
from bme280 import BME280

MQTT_INI = "/etc/mqtt.ini"
MQTT_SEC = "bme280"

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


# Initialise the BME280
bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)

def main():
    """Main program function, parse arguments, read configuration,
    setup client, listen for messages"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default=MQTT_INI, help="configuration file")
    parser.add_argument('-s', '--section', default=MQTT_SEC, help="configuration file section")
    parser.add_argument('-d', '--detach', action='store_true',
                    help="fork and detach process, run as daemon")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose messages")
    args = parser.parse_args()

    client = mqtt.Client('raspi-den-tr')

    mqtt_conf = configparser.ConfigParser()
    mqtt_conf.read(args.config)

    topic = mqtt_conf.get(args.section, 'topic')

    if (mqtt_conf.has_option(args.section, 'username') and
         mqtt_conf.has_option(args.section, 'password')):
        username = mqtt_conf.get(args.section, 'username')
        password = mqtt_conf.get(args.section, 'password')
        client.username_pw_set(username=username, password=password)

    host = mqtt_conf.get(args.section, 'host')
    port = int(mqtt_conf.get(args.section, 'port'))

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, 60)
    client.loop_start()

    topic_temp  = topic + '/' + 'bme280-temperature'
    topic_hum   = topic + '/' + 'bme280-humidity'
    topic_press = topic + '/' + 'bme280-pressure'

    while True:
        curr_time = time.time()

        temp  = bme280.get_temperature()
        temp  = 9.0/5.0 * temp + 32
        press = bme280.get_pressure()
        hum   = bme280.get_humidity()

        # print('{:05.2f}*F {:05.2f}hPa {:05.2f}%'.format(temp, press, hum))

        my_time = int(round(curr_time))

        if (my_time % 60 == 0): 

            curr_datetime = datetime.datetime.now()
            str_datetime = curr_datetime.strftime("%Y-%m-%d %H:%M:%S")

            humidity = str(round(hum, 2))
            temperature = str(round(temp, 2))
            pressure = str(round(press, 2))
            
            if args.verbose:
                print("{0}: temperature: {1:.2f} F, pressure: {2:.2f}hPa, humidity: {3:.2f} %RH".format(str_datetime, temp, press, hum))

            client.publish(topic_hum, humidity)
            client.publish(topic_temp, temperature)
            client.publish(topic_press, pressure)

        time.sleep(1)

if __name__ == '__main__':
    main()

