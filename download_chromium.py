import time
import os
import shutil
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
keywords = {"Hinweis", "Lösung"}  # Keywords for L-suffix


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

    # Handle SHEET-type courses
    if course_property == "SHEET":
        h_set = set()
        l_set = set()

        print(f"Processing missing files for {course_property}:")

        for file in web_files.keys():
            match = re.findall(r'\d+', file)
            if match:
                formatted_num = f"{int(match[0]):02d}"  # Ensure two-digit format
                if any(word in file for word in keywords):
                    l_set.add(formatted_num)
                else:
                    h_set.add(formatted_num)

        print("H-Prefix Set:", sorted(h_set))
        print("L-Prefix Set:", sorted(l_set))

        # Ensure all required H-prefixed folders exist
        existing_folders = {folder for folder in os.listdir(local_folder) if os.path.isdir(os.path.join(local_folder, folder))}
        missing_folders = sorted(set(f"H{num}" for num in h_set) - existing_folders)

        if missing_folders:
            print("Missing folders that need to be created:")
            for folder in missing_folders:
                print(f"- {folder}")
                os.makedirs(os.path.join(local_folder, folder), exist_ok=True)  # Create missing folder

        # Check which files are missing in the corresponding HXX folders
        downloaded_files = {f.replace(".pdf", "") for f in os.listdir(local_folder) if f.endswith(".pdf")}
        missing_files = sorted(set(web_files.keys()) - downloaded_files)

        if missing_files:
            print("Downloading missing files:")
            for file in missing_files:
                file_url = web_files[file]
                print(f"- Downloading {file} from {file_url}")
                driver.get(file_url)
                time.sleep(2)  # Allow some time for the download to complete

        # Move files to their respective HXX folders if they don't already exist
        for num in h_set:
            h_folder = os.path.join(local_folder, f"H{num}")

            if os.path.exists(h_folder):
                for prefix in ["H", "L"]:
                    filename = f"{prefix}{num}.pdf"
                    source_path = os.path.join(local_folder, filename)
                    destination_path = os.path.join(h_folder, filename)

                    # Überprüfung, ob die Datei bereits im HXX-Ordner existiert
                    if os.path.exists(source_path) and not os.path.exists(destination_path):
                        print(f"Moving {filename} to {h_folder}")
                        shutil.move(source_path, destination_path)
                    elif os.path.exists(destination_path):
                        print(f"{filename} already exists in {h_folder}, leaving in {local_folder}")

    driver.quit()  # Close WebDriver after processing the course

print("Success!")
