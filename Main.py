import time
from time import sleep
from Controller import Cep2Controller
from Model import Cep2Model, Cep2ZigbeeDevice
from Cep2Zigbee2mqttClient import start_mqtt_loop
from db import fetch_medication

if __name__ == "__main__":
    # Create a data model and add a list of known Zigbee devices.
    devices_model = Cep2Model()
    devices_model.add([Cep2ZigbeeDevice("0x54ef4410009495b7", "pir"),
                       Cep2ZigbeeDevice("0x00158d000a983a3f", "vibration"),
                       Cep2ZigbeeDevice("0xbc33acfffe8b8d78", "led"),
                       Cep2ZigbeeDevice("0x680ae2fffe725853", "power plug")])

    # Create a controller and give it the data model that was instantiated.
    controller = Cep2Controller(devices_model)
    controller.start()

    # Pass the same devices_model to start_mqtt_loop
    start_mqtt_loop(devices_model)

    # devices_model = Cep2Model()
    # start_mqtt_loop(devices_model)
    # start_mqtt_loop()

    print("Waiting for events...")

    while True:
        sleep(1)

    controller.stop()
