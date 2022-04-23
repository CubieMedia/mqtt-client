import json
import os
import sys
import threading
import time

import paho.mqtt.client as mqtt
from werkzeug.utils import redirect

sys.path.append('/usr/lib/cubiemedia/')
sys.path.append('../lib/cubiemedia/')

from flask import Flask, url_for, render_template
from cubiemedia_common import get_ip_address # noqa

app = Flask(__name__)
service_list = {"cubiemedia-io": "CubieMedia-IO", "cubiemedia-enocean": "CubieMedia-EnOcean",
                "cubiemedia-relay": "CubieMedia-Relay"}


@app.route('/show/<application>')
def show_application(application):
    config = get_config(application)
    return render_template('application.html', application=application, device_list=get_device_list(application),
                           learn_mode=config['learn_mode'])


@app.route('/delete/<application>/<item>')
def remove_item_from_application(application, item):
    config = get_config(application)

    device_list = get_device_list(application)
    if item == "all":
        delete_item(config, [device['id'] for device in device_list])
    else:
        delete_item(config, [item])

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


@app.route('/function/<application>/learn_mode')
def switch_learn_mode(application):
    config = get_config(application)
    mqtt_client = connect_mqtt_client(config)
    message = {"mode": "update", "learn_mode": not bool(config['learn_mode'])}
    mqtt_client.publish("cubiemedia/command", json.dumps(message))

    time.sleep(1)

    return redirect(url_for('show_application', application=application))


def get_running_applications():
    applications = {}
    for service in service_list:
        state = os.system('systemctl is-active --quiet ' + service)
        if state == 0:
            applications[service] = service_list[service]

    if len(applications) == 0:
        return service_list
    return applications


def get_device_list(application):
    config = get_config(application)
    if "deviceList" in config:
        return config["deviceList"]
    else:
        return config


def get_config(application):
    config = {"deviceList": []}
    try:
        path = get_path(application)
        if path:
            with open(path) as json_file:
                config = json.load(json_file)
    except FileNotFoundError:
        print("could not load config")
    finally:
        return config


def get_path(application):
    if application == "cubiemedia-io":
        return './gpioList.json'
    elif application == "cubiemedia-enocean":
        return './deviceList.json'
    elif application == "cubiemedia-relay":
        return './relayList.json'
    else:
        return None


def delete_item(config, items):
    if not len(items) == 0:
        mqtt_client = connect_mqtt_client(config)
        for item in items:
            message = {"mode": "delete", "device": {"id": item}}
            mqtt_client.publish("cubiemedia/command", json.dumps(message))


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
    return render_template('administration.html', url_reboot=url_for('system_reboot'))


@app.route('/cubie-admin/reboot')
def system_reboot():
    threading.Timer(3, os.system('reboot'))
    return render_template('reboot.html')


@app.route('/')
def index():
    response = '<h1>Running Applications:</h1>'
    application_list = get_running_applications()
    for application in application_list:
        response += '<p><a href="' + url_for('show_application', application=application) + '">' + application_list[
            application] + '</a>'
    response += '<p><a href="' + url_for('show_administration') + '">Cubie-Administration</a>'
    return response
