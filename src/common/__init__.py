# wording #
CUBIE_CORE = "core"
CUBIE_GPIO = "gpio"
CUBIE_ENOCEAN = "enocean"
CUBIE_RELAY = "relay"
CUBIE_SONAR = "sonar"
CUBIE_VICTRON = "victron"
CUBIE_SERIAL = "serial"
CUBIE_MODE_LIST = [CUBIE_CORE, CUBIE_RELAY, CUBIE_VICTRON, CUBIE_SONAR, CUBIE_ENOCEAN, CUBIE_GPIO]

CUBIE_RESET = "reset"
CUBIE_RELOAD = "reload"
CUBIE_TYPE = "type"
CUBIE_DEVICE = "device"
CUBIE_ANNOUNCE = "announce"
CUBIEMEDIA = "cubiemedia"
STATE_UNKNOWN = 'unknown'

# devices #
ENOCEAN_PORT = "/dev/ttyAMA0"
SONAR_PORT = "/dev/ttyS0"

# files
DEFAULT_CONFIGURATION_FILE = "./snap/hooks/install"

# MQTT #
QOS = 2
DEFAULT_MQTT_SERVER = "homeassistant"
DEFAULT_MQTT_USERNAME = "mqtt"
DEFAULT_MQTT_PASSWORD = "autoInstall"
DEFAULT_LEARN_MODE = True
DEFAULT_TOPIC_COMMAND = CUBIEMEDIA + "/command"
DEFAULT_TOPIC_ANNOUNCE = CUBIEMEDIA + "/" + CUBIE_ANNOUNCE

# Victron
EXPORT_CORRECTION_FACTOR = 'export_correction_factor'
IMPORT_CORRECTION_FACTOR = 'import_correction_factor'

# Relayboard #
RELAY_USERNAME = 'admin'
RELAY_PASSWORD = 'password'

# GPIO #
GPIO_PIN_TYPE_IN = "in"
GPIO_PIN_TYPE_OUT = "out"

# Timeouts #
TIMEOUT_UPDATE = 180
TIMEOUT_UPDATE_SEND = 30

# Values
DEFAULT_OFFSET = 5

# Colors for Logging #
COLOR_YELLOW = "\x1b[33;20m"
COLOR_RED = "\x1b[31;20m"
COLOR_GREY = "\x1b[38;20m"
COLOR_DEFAULT = "\x1b[0m"
