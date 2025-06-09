import os
import time
import re

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from ManageDatabase import DatabaseDetails


class ScrapeCouponIconAndAbout:
    file_path = 'shop_links.txt'

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
        self.db = DatabaseDetails()  # Creating an instance of ManageDB
        self.db.create_table()  # Ensure the table is created

    def start_webdriver(self):
        """
            Begins the web scraping process by first checking and scraping all links,
            then iterates through URLs from a file. For each URL, configures the logger,
            starts the WebDriver, maximizes the browser window, and performs scraping.
            Updates the URL status to 'True' after scraping is complete.
        """
        # First check all links and scrape them before starting
        self.alphabet_section()
        urls = self.get_urls_from_file()
        for url in urls:
            self.webdriver.get(url)
            self.webdriver.maximize_window()
            self.scrape_extra_details(url)

            # Update the URL status to True after scraping
            self.update_url_status(url, 'True')

    def scrape_extra_details(self, url):
        """
            Scrapes additional details such as the company icon and description.
            Waits for the company icon and description to load and saves them to the database.
        """
        time.sleep(3)  # Delay to ensure that elements are fully loaded

        icon_link = None
        about = None
        company_name = self.get_company_name_from_file(url)

        # Attempt to scrape the company icon
        try:
            company_icon = WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='gxs4fb0']//img")
                )
            )
            icon_link = company_icon.get_attribute('src')
            print("URL: ", icon_link)

            # Define a list of paths to check for in the URL
            paths = ['/a/', '/b/', '/l/', '/k/', '/c/', '/t/', '/d/', '/e/', '/f/', '/g/', '/h/', '/i/', '/j/', '/m/', '/9/', '/2/', '/n/', '/o/', '/p/', '/q/', '/r/', '/s/', '/8/', '/u/', '/1/', '/v/', '/w/', '/y/', '/z/']

            # Initialize the word variable
            word = "Not Found"

            # Iterate over each path to check if it's in the URL
            for path in paths:
                if path in icon_link:
                    # Extract the word between the path and the next '.'
                    word = icon_link.split(path)[1].split('.')[0]
                    break  # Exit the loop once the match is found

            print("Company name: ", word)
            print("\n\n")
        except Exception as e:
            print(f"Error getting the icon link: {e}")

        try:
            company_about = WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@data-testid=\'sidebar-text-sidebar-1\']//div[@class=\'_1mq6bor6\']')
                )
            )
            about = company_about.text.strip()
        except Exception as e:
            print(f"Error getting the description: {e}")

        # Save details to the database
        if icon_link and about:
            self.db.insert_details(company_name, icon_link, about)

    def get_company_name_from_file(self, url):
        """
            Retrieves the company name from the file based on the URL.

            Args:
                url (str): The URL for which the company name needs to be retrieved.

            Returns:
                str: The company name associated with the URL.
        """
        with open(self.file_path, 'r') as file:
            for line in file:
                file_url, company_name, status = line.strip().split(', ')
                if file_url == url:
                    return company_name
        return "Unknown Company"

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
            print(f"Number of sections: {number_of_sections}")
            self.save_all_coupon_links(number_of_sections)

        except TimeoutException:
            pass

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
                    continue

                for link in all_links:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    count_hrefs += 1
                    if href not in existing_urls:
                        file.write(f"{href}, {text}, False\n")
                        existing_urls[href] = {'text': text, 'status': 'False'}

        print(f"Number of urls to scrape: {count_hrefs}")

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
        If the file does not exist, it creates it and calls the alphabet_section method.

        Returns:
            list: A list of lists, where each sublist contains a URL and its status.
        """
        if not os.path.exists(self.file_path):
            # Create the file if it doesn't exist
            open(self.file_path, 'w').close()
            # Call the alphabet_section method after creating the file
            self.alphabet_section()

        # Now read the file
        with open(self.file_path, 'r') as file:
            lines = file.readlines()
        links = [line.strip().split(', ') for line in lines]
        return links

    def update_url_status(self, url, status):
        """
            Updates the status of a specific URL in the file. Reads all lines from the file, modifies
            the status for the specified URL, and writes the updated lines back to the file.

            Args:
                url (str): The URL whose status needs to be updated.
                status (str): The new status to set for the URL.
        """

        # Read all lines from the file
        with open(self.file_path, 'r') as file:
            lines = file.readlines()

        # Write back only the lines that are not for the URL being updated
        with open(self.file_path, 'w') as file:
            for line in lines:
                file_url, company_name, file_status = line.strip().split(', ')
                if file_url == url:
                    file.write(f"{url}, {company_name}, {status}\n")
                else:
                    file.write(line)

# Ensure to run the script if this is the entry point
if __name__ == '__main__':
    scraper = ScrapeCouponIconAndAbout()
    scraper.start_webdriver()
