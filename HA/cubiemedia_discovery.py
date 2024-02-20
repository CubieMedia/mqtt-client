"""
This script adds MQTT discovery support for CubieMedia devices.
"""
MQTT_SOFTWARE_VERSION = "sw"
MQTT_MANUFACTURER = "mf"
CONF_ID = "id"
CONF_TYPE = "type"
CONF_STATE = "state"
CONF_VALUE = "value"
CONF_CONFIG = "config"
CONF_CLIENT_ID = "client_id"
CONF_DISCOVERY_PREFIX = "discovery_prefix"

CUBIE_TOPIC = "cubiemedia"
CUBIE_TOPIC_COMMAND = CUBIE_TOPIC + "/command"

ATTR_MANUFACTURER = "CubieMedia"
ATTR_MODEL_SWITCH = "rps"
ATTR_MODEL_SWITCH_ARRAY = ["a1", "a2", "b1", "b2"]
ATTR_MODEL_TEMPERATURE = "temp"
ATTR_MODEL_RELAY = "relay"
ATTR_MODEL_RELAY_NAME = "relay_"
ATTR_MODEL_GPIO = "gpio"
ATTR_MODEL_SONAR = "sonar"
ATTR_MODEL_VICTRON = "victron"
ATTR_MODEL_CORE = "core"

ATTR_BATTERY = "battery"
ATTR_POWER = "power"
ATTR_LIGHT = "light"
ATTR_SENSOR = "sensor"
ATTR_SWITCH = "binary_sensor"
ATTR_EX_IMPORTED = "ported"
ATTR_CHARGED = "charged"
ATTR_ENERGY = "energy"
ATTR_MEASUREMENT = "measurement"

MQTT_QOS = "qos"
MQTT_RETAIN = "retain"
MQTT_PAYLOAD = "payload"
MQTT_TOPIC = "topic"
MQTT_NAME = "name"
MQTT_COMMAND_TOPIC = "cmd_t"
MQTT_STATE_TOPIC = "stat_t"
MQTT_AVAILABILITY_TOPIC = "avty_t"
MQTT_UNIQUE_ID = "uniq_id"
MQTT_DEVICE = "dev"
MQTT_DEVICE_IDS = "ids"
MQTT_DEVICE_DESCRIPTION = "mdl"
MQTT_UNIT_OF_MEASUREMENT = "unit_of_measurement"
MQTT_DEVICE_CLASS = "device_class"
MQTT_STATE_CLASS = "state_class"
MQTT_PAYLOAD_NOT_AVAILABLE = "pl_not_avail"
MQTT_PAYLOAD_AVAILABLE = "pl_avail"
MQTT_PAYLOAD_OFF = "pl_off"
MQTT_PAYLOAD_ON = "pl_on"

GPIO_TYPE_IN = "in"
GPIO_TYPE_OUT = "out"

DEFAULT_DISC_PREFIX = "homeassistant"

PAYLOAD_ACTOR = {
    MQTT_NAME: "SERVICE_NAME",
    MQTT_COMMAND_TOPIC: "STATE_TOPIC/command",
    MQTT_STATE_TOPIC: "STATE_TOPIC",
    MQTT_AVAILIBILITY_TOPIC: "AVAILABILITY_TOPIC",
    MQTT_PAYLOAD_ON: "1", MQTT_PAYLOAD_OFF: "0", MQTT_PAYLOAD_AVAILABLE: "true", MQTT_PAYLOAD_NOT_AVAILABLE: "false",
    MQTT_UNIQUE_ID: "UNIQUE_ID",
    MQTT_QOS: "0",
    MQTT_DEVICE: {
        MQTT_DEVICE_IDS: ["DEVICE_ID"],
        MQTT_NAME: "DEVICE_NAME",
        MQTT_DEVICE_DESCRIPTION: "DEVICE_DESCRIPTION",
        MQTT_SOFTWARE_VERSION: "SW",
        MQTT_MANUFACTURER: ATTR_MANUFACTURER
    }
}

PAYLOAD_SENSOR = {
    MQTT_NAME: "SERVICE_NAME",
    MQTT_STATE_TOPIC: "STATE_TOPIC",
    MQTT_AVAILIBILITY_TOPIC: "AVAILABILITY_TOPIC",
    MQTT_PAYLOAD_ON: "1", MQTT_PAYLOAD_OFF: "0", MQTT_PAYLOAD_AVAILABLE: "true", MQTT_PAYLOAD_NOT_AVAILABLE: "false",
    MQTT_UNIQUE_ID: "UNIQUE_ID",
    MQTT_QOS: "0",
    MQTT_DEVICE: {
        MQTT_DEVICE_IDS: ["DEVICE_ID"],
        MQTT_NAME: "DEVICE_NAME",
        MQTT_DEVICE_DESCRIPTION: "DEVICE_DESCRIPTION",
        MQTT_SOFTWARE_VERSION: "SW",
        MQTT_MANUFACTURER: ATTR_MANUFACTURER
    }
}
PAYLOAD_SPECIAL_ACTOR = {
    MQTT_NAME: "SERVICE_NAME",
    MQTT_COMMAND_TOPIC: "STATE_TOPIC/command",
    MQTT_STATE_TOPIC: "STATE_TOPIC",
    MQTT_AVAILIBILITY_TOPIC: "AVAILABILITY_TOPIC",
    MQTT_UNIT_OF_MEASUREMENT: "UNIT_OF_MEASUREMENT",
    MQTT_STATE_CLASS: "STATE_CLASS",
    MQTT_DEVICE_CLASS: "DEVICE_CLASS",
    MQTT_PAYLOAD_ON: "1", MQTT_PAYLOAD_OFF: "0", MQTT_PAYLOAD_AVAILABLE: "true", MQTT_PAYLOAD_NOT_AVAILABLE: "false",
    MQTT_UNIQUE_ID: "UNIQUE_ID",
    MQTT_QOS: "0",
    MQTT_DEVICE: {
        MQTT_DEVICE_IDS: ["DEVICE_ID"],
        MQTT_NAME: "DEVICE_NAME",
        MQTT_DEVICE_DESCRIPTION: "DEVICE_DESCRIPTION",
        MQTT_SOFTWARE_VERSION: "SW",
        MQTT_MANUFACTURER: ATTR_MANUFACTURER
    }
}


def mqtt_publish(topic, payload_to_publish):
    """Publish data to MQTT broker."""
    payload_str = str(payload_to_publish).replace("'", '"').replace("True", 'true')
    service_data = {
        "topic": topic,
        "payload": payload_str,
        "retain": retain,
        MQTT_QOS: qos,
    }
    logger.debug(service_data)  # noqa: F821
    hass.services.call("mqtt", "publish", service_data, False)  # noqa: F821


retain = False
qos = 0

device_payload = data.get(MQTT_PAYLOAD)

device_id = device_payload.get(CONF_ID)
string_id = device_id.replace('.', '_')
device_type = str(device_payload.get(CONF_TYPE)).lower()
plugin_type = device_type
device_state = device_payload.get(CONF_STATE)
client_id = device_payload.get(CONF_CLIENT_ID)
success = False

if not device_id:
    raise ValueError(f"{device_payload} is wrong device_id argument")
if not device_type:
    raise ValueError(f"{device_payload} is wrong device_type argument")

logger.debug("device: %s", device_payload)

disc_prefix = data.get(CONF_DISCOVERY_PREFIX, DEFAULT_DISC_PREFIX)

logger.info("add new %s [%s] to homeassistant" % (device_type, device_id))

# EnOcean Devices
if ATTR_MODEL_SWITCH == device_type:
    plugin_type = "enocean"
    for sensorId in range(0, 4):
        device_name = f"EnOcean Switch {device_id}"
        sensor_name = f"Sensor {ATTR_MODEL_SWITCH_ARRAY[sensorId].title()}"
        unique_id = f"enocean-{device_id}-{ATTR_MODEL_SWITCH_ARRAY[sensorId]}-input"
        config_topic = f"{disc_prefix}/binary_sensor/{device_id}-{ATTR_MODEL_SWITCH_ARRAY[sensorId]}/config"
        config_topic_longpush = f"{disc_prefix}/binary_sensor/{device_id}-{ATTR_MODEL_SWITCH_ARRAY[sensorId]}-longpush/config"
        state_topic = f"{CUBIE_TOPIC}/{plugin_type}/{device_id}/{ATTR_MODEL_SWITCH_ARRAY[sensorId]}"
        availability_topic = f"{CUBIE_TOPIC}/{plugin_type}/{device_id}/online"
        payload = PAYLOAD_SENSOR
        payload[MQTT_NAME] = sensor_name
        payload[MQTT_STATE_TOPIC] = state_topic
        payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
        payload[MQTT_UNIQUE_ID] = unique_id
        payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device_id
        payload[MQTT_DEVICE][MQTT_NAME] = device_name

        mqtt_publish(config_topic, payload)

        # also create longpush sensor for all normal sensors
        payload = PAYLOAD_SENSOR
        payload[MQTT_NAME] = sensor_name + "-longpush"
        payload[MQTT_STATE_TOPIC] = state_topic + "/longpush"
        payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
        payload[MQTT_UNIQUE_ID] = unique_id + "_longpush"
        payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device_id
        payload[MQTT_DEVICE][MQTT_NAME] = device_name

        mqtt_publish(config_topic_longpush, payload)
    success = True
# Relay Boards
elif ATTR_MODEL_RELAY in device_type:
    if len(device_id.split('.')) == 4:
        device_name = "Relayboard {}".format(device_id)
        for relay_id in device_state:
            relay_name = "Relay {}-{}".format(device_id, relay_id)
            state_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/{relay_id}"
            unique_id = f"{string_id}-light-{relay_id}"
            config_topic = f"{disc_prefix}/{ATTR_LIGHT}/{string_id}-{relay_id}/config"
            availability_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/online"

            payload = PAYLOAD_ACTOR
            payload[MQTT_NAME] = relay_name
            payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"
            payload[MQTT_STATE_TOPIC] = state_topic
            payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
            payload[MQTT_UNIQUE_ID] = unique_id
            payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = [device_id]
            payload[MQTT_DEVICE][MQTT_NAME] = device_name

            mqtt_publish(config_topic, payload)
        success = True
    else:
        logger.error("relay device id is incorrect [%s]" % device_id)
elif ATTR_MODEL_GPIO == device_type:
    if len(device_id.split('.')) == 4:
        for gpio in device_state:
            # {"id": 15, "type": "in", "value": 0}
            device_name = f"GPIO Device {device_id}"
            state_topic = f"{CUBIE_TOPIC}/gpio/{string_id}/{gpio['id']}"
            availability_topic = f"{CUBIE_TOPIC}/gpio/{string_id}/online"
            if gpio[CUBIE_TYPE] == GPIO_TYPE_OUT:
                gpio_name = f"Output {gpio['id']}"
                unique_id = f"{string_id}-out-{gpio['id']}"
                config_topic = f"{disc_prefix}/{ATTR_LIGHT}/{string_id}-{gpio['id']}/config"

                payload = PAYLOAD_ACTOR
                payload[MQTT_NAME] = gpio_name
                payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"
                payload[MQTT_STATE_TOPIC] = state_topic
                payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
                payload[MQTT_UNIQUE_ID] = unique_id
                payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device_id
                payload[MQTT_DEVICE][MQTT_NAME] = device_name
            elif gpio[CUBIE_TYPE] == GPIO_TYPE_IN:
                gpio_name = f"Input {gpio['id']}"
                unique_id = f"{string_id}-in-{gpio['id']}"
                config_topic = f"{disc_prefix}/binary_sensor/{string_id}-{gpio['id']}/config"

                payload = PAYLOAD_SENSOR
                payload[MQTT_NAME] = gpio_name
                payload[MQTT_STATE_TOPIC] = state_topic
                payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
                payload[MQTT_UNIQUE_ID] = unique_id
                payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device_id
                payload[MQTT_DEVICE][MQTT_NAME] = device_name
            else:
                continue
            mqtt_publish(config_topic, payload)
        success = True
    else:
        logger.error("gpio device id is incorrect [%s]" % device_id)
elif ATTR_MODEL_SONAR == device_type:
    if len(device_id.split('.')) == 4:
        device_name = f"Sonar Device {device_id}"
        availability_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/online"

        for sensor_name in ["distance", "percent"]:
            unique_id = f"{device_name}-{sensor_name}-sensor"
            state_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/{sensor_name}"
            config_topic = f"{disc_prefix}/{ATTR_SENSOR}/{string_id}-{sensor_name}/config"

            payload = PAYLOAD_SENSOR
            payload[MQTT_NAME] = sensor_name.title()
            payload[MQTT_STATE_TOPIC] = state_topic
            payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
            payload[MQTT_UNIQUE_ID] = unique_id
            payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device_id
            payload[MQTT_DEVICE][MQTT_NAME] = device_name
            mqtt_publish(config_topic, payload)

        success = True
    else:
        logger.error("sonar device id is incorrect [%s]" % device_id)
elif ATTR_MODEL_VICTRON == device_type:
    device_name = f"Victron MQTT Gateway {device_id}"
    service_list = device_state
    availability_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/online"

    for service in service_list:
        state_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/{service}"
        service_name = f"Victron {device_id}-{service}"
        unique_id = f"{string_id}-{device_type}-{service}"
        if ATTR_BATTERY in service or ATTR_EX_IMPORTED in service:
            if ATTR_POWER in service:
                unit = "W"
                state_class = ATTR_MEASUREMENT
                device_class = ATTR_POWER
            elif ATTR_CHARGED in service or ATTR_EX_IMPORTED in service:
                unit = "kWh"
                state_class = "total_increasing"
                device_class = ATTR_ENERGY
            else:
                unit = "%"
                state_class = ATTR_MEASUREMENT
                device_class = ATTR_BATTERY
            config_topic = f"{disc_prefix}/{ATTR_SENSOR}/{string_id}-{service}/config"
            payload = PAYLOAD_SPECIAL_ACTOR
            payload[MQTT_NAME] = service_name
            payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"
            payload[MQTT_STATE_TOPIC] = state_topic
            payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
            payload[MQTT_UNIT_OF_MEASUREMENT] = unit
            payload[MQTT_STATE_CLASS] = state_class
            payload[MQTT_DEVICE_CLASS] = device_class
            payload[MQTT_UNIQUE_ID] = unique_id
            payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device_id
            payload[MQTT_DEVICE][MQTT_NAME] = device_name
        else:
            if "allow" in service:
                config_topic = f"{disc_prefix}/{ATTR_LIGHT}/{string_id}-{service}/config"
            else:
                config_topic = f"{disc_prefix}/{ATTR_SWITCH}/{string_id}-{service}/config"
            payload = PAYLOAD_ACTOR
            payload[MQTT_NAME] = service_name
            payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"
            payload[MQTT_STATE_TOPIC] = state_topic
            payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
            payload[MQTT_UNIQUE_ID] = unique_id
            payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device_id
            payload[MQTT_DEVICE][MQTT_NAME] = device_name

        mqtt_publish(config_topic, payload)
    success = True
elif ATTR_MODEL_CORE == device_type:
    # do not create core devices in home assistant
    success = True
else:
    logger.error("unknown type [%s] with device [%s]" % (device_type, device_payload))

if success:
    payload = {"mode": "update", "type": plugin_type, "device": device_payload}
    mqtt_publish(CUBIE_TOPIC_COMMAND, payload)
