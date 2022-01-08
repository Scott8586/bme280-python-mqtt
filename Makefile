#
# Makefile for installing bme280_mqtt_daemon.py
INSTDIR = /usr/local/bin
SVCDIR  = /etc/systemd/system

SCRIPT  = bme280_mqtt_daemon.py
SERVICE = bme280-mqtt.service

#install: $(INSTDIR)/bme280_mqtt_daemon.py $(SVCDIR)/bme280-mqtt.service

install: install.daemon install.service
install.daemon: $(INSTDIR)/$(SCRIPT)
install.service: $(SVCDIR)/$(SERVICE)

build:
	sudo pip3 install -r requirements.txt

test:
	sudo ./$(SCRIPT)

$(INSTDIR)/$(SCRIPT): $(SCRIPT)
	cp $? $(INSTDIR)

$(SVCDIR)/$(SERVICE): $(SERVICE)
	cp $? $(SVCDIR)
	systemctl daemon-reload
	systemctl enable $?
#	systemctl start $?

clobber: clobber.daemon clobber.service

clobber.daemon:
	rm -f $(INSTDIR)/$(SCRIPT)

clobber.service: $(SERVICE)
	systemctl stop $?
	systemctl disable $?
	rm -f $(SVCDIR)/$(SERVICE)
	systemctl daemon-reload
