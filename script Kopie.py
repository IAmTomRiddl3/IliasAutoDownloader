import time
import os
from selenium import webdriver
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def download(kurs_url):
    driver.get(kurs_url)
    print(f"Prüfe Kurs: {kurs_url}")
    driver.get(kurs_url)
    time.sleep(2)

    # Safe the found files with their links
    web_files = {}
    for link in driver.find_elements(By.CLASS_NAME, "il_ContainerItemTitle"):
        file_name = link.text.strip()
        file_link = link.get_attribute("href")  # Grab the matching file link
        if file_name and file_link:
            web_files[file_name] = file_link

    # Find missing files
    missing_files = sorted(set(web_files.keys()) - downloaded_files)

    # Print out missing files
    if missing_files:
        print("Not yet downloaded:")
        for file in missing_files:
            print(f"- {file}")

        # Download missing files
        for file in missing_files:
            file_url = web_files[file]
            print(f"Lade herunter: {file} von {file_url}")
#            driver.get(file_url)  # Datei aufrufen
#            time.sleep(2)  # Warten, damit der Download abgeschlossen wird
            link_element = driver.find_element(By.LINK_TEXT, file)
            link_element.click()
            time.sleep(1)  # Warten auf Download-Abschluss
            downloaded_files.add(file)  # Aktualisieren der Liste

    else:
        print("Everything is downloaded.")

    print("Success!")
    driver.quit()


def course_chooser() -> str:
    THEO_FOLDER = "/home/acceus/Documents/Studium/Uebungblaetter/Theo_1/uebungsblaetter"
    PSE_FOLDER = "/home/acceus/Documents/Studium/Uebungblaetter/Programmierung_und_Softwareentwicklung/Vorlesungsfolien"
    MATHE_FOLDER = "/home/acceus/Documents/Studium/Uebungblaetter/Mathe_1/Uebungsblaetter"

    course = input("Which course do you want to download? ").strip().lower()

    print(f"Downloading course: {course}")

    local = {
        "theo": THEO_FOLDER,
        "pse": PSE_FOLDER,
        "mathe": MATHE_FOLDER,
        "quit": ""
    }.get(course, "")

    if not local:
        print(f"No such course: {course}")
        local = course_chooser()

    return local


# === CONFIGURATION ===
ILIAS_URL = "https://ilias3.uni-stuttgart.de"
KURS_BASE_URL = "/ilias.php?baseClass=ilrepositorygui&ref_id="
KURS_URLS = [
    "3889792",
    "3861265",
    "3893223",
]
USERNAME = "st192391"
PASSWORD = "5$%tWG6PHJUpm$EQidZu!3nyDe8o"
# Local Folder that will be matched with the files online and the missing files will be downloaded to



LOCAL_FOLDER = course_chooser()

if LOCAL_FOLDER == "":
    exit(0)

downloaded_files = {f.replace(".pdf", "") for f in os.listdir(LOCAL_FOLDER) if f.endswith(".pdf")}


# === SELENIUM SETUP ===
options = webdriver.FirefoxOptions()
firefox_profile = FirefoxProfile()
firefox_profile.set_preference("pdfjs.disabled", True)
firefox_profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf, application/octet-stream")
firefox_profile.set_preference("browser.download.dir", LOCAL_FOLDER)
firefox_profile.set_preference("browser.download.folderList",2)
firefox_profile.set_preference("browser.download.manager.showWindow", False)
options.profile = firefox_profile

driver = webdriver.Firefox(options=options)




# === LOGIN ===
driver.get(ILIAS_URL + "/login.php?client_id=Uni_Stuttgart&cmd=force_login&lang=de")
driver.find_element(By.NAME, "login_form/input_3/input_4").send_keys(USERNAME)
driver.find_element(By.NAME, "login_form/input_3/input_5").send_keys(PASSWORD + Keys.RETURN)
time.sleep(2)  # Warte auf Login

half_url = ILIAS_URL + KURS_BASE_URL

if course == "theo":
    download(half_url+ KURS_URLS[0])
elif course == "pse":
    download(half_url+ KURS_URLS[1])
else:
    download(half_url+ KURS_URLS[2])


