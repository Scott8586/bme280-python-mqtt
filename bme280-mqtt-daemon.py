#!/usr/bin/env python3

import time
import datetime
import platform
import os
import signal
import sys

import argparse
import configparser
import daemon
from daemon import pidfile
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

# Python library for the BME280 temperature, pressure and humidity sensor
from bme280 import BME280 as BME280, I2C_ADDRESS_GND as I2C_ADDRESS_GND, I2C_ADDRESS_VCC as I2C_ADDRESS_VCC

MQTT_INI = "/etc/mqtt.ini"
MQTT_SEC = "bme280"

def receiveSignal(signalNumber, frame):
    print('Received:', signalNumber)
    exit(0)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print("Connected with result code "+str(rc))

def start_daemon(args):
    ### This launches the daemon in its context

    ### XXX pidfile is a context
    context = daemon.DaemonContext(
        working_directory='/var/tmp',
        umask=0o002,
        pidfile=pidfile.TimeoutPIDLockFile(args.pid_file),
        )

    context.signal_map = {
       signal.SIGHUP: receiveSignal,
       signal.SIGINT: receiveSignal,
       signal.SIGQUIT: receiveSignal,
       signal.SIGTERM: receiveSignal,
    }

    with context:
        start_bme280_sensor(args)


def start_bme280_sensor(args):
    """Main program function, parse arguments, read configuration,
    setup client, listen for messages"""

    i2c_address=I2C_ADDRESS_GND # 0x76, alt is 0x77

    toffset = 0
    hoffset = 0
    poffset = 0

    if (args.daemon):
        fh = open(args.log_file, "w")
    else:
        fh = sys.stdout

    client = mqtt.Client(clientId)

    mqtt_conf = configparser.ConfigParser()
    mqtt_conf.read(args.config)

    topic = mqtt_conf.get(args.section, 'topic')

    if (mqtt_conf.has_option(args.section, 'address')):
        i2c_address = int(mqtt_conf.get(args.section, 'address'), 0)

    if (mqtt_conf.has_option(args.section, 'toffset')):
        toffset = float(mqtt_conf.get(args.section, 'toffset'))

    if (mqtt_conf.has_option(args.section, 'hoffset')):
        hoffset = float(mqtt_conf.get(args.section, 'hoffset'))

    if (mqtt_conf.has_option(args.section, 'poffset')):
        poffset = float(mqtt_conf.get(args.section, 'poffset'))

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

    topic_temp  = topic + '/' + 'bme280-temperature'
    topic_hum   = topic + '/' + 'bme280-humidity'
    topic_press = topic + '/' + 'bme280-pressure'

    # Initialise the BME280
    bus = SMBus(1)

    bme280 = BME280(i2c_addr=i2c_address, i2c_dev=bus)

    if (args.verbose):
        curr_datetime = datetime.datetime.now()
        str_datetime = curr_datetime.strftime("%Y-%m-%d %H:%M:%S")
        print("{0}: pid: {1:d} bme280 sensor started on 0x{2:x}, toffset: {3:0.1f} F, hoffset: {4:0.1f} %, poffset: {5:0.2f} hPa".format(str_datetime, os.getpid(), i2c_address, toffset, hoffset, poffset), file = fh)
        fh.flush()

    while True:
        curr_time = time.time()

        temp  = bme280.get_temperature()
        temp  = 9.0/5.0 * temp + 32 + toffset
        press = bme280.get_pressure() + poffset
        hum   = bme280.get_humidity() + hoffset

        # print('{:05.2f}*F {:05.2f}% {:05.2f}hPa'.format(temp, hum, press))

        my_time = int(round(curr_time))

        if (my_time % 60 == 0): 
            curr_datetime = datetime.datetime.now()
            str_datetime = curr_datetime.strftime("%Y-%m-%d %H:%M:%S")

            humidity = str(round(hum, 1))
            temperature = str(round(temp, 1))
            pressure = str(round(press, 2))
            
            if args.verbose:
                print("{0}: temperature: {1:.1f} F, humidity: {2:.1f} %, pressure: {3:.2f} hPa".format(str_datetime, temp, hum, press), file = fh)
                fh.flush()

            client.publish(topic_hum, humidity)
            client.publish(topic_temp, temperature)
            client.publish(topic_press, pressure)

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

    if (args.daemon):
        start_daemon(args)
    else:
        start_bme280_sensor(args)
