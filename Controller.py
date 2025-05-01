from Model import Cep2Model
from Cep2WebClient import Cep2WebClient, Cep2WebDeviceEvent
from Cep2Zigbee2mqttClient import (Cep2Zigbee2mqttClient,
                                   Cep2Zigbee2mqttMessage, Cep2Zigbee2mqttMessageType, start_mqtt_loop)
from db import fetch_medication, insert_event
import time
import json
from datetime import datetime, timedelta

class Cep2Controller:
    HTTP_HOST = "https://172.20.10.2:8000/api/getUserMedikamentListe/1"  # 8080 is same adress as zigbee gui. Got errors on 8000 and 8090
    # HTTP_HOST = "https://127.0.0.1:8000"  # Updated to use HTTPS and port 8000
    MQTT_BROKER_HOST = "localhost"
    MQTT_BROKER_PORT = 1883

    """ The controller is responsible for managing events received from zigbee2mqtt and handle them.
    By handle them it can be process, store and communicate with other parts of the system. In this
    case, the class listens for zigbee2mqtt events, processes them (turn on another Zigbee device)
    and send an event to a remote HTTP server.
    """

    def __init__(self, devices_model: Cep2Model) -> None:  
        """ Class initializer. The actuator and monitor devices are loaded (filtered) only when the
        class is instantiated. If the database changes, this is not reflected.

        Args:
            devices_model (Cep2Model): the model that represents the data of this application
        """
        self.__devices_model = devices_model
        self.__z2m_client = Cep2Zigbee2mqttClient(host=self.MQTT_BROKER_HOST,
                                                  port=self.MQTT_BROKER_PORT,
                                                  on_message_clbk=self.__zigbee2mqtt_event_received)
        self.__vibration_detected = False 
        self.__current_medication_index = 0             # Track the current medication being processed

        self.__medicine_data = fetch_medication()             # Fetch data once during initialization
        if self.__medicine_data:
            printed = set()
            print("Current medications:")
            for r in self.__medicine_data:
                if r['medikament_navn'] not in printed:
                    print(r)
                    printed.add(r['medikament_navn'])
            print("\n")


    def start(self) -> None:
        """ Start listening for zigbee2mqtt events.
        """
        self.__z2m_client.connect()
        print(f"Zigbee2Mqtt is {self.__z2m_client.check_health()}")

        for b in self.__devices_model.actuators_list:                                   # Turn powerplug and LED on and glow white
            self.__z2m_client.change_state(b.id_, "ON")                         
            self.__z2m_client.change_color(b.id_,  {"color": {"x": 0.33, "y": 0.33}})   



    def stop(self) -> None:
        """ Stop listening for zigbee2mqtt events.
        """
        self.__z2m_client.disconnect()


    def __zigbee2mqtt_event_received(self, message: Cep2Zigbee2mqttMessage) -> None:
        """ Process an event received from zigbee2mqtt. This function given as callback to
        Cep2Zigbee2mqttClient, which is then called when a message from zigbee2mqtt is received.

        Args:
            message (Cep2Zigbee2mqttMessage): an object with the message received from zigbee2mqtt
        """
        # If message is None (it wasn't parsed), then don't do anything.
        if not message:
            return

        # print(
        #     f"zigbee2mqtt event received on topic {message.topic}: {message.data}")       # Debugging, shows all events recieved on different topics 

        # If the message is not a device event, then don't do anything.
        if message.type_ != Cep2Zigbee2mqttMessageType.DEVICE_EVENT:
            return

        # Parse the topic to retreive the device ID. If the topic only has one level, don't do
        # anything.
        tokens = message.topic.split("/")
        if len(tokens) <= 1:
            return

        # Retrieve the device ID from the topic.
        device_id = tokens[1]
        # If the device ID is known, then process the device event and send a message to the remote
        # web server.
        device = self.__devices_model.find(device_id)



        
        """
        Main logic for light control

        """
        # # Real current time
        # current_time = datetime.now()                           
        # formatted_time = current_time.strftime("%H:%M:%S")

        # Set your own time for testing 
        custom_time_str = "13:08:00"  # Replace with your desired time
        custom_time = datetime.strptime(custom_time_str, "%H:%M:%S")
        formatted_time = custom_time.strftime("%H:%M:%S") 


        if device:
            try:
                if device.type_ == "pir":                   # Take messages based on device used
                    signal = message.event["occupancy"]
                elif device.type_ == "vibration":
                    signal = message.event["strength"]
                else:
                    signal = None                          
            
            except KeyError:                                # Exeception error
                signal = None

            
            # Known device activity detected and current index is within medicine DB length 
            if signal is not None and self.__current_medication_index < len(self.__medicine_data):          
                current_medication = self.__medicine_data[self.__current_medication_index]                  # Initialize index for current medicine    
                print("\n**** Current time:", formatted_time, " ****", 
                      "\nNext medication:\t", current_medication['medikament_navn'], 
                      "\nIntake time:\t\t", current_medication['tidspunkter_tages'],
                      "\nTime window:\t\t", current_medication['time_interval'],
                      )
                
                # Convert intake_time and time_window back to datetime and timedelta
                # intake_time = datetime.strptime(current_medication['tidspunkter_tages'], "%H:%M:%S")
                # intake_time = current_medication['tidspunkter_tages']
                # time_window_parts = current_medication['time_interval'].split(":")
                # time_window = timedelta(hours=int(time_window_parts[0]),
                #                         minutes=int(time_window_parts[1]),
                #                         seconds=int(time_window_parts[2]))
                # time_sum = (intake_time + time_window).time()
                
                
                # Get the time as a string
                intake_time_str = current_medication['tidspunkter_tages']
                # Ensure it's a string (optional safety)
                if isinstance(intake_time_str, list):
                    intake_time_str = intake_time_str[0]
                intake_time = datetime.strptime(intake_time_str, "%H:%M")

                # Parse the time interval string (e.g., "01:00:00")
                time_window_parts = current_medication['time_interval'].split(":")
                time_window = timedelta(
                    hours=int(time_window_parts[0]),
                    minutes=int(time_window_parts[1]),
                    seconds=int(time_window_parts[2])
                )


                # Calculate intake time + window
                time_sum = (intake_time + time_window).time()
                
                # Motion detected with pir sensor
                # Motion must be true and nonzero 
                if device.type_ == "pir" and signal != "false" and signal != 0: 
                    self.__vibration_detected = False                                                       # Set vibration to false 
                    if formatted_time >= intake_time_str:
                    # if formatted_time >= current_medication['tidspunkter_tages'] :                                # If current time surpasses intake time glow orange 
                        print("\nTime to take", current_medication['medikament_navn'], "!")
                        for b in self.__devices_model.actuators_list:                                   
                            self.__z2m_client.change_color(b.id_, {"color": {"x": 0.55, "y": 0.45}})           
                        if formatted_time >= time_sum.strftime("%H:%M"):                                 # If current time surpasses intake time + time window glow red
                            print("\n**** URGENT ****",
                                  "\nTime window of ", current_medication['medikament_navn'], "has passed",
                                  "\n**** MUST TAKE ACTION NOW ****")
                            for b in self.__devices_model.actuators_list:                                   
                                self.__z2m_client.change_color(b.id_, {"color": {"x": 0.72, "y": 0.25}})    

                # Vibration detected 
                elif device.type_ == "vibration" and self.__vibration_detected == False:
                    self.__vibration_detected = True                                                        # Set vibration detected to true
                    if formatted_time >= intake_time_str:
                    # if (current_medication['tidspunkter_tages'] <= formatted_time):                               # If vibration is detected after intake time glow green

                        print("\n", current_medication['medikament_navn'], "has been taken")
                        
                        # insert_event(current_medication['medication'],                                      # Insert into DB
                        #              current_medication['intake_time'], 
                        #              current_medication['time_window'], 
                        #              formatted_time)  

                                        # Prepare the event data to send to the web client
                        
                        event_data = {
                            "name": current_medication['medikament_navn'],
                            "timesToTake": current_medication['tidspunkter_tages'],
                            "timeInterval": current_medication['time_interval'],
                            "actual_time": formatted_time
                        }

                        # Use the Cep2WebClient to send the event
                        client = Cep2WebClient(self.HTTP_HOST)
                        try:
                            client.send_event(json.dumps(event_data))  # Serialize the event data to JSON
                            print("Event successfully sent to the web client API.")
                        except ConnectionError as ex:
                            print(f"Failed to send event to the web client API: {ex}")

                        


                        for b in self.__devices_model.actuators_list:
                            self.__z2m_client.change_color(b.id_, {"color": {"x": 0.15, "y": 0.75}})
                        time.sleep(30)                                                                       # Decide how long to glow green after intake
                        self.__current_medication_index += 1                                                # Increment index
                        for b in self.__devices_model.actuators_list:                                       # Glow white after set time
                            self.__z2m_client.change_color(b.id_, {"color": {"x": 0.33, "y": 0.33}})
                    

                # # Register event in the remote web server.
                # web_event = Cep2WebDeviceEvent(device_id=device.id_,
                #                                device_type=device.type_,
                #                                measurement=signal) # measurement=occupancy


                # client = Cep2WebClient(self.HTTP_HOST)
                # try:
                #     client.send_event(web_event.to_json())
                # except ConnectionError as ex:
                #     print(f"{ex}")
                    






            
            
                




            ##### Version 1.2: integrated with correct color codes ### 
            # if signal is not None:                         # Known device activity detected
            #     if device.type_ == "pir": 
            #         if not self.__vibration_detected:                   # If no vibrations detected at any point, stay orange
            #             for b in self.__devices_model.actuators_list:                           
            #                         self.__z2m_client.change_color(b.id_, {"color": {"x": 0.55, "y": 0.45}})   # Set color to orange 
                
            #     elif device.type_ == "vibration": 
            #         self.__vibration_detected = True                        # Set vibration detected to true
                
            #         for b in self.__devices_model.actuators_list:
            #             self.__z2m_client.change_color(b.id_, {"color": {"x": 0.35, "y": 0.518}})



            #####  Version 1: pir and vibration works, but no DB integration #### 
            # if signal is not None:                         # Known device activity detected
            #     if device.type_ == "pir":                   
            #         time.sleep(1)
            #         new_state = "ON" if signal else "OFF"                   # If motion detected, turn on, else off
            #         make_orange = {"r":255,"g":165, "b":0}                  # Turn LED orange
                    
            #         for b in self.__devices_model.actuators_list:           # Change state
            #             self.__z2m_client.change_state(b.id_, new_state)

            #             if not self.__vibration_detected:                   # If no vibrations detected at any point, stay orange
            #                 self.__z2m_client.change_color(b.id_, make_orange)
                
            #     elif device.type_ == "vibration": 
            #         self.__vibration_detected = True                        # Set vibration detected to true
            #         make_green = {"r":0,"g":255, "b":0}                     # Turn LED green 
                    
            #         for b in self.__devices_model.actuators_list:
            #             self.__z2m_client.change_color(b.id_, make_green)
                                

                