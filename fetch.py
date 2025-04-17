from db import create_db_connection

def fetch_and_print_events():
    connection = create_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;")
        rows = cursor.fetchall()
        for row in rows:
            print(f"{row['timestamp']}: {'Motion' if row['occupancy'] else 'No Motion'}")
        cursor.close()
        connection.close()

if __name__ == "__main__":
    fetch_and_print_events()
