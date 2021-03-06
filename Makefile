#
# Makefile for installing bme280_mqtt_daemon.py
INSTDIR = /usr/local/bin
SVCDIR  = /etc/systemd/system

#install: $(INSTDIR)/bme280_mqtt_daemon.py $(SVCDIR)/bme280-mqtt.service

install: install.daemon install.service
install.daemon: $(INSTDIR)/bme280_mqtt_daemon.py
install.service: $(SVCDIR)/bme280-mqtt.service

$(INSTDIR)/bme280_mqtt_daemon.py: bme280_mqtt_daemon.py
	cp $? $(INSTDIR)

$(SVCDIR)/bme280-mqtt.service: bme280-mqtt.service
	cp $? $(SVCDIR)
	systemctl daemon-reload
#	systemctl enable $?
#	systemctl start $?

clobber: clobber.daemon clobber.service

clobber.daemon:
	rm -f $(INSTDIR)/bme280_mqtt_daemon.py

clobber.service: bme280-mqtt.service
	systemctl stop $?
	systemctl disable $?
	rm -f $(SVCDIR)/bme280-mqtt.service
	systemctl daemon-reload
