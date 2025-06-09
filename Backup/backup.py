import sys
import os
import time
import logging
import requests

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv
from ManagaDBTest import Database

# Load environment variables from .env file
load_dotenv()


class ScrappingCoupon:
    file_path = 'links_test.txt'
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    CHAT_ID = os.getenv('CHAT_ID')
    MESSAGE = os.getenv('MESSAGE')

    def __init__(self):
        """
            Initializes the scraper with Chrome options, sets up the WebDriver,
            initializes an empty dictionary for coupon details, creates an instance
            of the ManageDB class, ensures the database table is created, and sets up
            the default logger.
        """
        self.chrome_options = uc.ChromeOptions()
        self.webdriver = uc.Chrome(options=self.chrome_options)
        self.detail_of_coupon = {}
        self.db = Database()  # Creating an instance of ManageDB
        self.db.create_table()  # Ensure the table is created
        self.setup_default_logger()

    def setup_default_logger(self):
        """
            Configures the default logger to output log messages to standard output
            with INFO level. Sets up the logging format to include timestamp, log level,
            and message.
        """
        # Configure default logger
        self.logger = logging.getLogger('default')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def start_webdriver(self):
        """
            Begins the web scraping process by first checking and scraping all links,
            then iterates through URLs from a file. For each URL, configures the logger,
            starts the WebDriver, maximizes the browser window, and performs scraping.
            Updates the URL status to 'True' after scraping is complete.
        """
        # First check all links and scrape them before starting
        # self.alphabet_section()
        urls = self.get_urls_from_file()
        for url in urls:
            # Configure logger for each URL
            self.setup_logger(url)
            self.logger.info(f"Starting scraping for URL: {url}")

            self.webdriver.get(url)
            self.webdriver.maximize_window()
            self.scrape_all_shop_links()

            # Update the URL status to True after scraping
            self.update_url_status(url, 'True')

    def setup_logger(self, url):
        """
            Sets up a logger for the given URL by extracting a directory and file name
            from the URL. Creates the necessary directory if it doesn't exist, configures
            the logger to output to a file with INFO level, and formats the log messages
            to include timestamp, log level, and message.
        """
        # Extract the last part of the URL to use as a directory and file name
        folder_name = url.split('/')[-1].split(',')[0]
        print(f"Folder name: {folder_name}")
        log_dir = os.path.join('Logs', folder_name)
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f'{folder_name}.log')

        print("File name: ", log_file)

        # Configure logger
        self.logger = logging.getLogger(folder_name)
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def send_telegram_message(self, bot_token, chat_id, message):
        """
            Sends a message to a specified Telegram chat.

            This function sends a message to a given chat_id using the Telegram Bot API.
            If the message fails to send, it attempts to retrieve a new chat_id via the get_updates method
            and retries sending the message.

            Parameters:
            bot_token (str): The token for accessing the Telegram Bot API.
            chat_id (str): The ID of the chat to send the message to.
            message (str): The message to send.

            Returns:
            None
        """
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': message
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print('Message sent successfully!')
        else:
            print(f'Failed to send message: {response.status_code} {response.text}')
            new_chat_id = self.get_updates(bot_token)
            if new_chat_id:
                print(f'New chat ID saved: {new_chat_id}')
                self.send_telegram_message(self, bot_token, chat_id, message)

    def get_updates(self, bot_token):
        """
            Retrieves the latest updates from the Telegram Bot API and extracts the chat_id.

            This function retrieves updates from the Telegram Bot API to find the latest chat_id.
            It saves the new chat_id to a .env file and updates the in-memory chat_id for immediate use.

            Parameters:
            bot_token (str): The token for accessing the Telegram Bot API.

            Returns:
            str: The latest chat_id if available, otherwise None.
        """
        url = f'https://api.telegram.org/bot{bot_token}/getUpdates'
        response = requests.get(url)
        if response.status_code == 200:
            updates = response.json()
            for update in updates['result']:
                chat_id = update['message']['chat']['id']
                print(f"Chat ID: {chat_id}")

                # Save the new chat_id to .env file using set_key
                set_key('.env', 'CHAT_ID', str(chat_id))

                # Update the in-memory CHAT_ID for immediate use
                global CHAT_ID
                CHAT_ID = chat_id

                return chat_id
        else:
            print(f'Failed to get updates: {response.status_code} {response.text}')
        return None

    def alphabet_section(self):
        """
            Navigates to the 'allshop' page on the Cuponation website, waits for the alphabet
            sections to load, and counts the number of sections. Logs and prints the number
            of sections, then calls a method to save all coupon links based on the section count.
            Logs an error if the page takes too long to load.
        """
        self.webdriver.get("https://www.cuponation.com.au/allshop")
        try:
            sections = WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_all_elements_located((
                    By.XPATH,
                    "//div[@data-testid='alphabet-sections']/div")
                )
            )
            number_of_sections = len(sections)
            self.logger.info(f"Number of sections: {number_of_sections}")
            print(f"Number of sections: {number_of_sections}")
            self.save_all_coupon_links(number_of_sections)

        except TimeoutException:
            self.logger.error("Loading took too much time!")
            self.send_telegram_message(self.BOT_TOKEN, self.CHAT_ID, self.MESSAGE)
            return None

    def save_all_coupon_links(self, number_of_sections):
        """
            Saves coupon links and their texts from the specified number of sections to a file.
            Reads existing URLs and their statuses from the file, if it exists.
            Appends new links with their texts and a 'False' status to the file if they are not
            already present. Logs and prints the total number of URLs to scrape.
        """
        # Create a dictionary to store existing URLs and their statuses
        existing_urls = {}

        # Read existing URLs and their statuses from the file if it exists
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as file:
                for line in file:
                    url, text, status = line.strip().split(', ')
                    existing_urls[url] = {'text': text, 'status': status}

        # Find new links and write them to the file with status False if they are not already in the dictionary
        with open(self.file_path, 'a') as file:
            count_hrefs = 0
            for i in range(1, number_of_sections + 1):
                try:
                    all_links = self.webdriver.find_elements(
                        By.XPATH,
                        f"//div[@data-testid='alphabet-sections']/div[{i}]/div/div//a"
                    )
                except:
                    self.send_telegram_message(self.BOT_TOKEN, self.CHAT_ID, self.MESSAGE)
                    continue

                for link in all_links:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    count_hrefs += 1
                    if href not in existing_urls:
                        file.write(f"{href}, {text}, False\n")
                        existing_urls[href] = {'text': text, 'status': 'False'}

        self.logger.info(f"Number of urls to scrape: {count_hrefs}")
        print(f"Number of urls to scrape: {count_hrefs}")

    def check_button_name(self, xpath, index):
        """
           Retrieves the text of a button from a specific element found using the given XPath
           and index, and stores it in the 'detail_of_coupon' dictionary under the key 'Button Name'.
           Returns the button text if found; otherwise, returns None.
        """
        try:
            button = self.webdriver.find_element(
                By.XPATH, f"{xpath}[{index}]//div[@role='button']"
            )
            self.detail_of_coupon['Button Name'] = button.text

            return button.text.strip()
        except:
            pass

    def get_code_or_url_from_voucher(self, button_text):
        """
            Retrieves a voucher code and URL based on the provided button text. If the button text is 'SEE CODE',
            waits for the voucher code to appear, switches to the appropriate window, and stores the URL and code
            in the 'detail_of_coupon' dictionary. If the button text is not 'SEE CODE', attempts to find the voucher
            code and URL similarly. Logs an error if the code or buttons are not found.
            """
        try:
            if button_text == 'SEE CODE':
                # Wait for up to 5 seconds for the codes to be present
                codes = WebDriverWait(self.webdriver, 3).until(EC.presence_of_all_elements_located(
                    (By.XPATH, "//span[@data-testid='voucherPopup-codeHolder-voucherType-code']/h4")
                ))
                code = [code.text for code in codes][0]

                time.sleep(1)
                self.webdriver.switch_to.window(self.webdriver.window_handles[0])
                time.sleep(1)
                self.detail_of_coupon['Url'] = self.webdriver.current_url
                self.webdriver.close()

                time.sleep(1)
                self.webdriver.switch_to.window(self.webdriver.window_handles[0])
                self.detail_of_coupon['Code'] = code
            else:
                try:
                    codes = self.webdriver.find_elements(
                        By.XPATH, "//span[@data-testid='voucherPopup-codeHolder-voucherType-code']/h4")
                    code = [code.text for code in codes][0]
                except:
                    self.logger.error("We don't find any code!")

                time.sleep(1)
                self.webdriver.switch_to.window(self.webdriver.window_handles[0])
                time.sleep(1)
                self.detail_of_coupon['Url'] = self.webdriver.current_url
                self.webdriver.close()

                time.sleep(1)
                self.webdriver.switch_to.window(self.webdriver.window_handles[0])
                self.detail_of_coupon['Code'] = code
        except:
            self.logger.error("We don't find buttons: see code & see deal!")
            print("We don't find buttons: see code & see deal!")

    def close_alert(self):
        """
            Closes a pop-up alert by waiting for the close icon to become clickable and then clicking it.
            Logs an error if the close button cannot be clicked.
        """
        try:
            # Wait until the element is clickable
            close_icon = WebDriverWait(self.webdriver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "span[data-testid='CloseIcon']"))
            )
            # Click the close icon
            close_icon.click()
        except:
            self.logger.error("We can't click on close alert button!")
            self.send_telegram_message(self.BOT_TOKEN, self.CHAT_ID, self.MESSAGE)

    def update_url_status(self, url, status):
        """
            Updates the status of a specific URL in the file. Reads all lines from the file, modifies
            the status for the specified URL, and writes the updated lines back to the file.

            Args:
                url (str): The URL whose status needs to be updated.
                status (str): The new status to set for the URL.
        """
        self.send_telegram_message(self.BOT_TOKEN, self.CHAT_ID, "U nderrua statusi i linkut kuponave!")

        # Read all lines from the file
        with open(self.file_path, 'r') as file:
            lines = file.readlines()

        # Write back all lines, updating the status for the specified URL
        with open(self.file_path, 'w') as file:
            for line in lines:
                existing_url, company_name, _ = line.strip().split(', ')
                if existing_url == url:
                    file.write(f"{url}, {company_name}, {status}\n")
                else:
                    file.write(line)

    def get_urls_from_file(self):
        """
            Retrieves URLs with a status of 'False' from the file.
            Reads each line, checks the status, and collects URLs to scrape.

            Returns:
                list: A list of URLs that need to be scraped.
        """
        time.sleep(1)
        urls_to_scrape = []
        with open(self.file_path, 'r') as file:
            for line in file:
                url, company_name, status = line.strip().split(', ')
                if status == 'False':
                    urls_to_scrape.append(url)
        return urls_to_scrape

    def read_links(self):
        """
            Reads all lines from the file and splits each line into URL and status.

            Returns:
                list: A list of lists, where each sublist contains a URL and its status.
        """
        with open(self.file_path, 'r') as file:
            lines = file.readlines()
        links = [line.strip().split(', ') for line in lines]
        return links

    def check_for_see_more_btn(self):
        """
            Checks for the presence of a 'See More' button and clicks it if it is clickable.
            Scrolls the button into view before clicking. Logs an informational message if the
            button is not found or cannot be clicked.
        """
        try:
            # If we have to show more see more button then click on it
            see_more_btn = WebDriverWait(self.webdriver, 3).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//div[@class='r0c5x30']/div")
                )
            )
            self.webdriver.execute_script("arguments[0].scrollIntoView(true);", see_more_btn)
            time.sleep(1)
            see_more_btn.click()
        except:
            self.logger.info("We don't have see more button!")
            print("We don't have see more button!")

    def get_company_name(self):
        current_url = self.webdriver.current_url
        print(f"\n\nCurrent url: {current_url}\n\n")
        with open(self.file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) > 1 and parts[0] == current_url:
                    company_name = parts[1].strip()
                    self.detail_of_coupon['Company Name'] = company_name
                    break
        
        return company_name

    def collect_vouchers(self, xpath):
        """
            Collects and processes voucher details from the specified XPath.

            - Checks for and clicks a 'See More' button if present.
            - Retrieves and logs information about each coupon, including title, description, offer, and any associated code or URL.
            - Handles elements within a modal or popup window and interacts with various parts of the page to extract relevant data.
            - Saves collected voucher details in a database and clears the detail dictionary after processing.

            Args:
                xpath (str): The XPath expression used to locate coupon elements on the page.
        """

        # Check first if we have see more btn to upload all coupon buttons
        self.check_for_see_more_btn()

        div_elements = WebDriverWait(self.webdriver, 3).until(
            EC.presence_of_all_elements_located((By.XPATH, xpath))
        )

        self.logger.info("--------------------------------------------------------------------")
        self.logger.info(f"Number of coupons: {len(div_elements)}")
        self.logger.info(f"We are scrapping: {self.webdriver.current_url}")
        print("\n\n--------------------------------------------------------------------")
        print("Number of coupons: ", len(div_elements))
        print(f"We are scrapping: {self.webdriver.current_url}")
        companyName = self.get_company_name()
        for i in range(1, len(div_elements) + 1):
            self.logger.info(f"Coupon {i}:")
            self.logger.info(f"Inside web element: {xpath}[{i}]")
            print(f"\n\nCoupon {i}:")
            print(f"Inside web element: {xpath}[{i}]")
            button_text = self.check_button_name(xpath, i)

            # Get the name of company for the coupons
            self.get_company_name()

            if button_text == "SUBSCRIBE":
                continue

            # call the function to click the see more btn to get info of coupon
            self.check_for_see_more_btn()

            try:
                #
                banner = WebDriverWait(self.webdriver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"{xpath}[{i}][@data-testid='kam-banner-main-1']")
                    )
                )
                continue
            except:
                pass

            try:
                coupon_btn = WebDriverWait(self.webdriver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"{xpath}[{i}]")
                    )
                )

                # Scroll to the element
                self.webdriver.execute_script("arguments[0].scrollIntoView(true);", coupon_btn)
                time.sleep(1)
                coupon_btn.click()
            except:
                self.logger.error("Coupon btn is not find!")
                print("Coupon btn is not find!")
                continue

            try:
                self.webdriver.switch_to.window(self.webdriver.window_handles[1])
                title_element = WebDriverWait(self.webdriver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@data-testid='voucherPopup-header-popupTitleWrapper']/h4"))
                )
                self.detail_of_coupon['Title'] = title_element.text
            except:
                self.logger.error("Error fetching title!")
                self.send_telegram_message(self.BOT_TOKEN, self.CHAT_ID, self.MESSAGE)
                print("Error fetching title!")

            try:
                # Wait until the button is clickable
                terms_button = WebDriverWait(self.webdriver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//div[@data-testid='voucherPopup-collapsablePanel-header']/button"))
                )
                terms_button.click()
            except:
                self.logger.info("We don't have terms_button for this coupon!")
                print("We don't have terms_button for this coupon!")

            try:
                all_paragraphs = WebDriverWait(self.webdriver, 3).until(EC.presence_of_all_elements_located(
                    (By.XPATH,
                     "//div[@data-testid='voucherPopup-termsAndConditions-root']//div[@data-testid='rich-text-root']/p")
                ))

                for p in all_paragraphs:
                    p_text = p.text.strip()
                    if not p_text:
                        continue  # Skip empty <p> elements

                    b_elements = p.find_elements(By.TAG_NAME, 'b')
                    if b_elements:
                        for b_element in b_elements:
                            field_name = b_element.text.strip(':')
                            field_value = p_text.replace(b_element.text, '').strip()
                            # Remove colon from the value if present
                            field_value = field_value.lstrip(':').strip()
                            self.detail_of_coupon[field_name] = field_value

                    else:
                        # Handle cases where <p> does not contain <b>
                        if 'description' not in self.detail_of_coupon:
                            self.detail_of_coupon['Description'] = p_text

                # Interact with tabs windows and get code and url
                self.get_code_or_url_from_voucher(button_text)  # <-- For getting the code or url of voucher

                # Logs Details
                self.logger.info(f"\n\nTitle: {self.detail_of_coupon.get('Title', None),}")
                self.logger.info(f"Description: {self.detail_of_coupon.get('Description', None)}")
                self.logger.info(f"Offer: {self.detail_of_coupon.get('Offer', None)}")
                self.logger.info(f"Order amount: {self.detail_of_coupon.get('Order amount', None)}")
                self.logger.info(f"Limitation for Users: {self.detail_of_coupon.get('Limitation for Users', None)}")
                self.logger.info(f"Limitations on brands: {self.detail_of_coupon.get('Limitations on Brands', None)}")
                self.logger.info(f"Button Name: {self.detail_of_coupon.get('Button Name', None)}")
                self.logger.info(f"Code: {self.detail_of_coupon.get('Code', None)}")
                self.logger.info(f"URL: {self.detail_of_coupon.get('Url', None)}")

                print(f"\n\nTitle: {self.detail_of_coupon.get('Title', None),}")
                print(f"Description: {self.detail_of_coupon.get('Description', None)}")
                print(f"Offer: {self.detail_of_coupon.get('Offer', None)}")
                print(f"Order amount: {self.detail_of_coupon.get('Order amount', None)}")
                print(f"Limitation for Users: {self.detail_of_coupon.get('Limitation for Users', None)}")
                print(f"Limitations on brands: {self.detail_of_coupon.get('Limitations on Brands', None)}")
                print(f"Button Name: {self.detail_of_coupon.get('Button Name', None)}")
                print(f"Code: {self.detail_of_coupon.get('Code', None)}")
                print(f"URL: {self.detail_of_coupon.get('Url', None)}")
                print(f"Company Name: {self.detail_of_coupon.get('Company Name', None)}")

                # Close modal after fetching data
                self.close_alert()

                # Save the coupon in database
                self.save_details_in_database()

                # Clear the dictionary after processing
                self.detail_of_coupon.clear()
            except:
                self.logger.error("Paragraphs does not exists!")
                print(f"Paragraphs does not exists!")
                # Interact with tabs windows and get code and url
                self.get_code_or_url_from_voucher(button_text)  # <-- For getting the code or url of voucher

                # Close modal after fetching data
                self.close_alert()

                # Save the coupon in database
                self.save_details_in_database()

                # Clear the dictionary after processing
                self.detail_of_coupon.clear()

        # This function checks for last_scrapped column value.
        self.db.update_last_scrapped_column(companyName)

    def save_details_in_database(self):
        """
            Saves the collected coupon details to the database.

            This method retrieves the coupon details from the `detail_of_coupon` dictionary and inserts them into the database using the `insert_coupon` method of the `db` object. It includes fields such as title, description, offer, order amount, limitations for users, limitations on brands, button name, code, and URL.

            Prints a message indicating that the coupon is being saved to the database.
        """

        print(f"Saving coupon to database!")
        self.db.insert_coupon(
            title=self.detail_of_coupon.get('Title', None),
            description=self.detail_of_coupon.get('Description', None),
            offer=self.detail_of_coupon.get('Offer', None),
            order_ammount=self.detail_of_coupon.get('Order amount', None),
            limitations_for_users=self.detail_of_coupon.get('Limitation for Users', None),
            limitations_on_brands=self.detail_of_coupon.get('Limitations on Brands', None),
            button_name=self.detail_of_coupon.get('Button Name', None),
            code=self.detail_of_coupon.get('Code', None),
            url=self.detail_of_coupon.get('Url', None),
            company_name=self.detail_of_coupon.get('Company Name', None),
        )

    def scrape_all_shop_links(self):
        """
            Scrapes voucher information from all shop links.

            This method performs the following steps:
            1. Defines helper functions to check the presence of active and similar vouchers.
            2. Waits for the presence of the active vouchers widget and, if found, collects voucher information using a specified XPath.
            3. Waits for the presence of the similar vouchers widget and, if found, collects voucher information using a different XPath.

            The helper functions `check_active_vouchers` and `check_similar_vouchers` use WebDriverWait to ensure the widgets are present before attempting to collect vouchers.

            The collected voucher details are processed by the `collect_vouchers` method.
        """

        def check_active_vouchers():
            try:
                # Wait for the presence of the element with the specified data-testid
                WebDriverWait(self.webdriver, 3).until(
                    EC.presence_of_element_located((
                        By.XPATH, '//div[@data-testid="active-vouchers-widget"]'))
                )
                return True
            except:
                return False

        def check_similar_vouchers():
            try:
                # Wait for the presence of the element with the specified data-testid
                WebDriverWait(self.webdriver, 3).until(
                    EC.presence_of_element_located((
                        By.XPATH, '//div[@data-testid="similar-vouchers-widget"]'))
                )
                return True
            except:
                return False

        time.sleep(1)
        if check_active_vouchers():
            xpath = '//div[@data-testid="active-vouchers-widget"]/div'
            self.collect_vouchers(xpath)

        if check_similar_vouchers():
            xpath = '//div[@data-testid="similar-vouchers-widget"]/div'
            self.collect_vouchers(xpath)

    def close_webdriver(self):
        self.webdriver.quit()


if __name__ == '__main__':
    scrapping_coupon = ScrappingCoupon()
    while True:
        links = scrapping_coupon.read_links()
        all_true = all(status == 'True' for _, _, status in links)
        if all_true:
            urls = [scrapping_coupon.update_url_status(item[0], False) for item in links]
            print("All links now have the status False!")
        scrapping_coupon.start_webdriver()
