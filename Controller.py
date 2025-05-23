from Model import Cep2Model
from WebClient import WebClient
from Cep2Zigbee2mqttClient import (
    Cep2Zigbee2mqttClient,
    Cep2Zigbee2mqttMessage,
    Cep2Zigbee2mqttMessageType,
)
import time
import json
import base64
from datetime import datetime, timedelta

""" 
The controller is responsible for managing events received from zigbee2mqtt and handle them.
By handle them it can be process, store and communicate with other parts of the system. In this
case, the class listens for zigbee2mqtt events, processes them (turn on another Zigbee device)
and send an event to a remote HTTP server.
"""
class Cep2Controller:
    base_url = "https://forglemmigej.duckdns.org/api"
    MQTT_BROKER_HOST = "localhost"
    MQTT_BROKER_PORT = 1883

    # Class initializer 
    def __init__(self, devices_model: Cep2Model) -> None:
        self.__user_id = None 
        self.__devices_model = devices_model
        self.__vibration_detected = False
        self.__current_medication_index = 0   
        self.__last_pir_room = None
        self.__taken_status = 0

        self.__z2m_client = Cep2Zigbee2mqttClient(
            host=self.MQTT_BROKER_HOST,
            port=self.MQTT_BROKER_PORT,
            on_message_clbk=self.__zigbee2mqtt_event_received
        )

        self.__web_client = WebClient()
        self.__user_id = self.__web_client.fetch_userid()  
        if not self.__user_id:
            print("Failed to get user ID. Aborting startup.")
            return

        self.__medicine_data = self.__web_client.fetch_medication()
        if self.__medicine_data:
            for r in self.__medicine_data:
                print(r)
            print("\n")



    # Start listening for zigbee2mqtt events.
    def start(self) -> None:
        self.__z2m_client.connect()
        print(f"Zigbee2Mqtt is {self.__z2m_client.check_health()}")
        for b in self.__devices_model.actuators_list:
            self.__z2m_client.change_state(b.id_, "ON")
            self.__z2m_client.change_color(b.id_, {"color": {"x": 0.33, "y": 0.33}})


    # Stop listening for zigbee2mqtt events.
    def stop(self) -> None:
        self.__z2m_client.disconnect()


    """
    Main logic for program
    Processes zigbee events
    """
    def __zigbee2mqtt_event_received(self, message: Cep2Zigbee2mqttMessage) -> None:
        if not message or message.type_ != Cep2Zigbee2mqttMessageType.DEVICE_EVENT:     # If message is not valid, return
            return

        tokens = message.topic.split("/")                                               # Retrieve device ID
        if len(tokens) <= 1:
            return
        device_id = tokens[1]
        device = self.__devices_model.find(device_id)

        # Real current time
        current_time = datetime.now()                           
        formatted_time = current_time.strftime("%H:%M:%S")

        # # Set your own time for testing 
        # custom_time_str = "08:15:00"  # Replace with your desired time
        # custom_time = datetime.strptime(custom_time_str, "%H:%M:%S")
        # formatted_time = custom_time.strftime("%H:%M:%S") 


        # Known device detected 
        if device:
            self.__web_client.device_status(device, message.event)
            
            # Take messages based on device used
            try:                                                                                    
                if device.type_ == "pir":
                    signal = message.event.get("occupancy")
                elif device.type_ == "vibration":
                    signal = message.event.get("strength")
                else:
                    signal = None
            except KeyError:
                signal = None

            if signal is not None and self.__current_medication_index < len(self.__medicine_data):          # Known device activity detected and current index is within medicine DB length
                current_medication = self.__medicine_data[self.__current_medication_index]                  # Set current medicine index
                print("\n**** Current time:", formatted_time, " ****", 
                      "\nNext medication:\t", current_medication['medikament_navn'], 
                      "\nIntake time:\t\t", current_medication['tidspunkter_tages'],
                      "\nTime window:\t\t", current_medication['time_interval'],
                      )

                intake_time_str = current_medication['tidspunkter_tages']                                   # Convert time to strings
                if isinstance(intake_time_str, list):
                    intake_time_str = intake_time_str[0]
                intake_time = datetime.strptime(intake_time_str, "%H:%M")

                time_window_parts = current_medication['time_interval'].split(":")                          # Format time
                time_window = timedelta(
                    hours=int(time_window_parts[0]),
                    minutes=int(time_window_parts[1]),
                    seconds=int(time_window_parts[2])
                )

                time_sum = (intake_time + time_window).time()                                               # Find max time for medication intake 


                """
                Sensor logic
                """
                # Motion detected with pir sensor
                # Motion must be true and nonzero 
                if device.type_ == "pir" and signal != "false" and signal != 0:     
                    self.__vibration_detected = False                                                       # Set vibration to false 
                    room = device.name_.removeprefix("pir_")                                                # Find room 
                    self.__last_pir_room = room
                    
                    # If current time surpasses intake time glow orange 
                    if formatted_time >= intake_time_str:                                            
                        print("\nTime to take", current_medication['medikament_navn'], "!")
                        for b in self.__devices_model.actuators_list:
                            self.__z2m_client.change_color(b.id_, {"color": {"x": 0.55, "y": 0.45}})        # Orange
                        
                        # If current time surpasses intake time + time window glow red
                        if formatted_time >= time_sum.strftime("%H:%M"):
                            print("\n**** URGENT ****",
                                  "\nTime window of ", current_medication['medikament_navn'], "has passed",
                                  "\n**** MUST TAKE ACTION NOW ****")
                            for b in self.__devices_model.actuators_list:
                                self.__z2m_client.change_color(b.id_, {"color": {"x": 0.72, "y": 0.25}})    # Red
                            
                            # Log medication has not been taken in DB
                            self.__taken_status = 0
                            payload = {
                                "medicationLog": {
                                    "name": current_medication['medikament_navn'],
                                    "tagetTid": formatted_time,
                                    "status": self.__taken_status,
                                    "lokale": room 
                                }
                            }
                            encoded_data = base64.b64encode(json.dumps(payload).encode()).decode()
                            # Send to API
                            try:
                                url = f"{self.__web_client.base_url}/MedicationRegistrationLog/{self.__user_id}"
                                self.__web_client.send_event(url, encoded_data, is_base64=True)
                                print("Medication not taken was logged")
                            except ConnectionError as ex:
                                print(f"Failed to send event to the web client API: {ex}")
                        

                # Vibration detected with sensor
                # No vibration has been detected
                elif device.type_ == "vibration" and not self.__vibration_detected:
                    self.__vibration_detected = True                                                        # Set vibration detected to true
                    room = self.__last_pir_room 
                    self.__taken_status = 1                                                            # Reinitialize room
                    
                    # Detect if taken
                    if formatted_time >= intake_time_str:
                        print("\n", current_medication['medikament_navn'], "has been taken")

                        # Send for json
                        payload = {
                            "medicationLog": {
                                "name": current_medication['medikament_navn'],
                                "tagetTid": formatted_time,
                                "status": self.__taken_status,
                                "lokale": room 
                            }
                        }
                        encoded_data = base64.b64encode(json.dumps(payload).encode()).decode()

                        # Send to API
                        try:
                            url = f"{self.__web_client.base_url}/MedicationRegistrationLog/{self.__user_id}"
                            self.__web_client.send_event(url, encoded_data, is_base64=True)
                            print("Medication intake was successfully logged")
                        except ConnectionError as ex:
                            print(f"Failed to send event to the web client API: {ex}")

                        # Glow green if taken. Wait set time and glow white again
                        for b in self.__devices_model.actuators_list:
                            self.__z2m_client.change_color(b.id_, {"color": {"x": 0.15, "y": 0.75}})        # Green
                        
                        time.sleep(30)                                                                       # Decide how long to glow green after intake
                        self.__current_medication_index += 1                                                # Increment index
                        
                        for b in self.__devices_model.actuators_list:
                            self.__z2m_client.change_color(b.id_, {"color": {"x": 0.33, "y": 0.33}})        # White