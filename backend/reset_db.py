import mysql.connector
from mysql.connector import Error

def reset_database():
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Drop database if exists
            cursor.execute("DROP DATABASE IF EXISTS conmetal_ot")
            
            # Create new database
            cursor.execute("CREATE DATABASE conmetal_ot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            print("Database reset successfully!")
            
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    reset_database()