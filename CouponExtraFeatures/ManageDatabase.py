import sqlite3


class DatabaseDetails:
    def __init__(self, db_name='coupons_detail.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def create_table(self):
        self.connect()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupons_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT,
                company_image TEXT,
                about TEXT
            )
        ''')
        self.conn.commit()
        self.close()

    def insert_details(self, company_name, company_image, about):
        self.connect()
        try:
            # Insert a new row into the coupons_details table
            self.cursor.execute('''
                INSERT INTO coupons_details (company_name, company_image, about)
                VALUES (?, ?, ?)
            ''', (company_name, company_image, about))
            self.conn.commit()
            print(f"Details inserted: {company_name}")
        except sqlite3.Error as e:
            print(f"Error inserting details: {e}")
        self.close()

    def get_all_columns(self):
        self.connect()
        # Create a cursor object
        cursor = self.conn.cursor()

        # Execute the query to retrieve all columns from the specified table
        cursor.execute("SELECT * FROM coupons_details")

        # Optionally, get column names
        column_names = [description[0] for description in cursor.description]

        # Close the connection
        self.conn.close()

        return column_names

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None


# # Usage Example
# if __name__ == "__main__":
#     db = DatabaseDetails()
#     db.create_table()
#     db.insert_details("https://example.com/image.png", "This is a description about the company.")