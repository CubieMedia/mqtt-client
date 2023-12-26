# wording #
CUBIE_CORE = "core"
CUBIE_GPIO = "gpio"
CUBIE_ENOCEAN = "enocean"
CUBIE_RELAY = "relay"
CUBIE_SONAR = "sonar"
CUBIE_VICTRON = "victron"
CUBIE_RESET = "reset"
CUBIE_ANNOUNCE = "announce"
CUBIEMEDIA = "cubiemedia/"
STATE_UNKNOWN = 'unknown'

# devices #
ENOCEAN_PORT = "/dev/ttyAMA0"
SONAR_PORT = "/dev/ttyS0"

# MQTT #
QOS = 2
DEFAULT_MQTT_SERVER = "homeassistant"
DEFAULT_MQTT_USERNAME = "mqtt"
DEFAULT_MQTT_PASSWORD = "autoInstall"
DEFAULT_LEARN_MODE = True
DEFAULT_TOPIC_COMMAND = CUBIEMEDIA + "command"
DEFAULT_TOPIC_ANNOUNCE = CUBIEMEDIA + CUBIE_ANNOUNCE

# Relayboard #
RELAY_USERNAME = 'admin'
RELAY_PASSWORD = 'password'

# Timeouts #
TIMEOUT_UPDATE = 10
TIMEOUT_UPDATE_SEND = 30

# Values
DEFAULT_OFFSET = 5

# Colors for Logging #
COLOR_YELLOW = "\x1b[33;20m"
COLOR_RED = "\x1b[31;20m"
COLOR_GREY = "\x1b[38;20m"
COLOR_DEFAULT = "\x1b[0m"
