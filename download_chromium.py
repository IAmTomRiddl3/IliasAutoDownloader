import time
import os
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# === CONFIGURATION ===
CONFIG_FILE = "config.json"
PUBLIC_CONFIG_FILE = "public_config.json"

# Load the configuration file, fallback to public_config.json if not found
if not os.path.exists(CONFIG_FILE):
    print(f"{CONFIG_FILE} not found. Using {PUBLIC_CONFIG_FILE} as fallback.")
    CONFIG_FILE = PUBLIC_CONFIG_FILE

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

ILIAS_URL = config["ILIAS_URL"]
USERNAME = config["USERNAME"]
PASSWORD = config["PASSWORD"]
COURSES = config["COURSES"]  # Load multiple courses from the JSON file


def setup_webdriver(download_folder):
    """
    Creates a new Chrome WebDriver with the specified download folder.
    """
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_folder,  # Set the specific course download folder
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True  # PDFs directly download instead of opening in Chrome
    })

    return webdriver.Chrome(options=chrome_options)


def login(driver):
    """
    Logs into ILIAS with the given WebDriver instance.
    """
    driver.get(ILIAS_URL + "/login.php?client_id=Uni_Stuttgart&cmd=force_login&lang=de")
    driver.find_element(By.NAME, "login_form/input_3/input_4").send_keys(USERNAME)
    driver.find_element(By.NAME, "login_form/input_3/input_5").send_keys(PASSWORD + Keys.RETURN)
    time.sleep(3)  # Wait for login


# === PROCESS ALL COURSES ===
for course in COURSES:
    course_id = course["COURSE_ID"]
    course_property = course["COURSE_PROPERTY"]
    local_folder = course["LOCAL_FOLDER"]

    # Ensure the base local folder exists
    os.makedirs(local_folder, exist_ok=True)

    # Start a new WebDriver for each course and log in
    driver = setup_webdriver(local_folder)
    login(driver)

    # Open the course page
    course_url = f"{ILIAS_URL}/ilias.php?baseClass=ilrepositorygui&ref_id={course_id}"
    print(f"Checking Course: {course_property} ({course_url})")

    driver.get(course_url)
    time.sleep(2)

    # Collect all files from the website
    web_files = {}
    for link in driver.find_elements(By.CLASS_NAME, "il_ContainerItemTitle"):
        file_name = link.text.strip()
        file_link = link.get_attribute("href")
        if file_name and file_link:
            web_files[file_name] = file_link

    # Handle LECTURE-type courses (Standard download behavior)
    if course_property == "LECTURE":
        downloaded_files = {f.replace(".pdf", "") for f in os.listdir(local_folder) if f.endswith(".pdf")}
        missing_files = sorted(set(web_files.keys()) - downloaded_files)

        if missing_files:
            print(f"Downloading missing files for {course_property}:")
            for file in missing_files:
                file_url = web_files[file]
                print(f"- Downloading {file} from {file_url}")
                driver.get(file_url)
                time.sleep(2)
        else:
            print(f"All files are already downloaded for {course_property}.")

    # Handle SHEET-type courses (Check if multiple files contain the same number)
    elif course_property == "SHEET":
        downloaded_files = {f.replace(".pdf", "") for f in os.listdir(local_folder) if f.endswith(".pdf")}
        missing_files = sorted(set(web_files.keys()) - downloaded_files)
        if missing_files:
            print(f"Downloading missing files for {course_property}:")
            for file in missing_files:
                print(f"- {file}")


        else:
            print(f"All files are already downloaded for {course_property}.")

    driver.quit()  # Close WebDriver after processing the course

print("Success!")
