from .network import get_ip_address
from .python import install_package, exit_gracefully

# wording #
CUBIE_IO = "gpio"
CUBIE_ENOCEAN = "enocean"
CUBIE_RELAY = "relay"
CUBIE_RESET = "reset"
CUBIE_ANNOUNCE = "announce"
CUBIEMEDIA = "cubiemedia/"
STATE_UNKNOWN = 'unknown'

# devices #
ENOCEAN_PORT = "/dev/ttyAMA0"

# MQTT #
QOS = 2
DEFAULT_MQTT_SERVER = "homeassistant"
DEFAULT_MQTT_USERNAME = "mqtt"
DEFAULT_MQTT_PASSWORD = "autoInstall"
DEFAULT_LEARN_MODE = True
DEFAULT_TOPIC_COMMAND = CUBIEMEDIA + "command"
DEFAULT_TOPIC_ANNOUNCE = CUBIEMEDIA + CUBIE_ANNOUNCE

# Relayboard #
RELAY_BOARD = "RELAYBOARD"
RELAY_USERNAME = 'admin'
RELAY_PASSWORD = 'password'

# Timeouts #
TIMEOUT_UPDATE = 10
TIMEOUT_UPDATE_SEND = 30

# Config Files #
CONFIG_FILE_NAME_ENOCEAN = "./config_enocean.json"
CONFIG_FILE_NAME_RELAY = "./config_relay.json"
CONFIG_FILE_NAME_GPIO = "./config_gpio.json"
