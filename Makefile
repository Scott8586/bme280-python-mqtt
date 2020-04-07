#
# Makefile for installing bme280-mqtt-daemon.py
INSTDIR = /usr/local/bin

install: bme280-mqtt-daemon.py
	cp $? $(INSTDIR)
