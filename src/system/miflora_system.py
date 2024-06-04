import asyncio
import json
import logging
import threading
import time

from bleak import BleakScanner, BLEDevice, AdvertisementData, BleakClient, BleakGATTCharacteristic
from miflora.miflora_poller import MI_BATTERY, MI_LIGHT, MI_CONDUCTIVITY, \
    MI_MOISTURE, MI_TEMPERATURE

from common import MQTT_CUBIEMEDIA, CUBIE_MIFLORA, MQTT_HOMEASSISTANT_PREFIX, TIMEOUT_UPDATE_MIFLORA
from common.homeassistant import MQTT_BATTERY, MQTT_TEMPERATURE, MQTT_BRIGHTNESS, MQTT_MOISTURE, \
    MQTT_CONDUCTIVITY, MQTT_UNIT, MQTT_STATE_CLASS, MQTT_DEVICE_CLASS, \
    MQTT_MEASUREMENT, MQTT_SENSOR, PAYLOAD_SPECIAL_SENSOR, MQTT_UNIT_OF_MEASUREMENT, MQTT_NAME, \
    MQTT_STATE_TOPIC, MQTT_AVAILABILITY_TOPIC, MQTT_UNIQUE_ID, MQTT_DEVICE, MQTT_DEVICE_IDS, \
    MQTT_DEVICE_DESCRIPTION
from common.miflora import XIAOMI_FLOWER_CARE_DISCOVERY, XIAOMI_DEVICE_MODE_CHANGE, \
    XIAOMI_REAL_TIME_DATA_UUID
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

devices = {}


class MiFloraSystem(BaseSystem):
    last_update = None
    scan_thread = None

    def __init__(self):
        self.execution_mode = CUBIE_MIFLORA
        super().__init__()

    def init(self):
        super().init()

        for device in self.config:
            devices[device['id']] = {}

        self.last_update = time.time() - TIMEOUT_UPDATE_MIFLORA + 5
        self.scan_thread = threading.Thread(target=self._run)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        if self.scan_thread.is_alive():
            logging.info("... stopping scan thread...")
            self.scan_thread_event.set()
            self.scan_thread.join()

        super().shutdown()

    def action(self, plant: {}):
        logging.info("... ... action for plant [%s]" % plant)
        for key, value in plant['state'].items():
            plant_name = str(plant['name'] if 'name' in plant else plant['id'])
            plant_name = plant_name.lower().replace(' ', '_')
            self.mqtt_client.publish(f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{plant_name}/{key}",
                                     value, True)

    def update(self):
        data = {}

        if self.last_update < time.time() - TIMEOUT_UPDATE_MIFLORA:
            self.last_update = time.time()

            device_found = False
            device_list = []
            for device_mac in devices.keys():
                for device in self.config:
                    mac_address = device['id']
                    if device_mac == mac_address:
                        self._read(mac_address)
                        if 'state' in devices[mac_address]:
                            device['state'] = devices[mac_address]['state']
                            device_list.append(device)
                        device_found = True

                if not device_found:
                    self._read(device_mac)
                    device = devices[device_mac]
                    device['id'] = device_mac
                    self.save(devices[device_mac])
                else:
                    self.set_availability(True)
            data['devices'] = device_list
        else:
            if time.time() - self.last_update % 180 == 0:
                self.set_availability(True)

        return data

    def announce(self):
        super().announce()

        for plant in self.config:
            if 'id' not in plant:
                logging.warning("config entry has no mac, ignoring!")
                continue
            mac = plant['id']
            plant_name = str(plant['name'] if 'name' in plant else mac)
            string_id = plant_name.lower().replace(' ', '_')
            if string_id != mac:
                plant_name += f" ({plant['id']})"

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
                payload[MQTT_DEVICE][
                    MQTT_DEVICE_IDS] = f"{self.execution_mode}-{mac.replace(':', '')}"
                payload[MQTT_DEVICE][MQTT_NAME] = plant_name
                payload[MQTT_DEVICE][
                    MQTT_DEVICE_DESCRIPTION] = f"via Gateway ({self.ip_address})"

                self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)

    def set_availability(self, state: bool):
        super().set_availability(state)
        logging.debug("... ... set availability [%s]", state)
        for plant in self.config:
            string_id = plant['name'].lower().replace(' ', '_') if 'name' in plant else plant['id']
            availability_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/online"
            self.mqtt_client.publish(availability_topic, str(state).lower())

    def _run(self):
        self.scan_thread_event = threading.Event()

        asyncio.run(
            _run([XIAOMI_FLOWER_CARE_DISCOVERY], self._check_device, self.scan_thread_event))

    @staticmethod
    def _read(device):
        asyncio.run(_read(device))

    def _check_device(self, device: BLEDevice, advertisement_data: AdvertisementData):
        for service, value in advertisement_data.service_data.items():
            if service == XIAOMI_FLOWER_CARE_DISCOVERY:
                if device.address not in devices:
                    logging.info("... ... found new device: %s, %s", device.name, device.address)
                    devices[device.address] = {}
                    self.last_update = 0
                return
            else:
                logging.warning("Recieved Data from %s: %s", device.address, advertisement_data)

        logging.info("%s: %s", device.address, advertisement_data)


async def _run(service_list, callback, thread_event):
    scanner = BleakScanner(callback, service_list)

    logging.info(f"... starting scanner for [{service_list}]")
    await scanner.start()
    while not thread_event.is_set():
        await asyncio.sleep(3)

    logging.info("... stopping scanner")
    await scanner.stop()


async def _read(device):
    def _notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
        """Simple notification handler which prints the data received."""
        temp, light, moisture, conductivity = _handle_data(data)
        logging.info(
            f"... ... data received - Temp: {temp}, Light: {light}, Moisture: {moisture}, Conductivity: {conductivity}")
        devices[device]['state'] = {"temperature": temp, "brightness": light, "moisture": moisture,
                                    "conductivity": conductivity}

    try:
        async with BleakClient(device) as client:
            logging.debug(f"... ... connected to {client.address}")
            await client.write_gatt_char(XIAOMI_DEVICE_MODE_CHANGE, bytearray([0xa0, 0x1f]))

            await client.start_notify(XIAOMI_REAL_TIME_DATA_UUID, _notification_handler)
            await asyncio.sleep(2.0)
            await client.stop_notify(XIAOMI_REAL_TIME_DATA_UUID)
    except:
        pass


def _handle_data(byte_array: bytearray):
    _BYTE_ORDER = "little"
    temperature = int.from_bytes(byte_array[:2], _BYTE_ORDER) / 10.0
    light = int.from_bytes(byte_array[3:7], _BYTE_ORDER)
    moisture = byte_array[7]
    conductivity = int.from_bytes(byte_array[8:10], _BYTE_ORDER)

    return temperature, light, moisture, conductivity
