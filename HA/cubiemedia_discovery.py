"""
This script adds MQTT discovery support for CubieMedia devices.
"""

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

DEFAULT_DISC_PREFIX = "homeassistant"

MQTT_QOS = "qos"
MQTT_RETAIN = "retain"
MQTT_PAYLOAD = "payload"
MQTT_TOPIC = "topic"

PAYLOAD_ACTOR = ('{"name":"SERVICE_NAME","cmd_t":"STATE_TOPIC/command","stat_t":"STATE_TOPIC","avty_t":"AVAILABILITY_TOPIC","pl_on":"1","pl_off":"0","pl_avail":"true","pl_not_avail":"false","uniq_id":"UNIQUE_ID","qos":"0","dev": {"ids": ["DEVICE_ID"],"name":"DEVICE_NAME","mdl":"DEVICE_DESCRIPTION","sw":"SW","mf":"' + ATTR_MANUFACTURER + '"}}')
PAYLOAD_SENSOR = ('{"name":"SERVICE_NAME","stat_t":"STATE_TOPIC","avty_t":"AVAILABILITY_TOPIC","pl_on":"1","pl_off":"0","pl_avail":"true","pl_not_avail":"false","uniq_id":"UNIQUE_ID","qos":"0","dev": {"ids": ["DEVICE_ID"],"name":"DEVICE_NAME","mdl":"DEVICE_DESCRIPTION","sw":"SW","mf":"' + ATTR_MANUFACTURER + '"}}')
PAYLOAD_SPECIAL_ACTOR = ('{"name":"SERVICE_NAME","cmd_t":"STATE_TOPIC/command","stat_t":"STATE_TOPIC","avty_t":"AVAILABILITY_TOPIC","unit_of_measurement":"UNIT_OF_MEASUREMENT","state_class":"STATE_CLASS","device_class":"DEVICE_CLASS","pl_on":"1","pl_off":"0","pl_avail":"true","pl_not_avail":"false","uniq_id":"UNIQUE_ID","qos":"0","dev": {"ids": ["DEVICE_ID"],"name":"DEVICE_NAME","mdl":"DEVICE_DESCRIPTION","sw":"SW","mf":"' + ATTR_MANUFACTURER + '"}}')

expire_after = 43200
off_delay = 3

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
    raise ValueError(f"{device_id} is wrong device_id argument")
if not device_type:
    raise ValueError(f"{device_type} is wrong device_type argument")
if not client_id:
    raise ValueError(f"{client_id} is wrong client_id argument")

logger.debug("device: %s", device_payload)

disc_prefix = data.get(CONF_DISCOVERY_PREFIX, DEFAULT_DISC_PREFIX)

logger.info("add new %s [%s] to homeassistant" % (device_type, device_id))

# EnOcean Devices
if ATTR_MODEL_SWITCH == device_type:
    plugin_type = "enocean"
    for sensorId in range(0, 4):
        device_name = "EnOcean Switch {}".format(device_id)
        sensor_name = "Sensor {}".format(ATTR_MODEL_SWITCH_ARRAY[sensorId].title())
        unique_id = "enocean-{}-{}-input".format(device_id, ATTR_MODEL_SWITCH_ARRAY[sensorId])
        config_topic = "{}/binary_sensor/{}-{}/config".format(
            disc_prefix, device_id, ATTR_MODEL_SWITCH_ARRAY[sensorId]
        )
        config_topic_longpush = "{}/binary_sensor/{}-{}-longpush/config".format(
            disc_prefix, device_id, ATTR_MODEL_SWITCH_ARRAY[sensorId]
        )
        state_topic = "{}/{}/{}/{}".format(CUBIE_TOPIC, plugin_type, device_id, ATTR_MODEL_SWITCH_ARRAY[sensorId])
        availability_topic = "{}/{}/{}/online".format(CUBIE_TOPIC, plugin_type, device_id)
        payload = PAYLOAD_SENSOR
        payload.replace('SERVICE_NAME', sensor_name)
        payload.replace('STATE_TOPIC', state_topic)
        payload.replace('AVAILABILITY_TOPIC', availability_topic)
        payload.replace('UNIQUE_ID', unique_id)
        payload.replace('DEVICE_ID', device_id)
        payload.replace('DEVICE_NAME', device_name)

        service_data = {
            MQTT_TOPIC: config_topic,
            MQTT_PAYLOAD: payload,
            MQTT_RETAIN: retain,
            MQTT_QOS: qos,
        }
        hass.services.call("mqtt", "publish", service_data, False)

        # also create longpush sensor for all normal sensors
        payload.replace('SERVICE_NAME', sensor_name + '-longpush",')
        payload.replace('STATE_TOPIC', state_topic + '/longpush",')
        payload.replace('UNIQUE_ID', unique_id + '_longpush",')

        service_data['payload'] = payload
        hass.services.call("mqtt", "publish", service_data, False)
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
            payload.replace('SERVICE_NAME', relay_name)
            payload.replace('STATE_TOPIC', state_topic)
            payload.replace('AVAILABILITY_TOPIC', availability_topic)
            payload.replace('UNIQUE_ID', unique_id)
            payload.replace('DEVICE_ID', device_id)
            payload.replace('DEVICE_NAME', device_name)

            service_data = {
                MQTT_TOPIC: config_topic,
                MQTT_PAYLOAD: payload,
                MQTT_RETAIN: retain,
                MQTT_QOS: qos,
            }
            hass.services.call("mqtt", "publish", service_data, False)
        success = True
    else:
        logger.error("relay device id is incorrect [%s]" % device_id)
elif ATTR_MODEL_GPIO == device_type:
    if len(device_id.split('.')) == 4:
        for gpio in device_state:
            # {"id": 15, "type": "in", "value": 0}
            device_name = "GPIO Device {}".format(device_id)
            state_topic = f"{CUBIE_TOPIC}/gpio/{string_id}/{gpio['id']}"
            availability_topic = f"{CUBIE_TOPIC}/gpio/{string_id}/online"
            if gpio['type'] == "out":
                gpio_name = "Output {}".format(gpio['id'])
                unique_id = f"{string_id}-out-{gpio['id']}"
                config_topic = f"{disc_prefix}/{ATTR_LIGHT}/{string_id}-{gpio['id']}/config"

                payload = PAYLOAD_ACTOR
                payload.replace('SERVICE_NAME', gpio_name)
                payload.replace('STATE_TOPIC', state_topic)
                payload.replace('AVAILABILITY_TOPIC', availability_topic)
                payload.replace('UNIQUE_ID', unique_id)
                payload.replace('DEVICE_ID', device_id)
                payload.replace('DEVICE_NAME', device_name)
            elif gpio['type'] == "in":
                gpio_name = "Input {}".format(gpio['id'])
                unique_id = f"{string_id}-in-{gpio['id']}"
                config_topic = f"{disc_prefix}/binary_sensor/{string_id}-{gpio['id']}/config"

                payload = PAYLOAD_SENSOR
                payload.replace('SERVICE_NAME', gpio_name)
                payload.replace('STATE_TOPIC', state_topic)
                payload.replace('AVAILABILITY_TOPIC', availability_topic)
                payload.replace('UNIQUE_ID', unique_id)
                payload.replace('DEVICE_ID', device_id)
                payload.replace('DEVICE_NAME', device_name)
            service_data = {
                MQTT_TOPIC: config_topic,
                MQTT_PAYLOAD: payload,
                MQTT_RETAIN: retain,
                MQTT_QOS: qos,
            }
            hass.services.call("mqtt", "publish", service_data, False)
        success = True
    else:
        logger.error("gpio device id is incorrect [%s]" % device_id)
elif ATTR_MODEL_SONAR == device_type:
    if len(device_id.split('.')) == 4:
        device_name = "Sonar Device {}".format(device_id)
        availability_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/online"

        for sensor_name in ["distance", "percent"]:
            unique_id = f"{device_name}-{sensor_name}-sensor"
            state_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/{sensor_name}"
            config_topic = f"{disc_prefix}/{ATTR_SENSOR}/{string_id}-{sensor_name}/config"

            payload = PAYLOAD_SENSOR
            payload.replace('SERVICE_NAME', sensor_name.title())
            payload.replace('STATE_TOPIC', state_topic)
            payload.replace('AVAILABILITY_TOPIC', availability_topic)
            payload.replace('UNIQUE_ID', unique_id)
            payload.replace('DEVICE_ID', device_id)
            payload.replace('DEVICE_NAME', device_name)
            service_data = {
                MQTT_TOPIC: config_topic,
                MQTT_PAYLOAD: payload,
                MQTT_RETAIN: retain,
                MQTT_QOS: qos,
            }
            hass.services.call("mqtt", "publish", service_data, False)

        success = True
    else:
        logger.error("sonar device id is incorrect [%s]" % device_id)
elif ATTR_MODEL_VICTRON == device_type:
    device_name = "Victron MQTT Gateway {}".format(device_id)
    service_list = device_state
    availability_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/online"

    for service in service_list:
        state_topic = f"{CUBIE_TOPIC}/{device_type}/{string_id}/{service}"
        service_name = "Victron {}-{}".format(device_id, service)
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
            payload.replace('SERVICE_NAME', service_name)
            payload.replace('STATE_TOPIC', state_topic)
            payload.replace('AVAILABILITY_TOPIC', availability_topic)
            payload.replace('UNIT_OF_MEASUREMENT', unit)
            payload.replace('STATE_CLASS', state_class)
            payload.replace('DEVICE_CLASS', device_class)
            payload.replace('UNIQUE_ID', unique_id)
            payload.replace('DEVICE_ID', device_id)
            payload.replace('DEVICE_NAME', device_name)
        else:
            if "allow" in service:
                config_topic = f"{disc_prefix}/{ATTR_LIGHT}/{string_id}-{service}/config"
            else:
                config_topic = f"{disc_prefix}/{ATTR_SWITCH}/{string_id}-{service}/config"
            payload = PAYLOAD_ACTOR
            payload.replace('SERVICE_NAME', service_name)
            payload.replace('STATE_TOPIC', state_topic)
            payload.replace('AVAILABILITY_TOPIC', availability_topic)
            payload.replace('UNIQUE_ID', unique_id)
            payload.replace('DEVICE_ID', device_id)
            payload.replace('DEVICE_NAME', device_name)

        service_data = {
            MQTT_TOPIC: config_topic,
            MQTT_PAYLOAD: payload,
            MQTT_RETAIN: retain,
            MQTT_QOS: qos,
        }
        # logger.error(config_topic)
        hass.services.call("mqtt", "publish", service_data, False)
    success = True
elif ATTR_MODEL_CORE == device_type:
    # do not create core devices in home assistant
    success = True
else:
    logger.error("unkown type [%s] with device [%s]" % (device_type, device_payload))

if success:
    payload = (
            '{"mode":"update", "type": "' + str(plugin_type) +
            '","device":' + str(device_payload).replace('\'', '"').replace('True', 'true') + '}'
    )

    service_data = {
        MQTT_TOPIC: CUBIE_TOPIC_COMMAND,
        MQTT_PAYLOAD: payload,
        MQTT_RETAIN: retain,
        MQTT_QOS: qos,
    }
    hass.services.call("mqtt", "publish", service_data, False)
