import json
import logging
import os
import threading
import time

import paho.mqtt.client as mqtt
from flask import Flask, url_for, render_template, request
from werkzeug.utils import redirect

from common import CUBIE_GPIO, CUBIE_ENOCEAN, CUBIE_RELAY, CUBIE_VICTRON, CUBIE_SONAR, CUBIE_CORE
from common.network import get_ip_address  # noqa
from common.python import get_configuration, execute_command, set_configuration
from mqtt_client import configure_logger

app = Flask(__name__)
configure_logger()
service_list = [
    {"id": CUBIE_CORE, "name": "Cubie Core", "icon": "demo.png",
     "description": "Core Service for general configuration and communication"},
    {"id": CUBIE_GPIO, "name": "Cubie-GPIO", "icon": "gpio.png",
     "description": "Control GPIO Pins on your device (eg. Raspberry Pi)"},
    {"id": CUBIE_ENOCEAN, "name": "Cubie-EnOcean", "icon": "enocean.png",
     "description": "With an EnOcean Adapter on your GPIO Pins you can communicate with EnOcean Devices"},
    {"id": CUBIE_RELAY, "name": "Cubie-Relay", "icon": "relay.png",
     "description": "Find and control ETH008 Relay Boards"},
    {"id": CUBIE_SONAR, "name": "Cubie-Sonar", "icon": "sonar.png",
     "description": "Read values from Sonar Device connected to your GPIO Pins"},
    {"id": CUBIE_VICTRON, "name": "Cubie-Victron", "icon": "victron.png",
     "description": "Connect your Victron Energy System with this Gateway"}
]


@app.route('/show/<application>')
def show_application(application):
    device_list = get_device_list(application)
    if type(device_list) is not dict:
        return render_template('application.html', application=application, device_list=device_list)
    return render_template('device.html', application=application, device=device_list)


@app.route('/show/<application>/<device_id>')
def show_device(application, device_id):
    configuration = get_configuration(application)
    device = None
    for item in configuration:
        if item['id'] == device_id:
            device = item
    return render_template('device.html', application=application, device=device)


@app.route('/update/<application>/<parameter_id>', methods=['POST'])
def update_application_parameter(application, parameter_id):
    configuration = get_configuration(application)
    configuration[parameter_id] = request.form[parameter_id]

    set_configuration(application, configuration)

    return render_template('application.html', application=application, device_list=get_device_list(application))


@app.route('/update/<application>/<device_id>/<parameter_id>', methods=['POST'])
def update_device_parameter(application, device_id, parameter_id):
    configuration = get_configuration(application)
    device = None
    for item in configuration:
        if item['id'] == device_id:
            item[parameter_id] = request.form[parameter_id]
            device = item

    set_configuration(application, configuration)

    return render_template('device.html', application=application, device=device)


@app.route('/delete/<application>/<item>')
def remove_item_from_application(application, item):
    device_list = get_device_list(application)
    if item == "all":
        delete_item(application, [device['id'] for device in device_list])
    else:
        delete_item(application, [item])

    time.sleep(1)

    return redirect(url_for('show_application', application=application))


@app.route('/function/<application>/<item>')
def switch_io_function_of_item(application, item):
    device_list = get_device_list(application)
    for i in range(len(device_list)):
        if item == str(device_list[i]["id"]):
            function = device_list[i]["function"]
            device_list[i]["function"] = "OUT" if function == "IN" else "IN"
            break

    return redirect(url_for('show_application', application=application))


@app.route('/switch_learn_mode')
def switch_learn_mode():
    config = get_configuration(CUBIE_CORE)
    new_learn_mode = not bool(config['learn_mode'])
    logging.info(f"switching learn_mode to {new_learn_mode}")
    mqtt_client = connect_mqtt_client(config)
    if 'learn_mode' in config:
        message = {"mode": "update", "type": "core", "device": {"learn_mode": new_learn_mode}}
    else:
        message = {"mode": "update", "type": "core", "device": {"learn_mode": True}}
    mqtt_client.publish("cubiemedia/command", json.dumps(message))
    time.sleep(1)

    mqtt_client.disconnect()
    return redirect(url_for('index'))


def get_running_applications():
    applications = []
    for service in service_list:
        response = execute_command(["ps", "-ef"]).strip()
        response = response.decode()
        if "mqtt_client.py " + service['id'] in response or "cubiemedia-mqtt-client " + \
                service['id'] in response:
            service['running'] = True
            applications.append(service)
        else:
            service['running'] = False

    return applications


def get_device_list(application):
    config = get_configuration(application)
    if "deviceList" in config:
        return config["deviceList"]
    else:
        return config


def delete_item(application, items):
    config = get_configuration(CUBIE_CORE)
    if not len(items) == 0:
        mqtt_client = connect_mqtt_client(config)
        for item in items:
            message = {"mode": "delete", "type": application, "device": {"id": item}}
            mqtt_client.publish("cubiemedia/command", json.dumps(message))
        mqtt_client.disconnect()


def connect_mqtt_client(config):
    mqtt_server = config['host']
    mqtt_user = config['username']
    mqtt_password = config['password']
    client_id = get_ip_address() + "-web_app-client"
    mqtt_client = mqtt.Client(client_id=client_id, clean_session=True, userdata=None, transport="tcp")
    mqtt_client.username_pw_set(username=mqtt_user, password=mqtt_password)
    mqtt_client.connect(mqtt_server, 1883, 60)

    return mqtt_client


@app.route('/cubie-admin')
def show_administration():
    return render_template('administration.html')


#
#
# this is unused, snap environment does not allow this access
#
#

@app.route('/<application>/start')
def application_start(application):
    logging.info(f"Start Application {application}")
    state = os.system('systemctl enable snap.cubiemedia-mqtt-client.cubiemedia-' + application + " --now")
    if state != 0:
        logging.warning(f"could not enable application {application}")
    return redirect(url_for('index'))


@app.route('/<application>/stop')
def application_stop(application):
    logging.info(f"Stop Application {application}")
    state = os.system('systemctl disable snap.cubiemedia-mqtt-client.cubiemedia-' + application + " --now")
    if state != 0:
        logging.warning(f"could not enable application {application}")
    return redirect(url_for('index'))


@app.route('/<application>/restart')
def application_restart(application):
    logging.info(f"Restart Application {application}")
    state = os.system('systemctl restart snap.cubiemedia-mqtt-client.cubiemedia-' + application)
    if state != 0:
        logging.warning(f"could not enable application {application}")
    return redirect(url_for('index'))


#
#
# end unused
#
#

@app.route('/cubie-admin/reboot')
def system_reboot():
    threading.Timer(3, os.system('reboot'))
    return render_template('reboot.html')


@app.route('/')
def index():
    application_list = get_running_applications()
    core_configuration = get_configuration(CUBIE_CORE)
    learn_mode = core_configuration['learn_mode']
    server = core_configuration['host']
    user = core_configuration['username']

    return render_template('index.html', application_list=application_list, service_list=service_list,
                           ip=get_ip_address(), learn_mode=learn_mode, server=server, user=user)
