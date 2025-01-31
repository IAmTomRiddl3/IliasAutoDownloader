import json
import time
import os
import extras
from selenium import webdriver
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# === CONFIGURATION ===
# Load the configuration file, fallback to public_config.json if not found
CONFIG_FILE = extras.config_file()

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

ILIAS_URL = config["ILIAS_URL"]
LOGIN_URL = config["LOGIN_URL"]
USERNAME = config["USERNAME"]
PASSWORD = config["PASSWORD"]
COURSES = config["COURSES"]  # Load multiple courses from the JSON file

# === SELENIUM SETUP ===
options = webdriver.FirefoxOptions()
options.set_preference("browser.download.folderList", 2)
options.set_preference("pdfjs.disabled", True)
options.set_preference("browser.download.manager.showWhenStarting", False)
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf, application/octet-stream")

course_id = COURSES[0]["COURSE_ID"]
course_property = COURSES[0]["COURSE_PROPERTY"]
local_folder = COURSES[0]["LOCAL_FOLDER"]
course_url = f"{ILIAS_URL}/ilias.php?baseClass=ilrepositorygui&ref_id={course_id}"

# === PROCESS ALL COURSES ===
for course in COURSES:
    course_id = course["COURSE_ID"]
    course_property = course["COURSE_PROPERTY"]
    local_folder = course["LOCAL_FOLDER"]

    course_url = f"{ILIAS_URL}/ilias.php?baseClass=ilrepositorygui&ref_id={course_id}"
    print(f"Checking Course: {course_property} ({course_url})")


    options.set_preference("browser.download.dir", local_folder)
    driver = webdriver.Firefox(options=options)

    # === LOGIN ===
    driver.get(ILIAS_URL + "/login.php?client_id=Uni_Stuttgart&cmd=force_login&lang=de")
    driver.find_element(By.NAME, "login_form/input_3/input_4").send_keys(USERNAME)
    driver.find_element(By.NAME, "login_form/input_3/input_5").send_keys(PASSWORD + Keys.RETURN)
    time.sleep(2)  # Warte auf Login

    # Ensure the local folder exists
    os.makedirs(local_folder, exist_ok=True)

    # Retrieve existing files in the local folder
    downloaded_files = {f.replace(".pdf", "") for f in os.listdir(local_folder) if f.endswith(".pdf")}

    # Open the course page
    driver.get(course_url)
    time.sleep(2)

    # Collect all files from the website
    web_files = {}
    for link in driver.find_elements(By.CLASS_NAME, "il_ContainerItemTitle"):
        file_name = link.text.strip()
        file_link = link.get_attribute("href")
        if file_name and file_link:
            web_files[file_name] = file_link

    # Identify missing files
    missing_files = sorted(set(web_files.keys()) - downloaded_files)

    # Download missing files if any exist
    if missing_files:
        print(f"Downloading missing files for {course_property}:")
        for file in missing_files:
            file_url = web_files[file]
            print(f"- Downloading {file} from {file_url}")
            driver.get(file_url)
            time.sleep(2)
    else:
        print(f"All files are already downloaded for {course_property}.")

print("Success!")
driver.quit()
