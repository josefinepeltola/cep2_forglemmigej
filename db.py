import mysql.connector
from mysql.connector import Error
import Controller

def create_db_connection():
    try:
        connection = mysql.connector.connect(
            host='172.20.10.2',         # Replace with your computer's IP address
            user='group3',              # Your MySQL username
            password='group3',          # Your MySQL password
            database='smart_home'       # Your database name
        )
        if connection.is_connected():
            print("Successfully connected to the database")
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None


# def insert_motion_event(occupancy):
#     connection = create_db_connection()
#     if connection:
#         try:
#             cursor = connection.cursor()
#             insert_query = """
#             INSERT INTO motion_events (occupancy)
#             VALUES (%s)
#             """
#             cursor.execute(insert_query, (occupancy,))
#             connection.commit()
#             print("Motion event inserted successfully")
#         except Error as e:
#             print(f"Error: {e}")
#         finally:
#             cursor.close()
#             connection.close()


# def insert_motion_event(occupancy):
#     connection = create_db_connection()
#     if connection:
#         try:
#             cursor = connection.cursor()
#             insert_query = """
#             INSERT INTO events (occupancy)
#             VALUES (%s)
#             """
#             cursor.execute(insert_query, (occupancy,)) 
#             connection.commit()
#             print("Motion event inserted successfully")
#         except Error as e:
#             print(f"Error: {e}")
#         finally:
#             cursor.close()
#             connection.close()


def insert_motion_event(signal, device):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            if device: 
                if device.type_ == "pir":     
                    insert_query = """
                    INSERT INTO events (occupancy)
                    VALUES (%s)
                    """
                if device.type_ == "vibration":     
                    insert_query = """
                    INSERT INTO events (strength)
                    VALUES (%s)
                    """
            cursor.execute(insert_query, (signal,)) 
            connection.commit()
            print("Motion event inserted successfully")
        except Error as e:
            print(f"Error: {e}")
        finally:
            cursor.close()
            connection.close()

    