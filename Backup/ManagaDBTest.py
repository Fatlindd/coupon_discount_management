import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_name='text_coupons.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def create_table(self):
        self.connect()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                offer TEXT,
                order_ammount TEXT,
                limitations_for_users TEXT,
                limitations_on_brands TEXT,
                button_name TEXT,
                code TEXT,
                url TEXT,
                company_name TEXT,
                last_scrapped TEXT,  -- Add a column for the last_scrapped timestamp
                UNIQUE(title, description)  -- Add a unique constraint on title and description
            )
        ''')
        self.conn.commit()
        self.close()

    def get_all_columns(self):
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM coupons")
        column_names = [description[0] for description in cursor.description]
        self.conn.close()
        return column_names

    def insert_coupon(self, title, description, offer, order_ammount, limitations_for_users, limitations_on_brands,
                      button_name, code, url, company_name):
        self.connect()
        try:
            # Get the current timestamp
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Prepare SQL query with NULL checks
            query = '''
                SELECT * FROM coupons WHERE title = ? AND 
            '''
            if description is None:
                query += 'description IS NULL'
            else:
                query += 'description = ?'

            # Execute the query
            self.cursor.execute(query, (title,) if description is None else (title, description))
            result = self.cursor.fetchone()

            if result is not None:
                # If a row exists, compare other fields to decide if an update is necessary
                existing_coupon = dict(zip([description[0] for description in self.cursor.description], result))
                fields_to_update = {}

                # List of fields to compare and potentially update
                fields_to_check = {
                    'offer': offer,
                    'order_ammount': order_ammount,
                    'limitations_for_users': limitations_for_users,
                    'limitations_on_brands': limitations_on_brands,
                    'button_name': button_name,
                    'code': code,
                    'url': url,
                    'company_name': company_name
                }

                # Check each field for differences
                for field, new_value in fields_to_check.items():
                    if existing_coupon[field] != new_value:
                        fields_to_update[field] = new_value

                # Always update the last_scrapped field
                fields_to_update['last_scrapped'] = current_timestamp

                if fields_to_update:
                    # Update the existing row if any field is different
                    update_query = 'UPDATE coupons SET ' + ', '.join(
                        [f"{k} = ?" for k in fields_to_update.keys()]) + ' WHERE title = ? AND '
                    update_query += 'description IS NULL' if description is None else 'description = ?'
                    self.cursor.execute(update_query, list(fields_to_update.values()) + (
                        [title] if description is None else [title, description]))
                    self.conn.commit()
                    print(f"Coupon updated: {title}")
                else:
                    print(f"No changes detected for the coupon with title '{title}' and description '{description}'.")
            else:
                # Insert a new row if no matching row exists
                self.cursor.execute('''
                    INSERT INTO coupons (
                        title, description, offer, order_ammount, limitations_for_users,
                        limitations_on_brands, button_name, code, url, company_name, last_scrapped
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    title, description, offer, order_ammount, limitations_for_users, limitations_on_brands, button_name,
                    code, url, company_name, current_timestamp))
                self.conn.commit()
                print(f"Coupon inserted: {title}")
                print("--------------------------------------------------------------------\n\n")
        except sqlite3.Error as e:
            print(f"Error inserting or updating coupon: {e}")

        self.close()

    def update_last_scrapped_column(self, companyName):
        print("***************************************************************")
        print("***************************************************************")
        print("We are inside the update_last_scrapped_column method")
        print(f"Company name: {companyName}")
        print("***************************************************************")
        print("***************************************************************")

        current_datetime = datetime.now()
        current_date_only = current_datetime.date()

        try:
            self.connect()

            if not self.conn or not self.cursor:
                raise Exception("Database connection failed.")

            # Fetch the rows from the database for the given company name
            self.cursor.execute("SELECT * FROM coupons WHERE company_name = ?", (companyName,))
            rows = self.cursor.fetchall()

            if not rows:
                print("No rows fetched from the database.")
                return

            print(f"Current Date and Time: {current_datetime}")
            print(f"Fetched rows for company '{companyName}':")
            rows_to_delete = []

            for row in rows:
                row_dict = dict(zip([description[0] for description in self.cursor.description], row))
                last_scrapped = row_dict.get('last_scrapped', '')
                last_scrapped_datetime = datetime.strptime(last_scrapped,
                                                           '%Y-%m-%d %H:%M:%S') if last_scrapped else None
                last_scrapped_date_only = last_scrapped_datetime.date() if last_scrapped_datetime else None

                if last_scrapped_date_only != current_date_only:
                    rows_to_delete.append(row_dict['id'])  # Collect IDs of rows to be deleted

            if rows_to_delete:
                # Delete the rows with IDs collected in rows_to_delete
                self.cursor.executemany("DELETE FROM coupons WHERE id = ?", [(row_id,) for row_id in rows_to_delete])
                self.conn.commit()
                print(f"Deleted rows with IDs: {rows_to_delete}")
            else:
                print("No rows to delete.")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.close()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

