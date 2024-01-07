# mqtt-client

Gateway connecting different Protocols and Devices via MQTT

This works perfectly together with <b>Home Assistant</b> and is an important part of the [CubieMedia - System](https://www.cubiemedia.de)

It supports following modules:

* Relayboards
  * [ETH 008](https://www.robot-electronics.co.uk/files/eth008.pdf)
  * only one Gateway is needed per Installation
* Enocean (with the Enocean Pi Module)
  * [EnOcean Module for Raspberry Pi](https://www.rasppishop.de/ENOCEAN-PI-868-Das-868MHz-Transceiver-Modul-fuer-Raspberry-Pi)
  * [Switch Eltako FT-55](https://www.amazon.de/Eltako-FT55-RW-Funktaster/dp/B004OXQ93G/ref=sr_1_1?keywords=enocean+taster&sr=8-1)
  * Enocean supports multiple Gateways for range extension
* GPIO (normal GPIO Pins on Pi)
  * [Simple Relayboards with Optokoppler](https://www.amazon.de/Yizhet-Optokoppler-Channel-Raspberry-Arduino/dp/B07GXBSX58/ref=sr_1_15_sspa?__mk_de_DE=%C3%85M%C3%85%C5%BD%C3%95%C3%91&keywords=relay%2Bboard%2Boptokoppler&sr=8-15-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9tdGY&th=1)
  * Doorbell, door opener inclusion
* Sonar (Distance sensor with sound)
  * connect [Sonar](https://www.amazon.de/Ultraschall-Sensor-JSN-SR04T-Entfernungsmessmodul-Wasserdichtem/dp/B07MKQ7VQF/ref=sr_1_4?__mk_de_DE=%C3%85M%C3%85%C5%BD%C3%95%C3%91&keywords=ultraschallsensor+entfernung&sr=8-4) sensor to gpio's
* Victron Energy MQTT Gateway
  * [Cerbo GX](https://www.victronenergy.com/communication-centres/cerbo-gx)
  * only one Gateway is needed per Installation (currently only one system is supported)

The Code will run on all architectures but Enocean and GPIO only work on arm.


<h1>A Manual for setup on Ubuntu Core will follow</h1>


<br>
Help is appreciated!
Contact me on Discord @Cubiemedia or via Mail
