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
NAME = config["NAME"]
MATNR = config["MATNR"]
COURSES = config["COURSES"]  # Load multiple courses from the JSON file
keywords = {"Hinweis", "Lösung", "Loesung", "Hinw"}  # Keywords for L-suffix


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
    course_name = course["COURSE_NAME"]

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

        # **Erstellung fehlender HXX-Ordner**
        for num in h_set:
            h_folder = os.path.join(local_folder, f"H{num}")
            if not os.path.exists(h_folder):
                print(f"Creating folder: {h_folder}")
                os.makedirs(h_folder)

        # **Download fehlender Dateien**
        downloaded_files = {f.replace(".pdf", "") for f in os.listdir(local_folder) if f.endswith(".pdf")}
        missing_files = sorted(set(web_files.keys()) - downloaded_files)

        if missing_files:
            print("Downloading missing files:")
            for file in missing_files:
                file_url = web_files[file]
                print(f"- Downloading {file} from {file_url}")
                driver.get(file_url)
                time.sleep(1)  # Allow some time for the download to complete

        # Verschieben der Dateien in ihre entsprechenden HXX-Ordner basierend auf der Nummer im Dateinamen
        for filename in os.listdir(local_folder):
            file_path = os.path.join(local_folder, filename)
            # Nur echte Dateien (keine Ordner) und nur PDFs berücksichtigen
            if os.path.isfile(file_path) and filename.lower().endswith(".pdf"):
                # Extrahiere die erste Zahlenfolge aus dem Dateinamen
                matches = re.findall(r'\d+', filename)
                if not matches:
                    print(f"Keine Nummer in '{filename}' gefunden, Datei wird übersprungen.")
                    continue

                formatted_num = f"{int(matches[0]):02d}"
                # Verschiebe die Datei nur, wenn es bereits eine H-Datei (also einen Eintrag in h_set) zu dieser Nummer gibt
                if formatted_num in h_set:
                    target_folder = os.path.join(local_folder, f"H{formatted_num}")
                    # Zielordner anlegen, falls er noch nicht existiert
                    if not os.path.exists(target_folder):
                        os.makedirs(target_folder)
                        print(f"Erstelltes Zielverzeichnis: {target_folder}")

                    destination_path = os.path.join(target_folder, filename)
                    if os.path.exists(destination_path):
                        print(f"'{filename}' existiert bereits in '{target_folder}', Überspringe Verschiebung.")
                    else:
                        try:
                            os.rename(file_path, destination_path)
                            print(f"Verschoben: '{filename}' nach '{target_folder}'")
                        except Exception as e:
                            # Fallback: Wenn os.rename fehlschlägt, versuche mit shutil.move
                            shutil.move(file_path, destination_path)
                            print(f"Fallback Verschiebung: '{filename}' nach '{target_folder}'")
                else:
                    print(
                        f"Für '{filename}' wurde keine passende H-Nummer in h_set gefunden, daher keine Verschiebung.")

        # === Hier endet die Schleife, die die PDFs verschiebt ===

        # --- Schritt 2: Löschen nicht verschobener PDFs ---
        for filename in os.listdir(local_folder):
            file_path = os.path.join(local_folder, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(".pdf"):
                try:
                    os.remove(file_path)
                    print(f"Gelöscht: '{filename}' da nicht verschoben.")
                except Exception as e:
                    print(f"Fehler beim Löschen von '{filename}': {e}")

        # --- Schritt 3: Erstellen der Unterordner in jedem H-Ordner und Anlegen der .tex-Dateien ---

        # Definiere das LaTeX-Template mit Platzhaltern für COURSE_NAME, Blattnummer, NAME und MATNR.
        # Die doppelten geschweiften Klammern {{ und }} dienen dazu, einzelne geschweifte Klammern in LaTeX zu erhalten.
        latex_template = r"""\documentclass[10pt,a4paper]{{article}}
        \usepackage[T1]{{fontenc}}
        \usepackage[left=2cm, right=2cm, top=2cm, bottom=2cm]{{geometry}}
        \usepackage{{graphicx}}
        \usepackage{{mathtools}}
        \usepackage{{amssymb}}
        \usepackage{{xcolor}}
        \usepackage{{hyperref}}
        \usepackage{{tikz}}
        \usetikzlibrary{{automata, positioning}} 
        \begin{{document}}
        		\setlength{{\parindent}}{{0pt}} 
        	\part*{{{course_name}, Blatt {sheet_number}}}
        	{student_name}, Matrikelnummer:{matnr} \\
        \end{{document}}
        """

        # Durchlaufe alle Unterordner im local_folder, die dem Muster "H\d{2}" entsprechen
        for folder in os.listdir(local_folder):
            folder_path = os.path.join(local_folder, folder)
            if os.path.isdir(folder_path) and re.match(r'^H\d{2}$', folder):
                m = re.match(r'^H(\d{2})$', folder)
                if m:
                    number = m.group(1)  # Das ist die Blattnummer, z. B. "01"

                    # --- Erstellen des Unterordners HXX und dessen Tex-Unterordner ---
                    h_subfolder = os.path.join(folder_path, f"H{number}")
                    if not os.path.exists(h_subfolder):
                        os.makedirs(h_subfolder)
                        print(f"Erstellter Unterordner: '{h_subfolder}'")
                    h_tex_folder = os.path.join(h_subfolder, "Tex")
                    if not os.path.exists(h_tex_folder):
                        os.makedirs(h_tex_folder)
                        print(f"Erstellter 'Tex'-Ordner in '{h_subfolder}'")
                    # Erstelle die .tex-Datei in HXX/Tex und benenne sie als HXX.tex
                    h_tex_file_path = os.path.join(h_tex_folder, f"H{number}.tex")
                    with open(h_tex_file_path, "w", encoding="utf-8") as f:
                        f.write(latex_template.format(course_name=course_name,
                                                      sheet_number=number,
                                                      student_name=NAME,
                                                      matnr=MATNR))
                    print(f".tex-Datei in '{h_tex_folder}' erstellt: {h_tex_file_path}")

                    # --- Erstellen des Unterordners PXX und dessen Tex-Unterordner ---
                    p_subfolder = os.path.join(folder_path, f"P{number}")
                    if not os.path.exists(p_subfolder):
                        os.makedirs(p_subfolder)
                        print(f"Erstellter Unterordner: '{p_subfolder}'")
                    p_tex_folder = os.path.join(p_subfolder, "Tex")
                    if not os.path.exists(p_tex_folder):
                        os.makedirs(p_tex_folder)
                        print(f"Erstellter 'Tex'-Ordner in '{p_subfolder}'")
                    # Erstelle die .tex-Datei in PXX/Tex und benenne sie als PXX.tex
                    p_tex_file_path = os.path.join(p_tex_folder, f"P{number}.tex")
                    with open(p_tex_file_path, "w", encoding="utf-8") as f:
                        f.write(latex_template.format(course_name=course_name,
                                                      sheet_number=number,
                                                      student_name=NAME,
                                                      matnr=MATNR))
                    print(f".tex-Datei in '{p_tex_folder}' erstellt: {p_tex_file_path}")
                else:
                    print(f"Error while extracting the number from '{folder}'")

print("Success!")
