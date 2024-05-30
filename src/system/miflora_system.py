import json
import logging
import time

from btlewrap import BluetoothBackendException
from btlewrap.bluepy import BluepyBackend
from miflora.miflora_poller import MiFloraPoller, MI_BATTERY, MI_LIGHT, MI_CONDUCTIVITY, \
    MI_MOISTURE, MI_TEMPERATURE

from common import MQTT_CUBIEMEDIA, CUBIE_MIFLORA, MQTT_HOMEASSISTANT_PREFIX
from common.homeassistant import MQTT_BATTERY, MQTT_TEMPERATURE, MQTT_BRIGHTNESS, MQTT_MOISTURE, \
    MQTT_CONDUCTIVITY, MQTT_UNIT, MQTT_STATE_CLASS, MQTT_DEVICE_CLASS, \
    MQTT_MEASUREMENT, MQTT_SENSOR, PAYLOAD_SPECIAL_SENSOR, MQTT_UNIT_OF_MEASUREMENT, MQTT_NAME, \
    MQTT_STATE_TOPIC, MQTT_AVAILABILITY_TOPIC, MQTT_UNIQUE_ID, MQTT_DEVICE, MQTT_DEVICE_IDS, \
    MQTT_DEVICE_DESCRIPTION
from system.base_system import BaseSystem

MI_TOPIC = "mi_topic"

SERVICES = {
    MQTT_BATTERY: {
        MI_TOPIC: MI_BATTERY,
        MQTT_UNIT: "%",
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: MQTT_BATTERY
    },
    MQTT_TEMPERATURE: {
        MI_TOPIC: MI_TEMPERATURE,
        MQTT_UNIT: "°C",
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: MQTT_TEMPERATURE
    },
    MQTT_BRIGHTNESS: {
        MI_TOPIC: MI_LIGHT,
        MQTT_UNIT: "lx",
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: 'illuminance'
    },
    MQTT_MOISTURE: {
        MI_TOPIC: MI_MOISTURE,
        MQTT_UNIT: "%",
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: None
    },
    MQTT_CONDUCTIVITY: {
        MI_TOPIC: MI_CONDUCTIVITY,
        MQTT_UNIT: "µS/cm",
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: None
    }
}


class MiFloraSystem(BaseSystem):
    update_interval = 3600
    last_update = None

    def __init__(self):
        self.execution_mode = CUBIE_MIFLORA
        super().__init__()

    def init(self):
        super().init()
        self.last_update = time.time() - self.update_interval + 10

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        super().shutdown()

    def action(self, plant: {}):
        logging.info("... ... action for plant [%s]" % plant)
        for key, value in plant['values'].items():
            self.mqtt_client.publish(
                f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{plant['name'].lower().replace(' ', '_')}/{key}",
                value, True)

    def update(self):
        data = {}

        device_list = []
        if self.last_update < time.time() - self.update_interval:
            self.last_update = time.time()

            logging.info('... ... scanning for bluetooth devices')
            try:
                BluepyBackend.scan_for_devices(5)
            except BluetoothBackendException:
                logging.warning("could not scan, maybe a permission problem")
                logging.warning(
                    "sudo setcap 'cap_net_raw,cap_net_admin+eip' [YOUR_PYTHON_VENV]/site-packages/bluepy/bluepy-helper")

            # get data from devices
            for device in self.config:
                mac = device['mac']
                name = device['name'] if 'name' in device else mac
                poller = MiFloraPoller(mac, BluepyBackend)

                # get data
                logging.info('... ... getting data for sensor %s', mac)
                plant = {'mac': mac, 'name': name, 'values': {}}
                try:
                    for service, attributes in SERVICES.items():
                        value = poller.parameter_value(attributes[MI_TOPIC])
                        logging.debug(f"... ... ... received {service} with value [{value}]")
                        plant['values'][service] = value
                    device_list.append(plant)
                except BluetoothBackendException:
                    logging.warning(f"failed connection with Bluetooth Device [{mac}]")
            self.set_availability(True)
        else:
            pass  # no update time, nothing to do

        data['devices'] = device_list
        return data

    def announce(self):
        super().announce()

        for plant in self.config:
            if 'mac' not in plant:
                logging.warning("config entry has no mac, ignoring!")
                continue
            mac = plant['mac']
            plant_name = str(plant['name'] if 'name' in plant else mac)
            string_id = plant_name.lower().replace(' ', '_')
            if string_id != mac:
                plant_name += f" ({plant['mac']})"

            logging.info("... ... announce plant [%s]", plant_name)
            availability_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/online"

            for service, attributes in SERVICES.items():
                state_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/{service}"
                service_name = f"{service.capitalize().replace('_', ' ')}"
                unique_id = f"{string_id}-{self.execution_mode}-{service}"
                config_topic = f"{MQTT_HOMEASSISTANT_PREFIX}/{MQTT_SENSOR}/{string_id}-{service}/config"

                payload = PAYLOAD_SPECIAL_SENSOR
                payload[MQTT_UNIT_OF_MEASUREMENT] = attributes[MQTT_UNIT]
                payload[MQTT_STATE_CLASS] = attributes[MQTT_STATE_CLASS]
                payload[MQTT_DEVICE_CLASS] = attributes[MQTT_DEVICE_CLASS]
                payload[MQTT_NAME] = service_name
                payload[MQTT_STATE_TOPIC] = state_topic
                payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
                payload[MQTT_UNIQUE_ID] = unique_id
                payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = f"{self.execution_mode}-{mac.replace(':', '')}"
                payload[MQTT_DEVICE][MQTT_NAME] = plant_name
                payload[MQTT_DEVICE][
                    MQTT_DEVICE_DESCRIPTION] = f"via Gateway ({self.ip_address})"

                self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)

    def set_availability(self, state: bool):
        super().set_availability(state)
        logging.debug("... ... set availability [%s]", state)
        for plant in self.config:
            string_id = plant['name'].lower().replace(' ', '_') if 'name' in plant else plant['mac']
            availability_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/online"
            self.mqtt_client.publish(availability_topic, str(state).lower())
