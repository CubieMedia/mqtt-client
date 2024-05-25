from common import VERSION, CUBIEMEDIA

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
MQTT_SOFTWARE_VERSION = "sw"
MQTT_MANUFACTURER = "mf"
MQTT_CONFIG_TOPIC = "config_topic"
MQTT_SUGGESTED_DISPLAY_PRECISION = "sug_dsp_prc"
MQTT_BATTERY = "battery"
MQTT_TEMPERATURE = "temperature"
MQTT_BRIGHTNESS = "brightness"
MQTT_MOISTURE = 'moisture'
MQTT_CONDUCTIVITY = 'conductivity'
MQTT_POWER = "power"
MQTT_UNIT = "unit"
MQTT_LIGHT = "light"
MQTT_CLIMATE = "climate"
MQTT_SENSOR = "sensor"
MQTT_BUTTON = "button"
MQTT_SWITCH = "switch"
MQTT_BINARY_SENSOR = "binary_sensor"
MQTT_ENERGY = "energy"
MQTT_MEASUREMENT = "measurement"
MQTT_TOTAL_INCREASING = "total_increasing"
VICTRON_MQTT_TOPIC = "victron_mqtt_topic"

PAYLOAD_SPA_ACTOR = {
    MQTT_NAME: "SERVICE_NAME",
    MQTT_COMMAND_TOPIC: "STATE_TOPIC/command",
    MQTT_STATE_TOPIC: "STATE_TOPIC",
    MQTT_AVAILABILITY_TOPIC: "AVAILABILITY_TOPIC",
    MQTT_PAYLOAD_AVAILABLE: "true",
    MQTT_PAYLOAD_NOT_AVAILABLE: "false",
    MQTT_UNIQUE_ID: "UNIQUE_ID",
    "action_topic": "cubiemedia/balboa/10_10_23_20/heating",
    "action_template": "{%if value==0%}off{%else%}heating{%endif%}",
    "mode_command_topic": "cubiemedia/balboa/10_10_23_20/temperature_control/command",
    "mode_state_topic": "cubiemedia/balboa/10_10_23_20/temperature_control",
    "current_temperature_topic": "cubiemedia/balboa/10_10_23_20/current_temperature",
    "temperature_state_topic": "cubiemedia/balboa/10_10_23_20/target_temperature",
    "temperature_command_topic": "cubiemedia/balboa/10_10_23_20/target_temperature/command",
    "temp_step": 0.5,
    "max_temp": 40,
    "min_temp": 10,
    "modes": [
        "heat",
        "auto",
        "off"
    ],
    MQTT_QOS: "0",
    MQTT_DEVICE: {
        MQTT_DEVICE_IDS: ["DEVICE_ID"],
        MQTT_NAME: "DEVICE_NAME",
        MQTT_DEVICE_DESCRIPTION: "DEVICE_DESCRIPTION",
        MQTT_SOFTWARE_VERSION: VERSION,
        MQTT_MANUFACTURER: CUBIEMEDIA
    }
}
PAYLOAD_SWITCH_ACTOR = {
    MQTT_NAME: "SERVICE_NAME",
    MQTT_COMMAND_TOPIC: "STATE_TOPIC/command",
    MQTT_STATE_TOPIC: "STATE_TOPIC",
    MQTT_AVAILABILITY_TOPIC: "AVAILABILITY_TOPIC",
    MQTT_PAYLOAD_ON: "1",
    MQTT_PAYLOAD_OFF: "0",
    MQTT_PAYLOAD_AVAILABLE: "true",
    MQTT_PAYLOAD_NOT_AVAILABLE: "false",
    MQTT_UNIQUE_ID: "UNIQUE_ID",
    MQTT_QOS: "0",
    MQTT_DEVICE: {
        MQTT_DEVICE_IDS: ["DEVICE_ID"],
        MQTT_NAME: "DEVICE_NAME",
        MQTT_DEVICE_DESCRIPTION: "DEVICE_DESCRIPTION",
        MQTT_SOFTWARE_VERSION: VERSION,
        MQTT_MANUFACTURER: CUBIEMEDIA
    }
}
PAYLOAD_BUTTON = {
    MQTT_NAME: "SERVICE_NAME",
    MQTT_COMMAND_TOPIC: "STATE_TOPIC/command",
    MQTT_AVAILABILITY_TOPIC: "AVAILABILITY_TOPIC",
    MQTT_PAYLOAD_ON: "1",
    MQTT_PAYLOAD_OFF: "0",
    MQTT_PAYLOAD_AVAILABLE: "true",
    MQTT_PAYLOAD_NOT_AVAILABLE: "false",
    MQTT_UNIQUE_ID: "UNIQUE_ID",
    MQTT_QOS: "0",
    MQTT_DEVICE: {
        MQTT_DEVICE_IDS: ["DEVICE_ID"],
        MQTT_NAME: "DEVICE_NAME",
        MQTT_DEVICE_DESCRIPTION: "DEVICE_DESCRIPTION",
        MQTT_SOFTWARE_VERSION: VERSION,
        MQTT_MANUFACTURER: CUBIEMEDIA
    }
}

PAYLOAD_SENSOR = {
    MQTT_NAME: "SERVICE_NAME",
    MQTT_STATE_TOPIC: "STATE_TOPIC",
    MQTT_AVAILABILITY_TOPIC: "AVAILABILITY_TOPIC",
    MQTT_PAYLOAD_ON: "1",
    MQTT_PAYLOAD_OFF: "0",
    MQTT_PAYLOAD_AVAILABLE: "true",
    MQTT_PAYLOAD_NOT_AVAILABLE: "false",
    MQTT_UNIQUE_ID: "UNIQUE_ID",
    MQTT_QOS: "0",
    MQTT_DEVICE: {
        MQTT_DEVICE_IDS: ["DEVICE_ID"],
        MQTT_NAME: "DEVICE_NAME",
        MQTT_DEVICE_DESCRIPTION: "DEVICE_DESCRIPTION",
        MQTT_SOFTWARE_VERSION: VERSION,
        MQTT_MANUFACTURER: CUBIEMEDIA
    }
}
PAYLOAD_SPECIAL_SENSOR = {
    MQTT_NAME: "SERVICE_NAME",
    MQTT_STATE_TOPIC: "STATE_TOPIC",
    MQTT_AVAILABILITY_TOPIC: "AVAILABILITY_TOPIC",
    MQTT_UNIT_OF_MEASUREMENT: "UNIT_OF_MEASUREMENT",
    MQTT_STATE_CLASS: "STATE_CLASS",
    MQTT_DEVICE_CLASS: "DEVICE_CLASS",
    MQTT_SUGGESTED_DISPLAY_PRECISION: 2,
    MQTT_PAYLOAD_AVAILABLE: "true",
    MQTT_PAYLOAD_NOT_AVAILABLE: "false",
    MQTT_UNIQUE_ID: "UNIQUE_ID",
    MQTT_QOS: "0",
    MQTT_DEVICE: {
        MQTT_DEVICE_IDS: ["DEVICE_ID"],
        MQTT_NAME: "DEVICE_NAME",
        MQTT_DEVICE_DESCRIPTION: "DEVICE_DESCRIPTION",
        MQTT_SOFTWARE_VERSION: VERSION,
        MQTT_MANUFACTURER: CUBIEMEDIA
    }
}
