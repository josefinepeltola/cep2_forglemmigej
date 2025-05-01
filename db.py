import mysql.connector
from mysql.connector import Error
import Controller
from datetime import timedelta
import requests
import json

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_db_connection():
    try:
        connection = mysql.connector.connect(
            host='172.20.10.2',         # Replace with your computer's IP address
            user='group3',              # Your MySQL username
            password='group3',          # Your MySQL password
            database='smart_home'       # Your database name
        )
        if connection.is_connected():
            # print("Successfully connected to the database")       # Debugging, shows if connected to DB
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None


# New func
def insert_event(medication, intake_time, time_window, current_time):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            insert_query = """
            INSERT INTO medication_log (medication, set_intake_time, intake_window, taken_at)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (medication, intake_time, time_window, current_time)) 
            connection.commit()
            print("\nMedication intake was logged")
        except Error as e:
            print(f"Error: {e}")
        finally:
            cursor.close()
            connection.close()

# # Original func, logs all events
# def insert_motion_event(signal, device):
#     connection = create_db_connection()
#     if connection:
#         try:
#             cursor = connection.cursor()
#             if device: 
#                 if device.type_ == "pir":     
#                     insert_query = """
#                     INSERT INTO events (occupancy)
#                     VALUES (%s)
#                     """
#                 if device.type_ == "vibration":     
#                     insert_query = """
#                     INSERT INTO events (strength)
#                     VALUES (%s)
#                     """
#             cursor.execute(insert_query, (signal,)) 
#             connection.commit()
#             print("Motion event inserted successfully")
#         except Error as e:
#             print(f"Error: {e}")
#         finally:
#             cursor.close()
#             connection.close()


def format_timedelta(td):
    """Convert a datetime.timedelta object to HH:MM:SS format."""
    if isinstance(td, timedelta):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return td  # Return as-is if not a timedelta


def fetch_and_print_tables():
    connection = create_db_connection()

    if connection:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        print("Tables in the database:")
        for table in tables:
            print(" -", table[0])
        connection.close()
    else:
        print("Could not connect to MySQL server.")




# def fetch_medication():
#     connection = create_db_connection()

#     if connection:
#         cursor = connection.cursor(dictionary=True)
#         cursor.execute(
#             "SELECT medikament_navn, time_interval, dosis, enhed, tidspunkter_tages, prioritet " \
#             "FROM medikament_liste " \
#             "ORDER BY tidspunkter_tages ASC")
#         medicine = cursor.fetchall()
#         for r in medicine:
#             r['intake_time'] = str(r['intake_time'])  # already string, but keep for clarity
#             r['time_window'] = format_timedelta(timedelta(minutes=r['time_interval']))
#             # r['intake_time'] = format_timedelta(r['intake_time'])   # Format time 
#             # r['time_window'] = format_timedelta(r['time_window'])   # Format time 

#             # print("Current medications:")
#             # print(r)    # print all data in tables for debugging                              
#         connection.close()      # Safeley close connection to DB
#         return medicine
#     else:
#         print("Could not connect to MySQL server.")
#         return None



# def fetch_medication():
#     try:
#             response = requests.get(
#                 "https://172.20.10.2:8000/api/getUserMedikamentListe/1",
#                 verify=False  # ← disables certificate verification
#             )

#             if response.status_code == 200:
#                 raw = response.json()
#                 return [
#                     {
#                         'medikament_navn': med['name'],
#                         'tidspunkter_tages': med['timesToTake'],
#                         'time_interval': f"{int(med['timeInterval'])//60:02}:{int(med['timeInterval'])%60:02}:00",
#                         'dosis': med['dose'],
#                         'enhed': med['unit'],
#                         'prioritet': med['priority'],
#                     }
#                     for med in raw['list']
#                 ]
#             else:
#                 print(f"API error: {response.status_code}")
#                 return []

#     except Exception as e:
#         print(f"Failed to fetch data: {e}")
#         return []
def fetch_medication():
    try:
        response = requests.get(
            "https://172.20.10.2:8000/api/getUserMedikamentListe/1",
            verify=False
        )

        if response.status_code != 200:
            print(f"API error: {response.status_code}")
            return []

        raw = response.json()
        flat_list = []

        for med in raw['list']:
            times = med['timesToTake']
            if isinstance(times, str):
                times = [times]  # wrap single string in a list
            for time in times:
                flat_list.append({
                    'medikament_navn': med['name'],
                    'tidspunkter_tages': med['timesToTake'],
                    'time_interval': f"{int(med['timeInterval'])//60:02}:{int(med['timeInterval'])%60:02}:00",
                    'dosis': med['dose'],
                    'enhed': med['unit'],
                    'prioritet': med['priority'],
                })

        return flat_list
    

    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return []



# if __name__ == "__main__":
#     # create_db_connection()
#     # fetch_and_print_tables()
#     fetch_medication()
    