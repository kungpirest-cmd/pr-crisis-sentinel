import sqlite3

# Connect to the database file (it will be created if it doesn't exist)
connection = sqlite3.connect('history.db')
cursor = connection.cursor()

# Create the table to store analysis history
cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL,
        analysis_date TEXT NOT NULL,
        negative_percent REAL NOT NULL,
        positive_percent REAL NOT NULL,
        neutral_percent REAL NOT NULL
    )
''')

connection.commit()
connection.close()

print("Database 'history.db' and table 'analysis_history' created successfully.")