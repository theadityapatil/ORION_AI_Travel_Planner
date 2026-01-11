import sqlite3

# Connect to the database file (it will be created if it doesn't exist)
connection = sqlite3.connect('database.db')
cursor = connection.cursor()

# SQL command to create the 'users' table
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        number TEXT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
''')

# UPDATED: SQL command to create the 'trips' table with the new rating column
cursor.execute('''
    CREATE TABLE trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        destination TEXT NOT NULL,
        days INTEGER NOT NULL,
        trip_type TEXT NOT NULL,
        travelers INTEGER NOT NULL,
        budget TEXT NOT NULL,
        estimated_cost TEXT,
        itinerary_json TEXT NOT NULL,
        rating INTEGER,                      -- New column for the rating
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

# Commit the changes and close the connection
connection.commit()
connection.close()

print("Database re-initialized with 'users' and updated 'trips' tables (including rating) successfully.")