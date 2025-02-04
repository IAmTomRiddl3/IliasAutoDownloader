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
    if course_property in ["SHEET", "CODING_SHEET"]:
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

        # **Creation of missing HXX folders**
        for num in h_set:
            h_folder = os.path.join(local_folder, f"H{num}")
            if not os.path.exists(h_folder):
                print(f"Creating folder: {h_folder}")
                os.makedirs(h_folder)

        # **Download missing files**
        downloaded_files = {f.replace(".pdf", "") for f in os.listdir(local_folder) if f.endswith(".pdf")}
        missing_files = sorted(set(web_files.keys()) - downloaded_files)

        if missing_files:
            print("Downloading missing files:")
            for file in missing_files:
                file_url = web_files[file]
                print(f"- Downloading {file} from {file_url}")
                driver.get(file_url)
                time.sleep(1)  # Allow some time for the download to complete

        # Move the files to their corresponding HXX folders based on the number in the filename
        for filename in os.listdir(local_folder):
            file_path = os.path.join(local_folder, filename)
            # Only actual files (no folders) and only PDFs are considered
            if os.path.isfile(file_path) and filename.lower().endswith(".pdf"):
                # Extract the first digit sequence from the filename
                matches = re.findall(r'\d+', filename)
                if not matches:
                    print(f"No number found in '{filename}', skipping file.")
                    continue

                formatted_num = f"{int(matches[0]):02d}"
                # Move the file only if there's a matching H-number (an entry in h_set)
                if formatted_num in h_set:
                    target_folder = os.path.join(local_folder, f"H{formatted_num}")
                    # Create the target directory if it doesn't exist
                    if not os.path.exists(target_folder):
                        os.makedirs(target_folder)
                        print(f"Created target directory: {target_folder}")

                    destination_path = os.path.join(target_folder, filename)
                    if os.path.exists(destination_path):
                        print(f"'{filename}' already exists in '{target_folder}', skipping move.")
                    else:
                        try:
                            os.rename(file_path, destination_path)
                            print(f"Moved '{filename}' to '{target_folder}'")
                        except Exception as e:
                            # Fallback: If os.rename fails, try shutil.move
                            shutil.move(file_path, destination_path)
                            print(f"Fallback move: '{filename}' to '{target_folder}'")
                else:
                    print(f"No matching H-number in h_set for '{filename}', so no move performed.")

        # Here ends the loop that moves the PDFs

        # --- Step 2: Delete non-moved PDFs ---
        for filename in os.listdir(local_folder):
            file_path = os.path.join(local_folder, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(".pdf"):
                try:
                    os.remove(file_path)
                    print(f"Deleted '{filename}' because it was not moved.")
                except Exception as e:
                    print(f"Error deleting '{filename}': {e}")

        # --- Step 3: Create subfolders in each H-folder and create the .tex files ---

        # Define the LaTeX template with placeholders for COURSE_NAME, sheet_number, NAME, and MATNR.
        # The double braces {{ and }} are needed to keep single braces in LaTeX.
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

        # Go through all subfolders in local_folder that match the pattern "H\d{2}"
        for folder in os.listdir(local_folder):
            folder_path = os.path.join(local_folder, folder)
            if os.path.isdir(folder_path) and re.match(r'^H\d{2}$', folder):
                m = re.match(r'^H(\d{2})$', folder)
                if m:
                    number = m.group(1)  # This is the sheet number, e.g. "01"

                    # --- Create the subfolder HXX and its Tex subfolder ---
                    h_subfolder = os.path.join(folder_path, f"H{number}")
                    if not os.path.exists(h_subfolder):
                        os.makedirs(h_subfolder)
                        print(f"Created subfolder: '{h_subfolder}'")
                    h_tex_folder = os.path.join(h_subfolder, "Tex")
                    if not os.path.exists(h_tex_folder):
                        os.makedirs(h_tex_folder)
                        print(f"Created 'Tex' folder in '{h_subfolder}'")
                    # Create the .tex file in HXX/Tex and name it HXX.tex
                    h_tex_file_path = os.path.join(h_tex_folder, f"H{number}.tex")
                    with open(h_tex_file_path, "w", encoding="utf-8") as f:
                        f.write(latex_template.format(course_name=course_name,
                                                      sheet_number=number,
                                                      student_name=NAME,
                                                      matnr=MATNR))
                    print(f".tex file created in '{h_tex_folder}': {h_tex_file_path}")

                    # --- Create the subfolder PXX and its Tex subfolder ---
                    p_subfolder = os.path.join(folder_path, f"P{number}")
                    if not os.path.exists(p_subfolder):
                        os.makedirs(p_subfolder)
                        print(f"Created subfolder: '{p_subfolder}'")
                    p_tex_folder = os.path.join(p_subfolder, "Tex")
                    if not os.path.exists(p_tex_folder):
                        os.makedirs(p_tex_folder)
                        print(f"Created 'Tex' folder in '{p_subfolder}'")
                    # Create the .tex file in PXX/Tex and name it PXX.tex
                    p_tex_file_path = os.path.join(p_tex_folder, f"P{number}.tex")
                    with open(p_tex_file_path, "w", encoding="utf-8") as f:
                        f.write(latex_template.format(course_name=course_name,
                                                      sheet_number=number,
                                                      student_name=NAME,
                                                      matnr=MATNR))
                    print(f".tex file created in '{p_tex_folder}': {p_tex_file_path}")

                    # If the course is of type CODING_SHEET, create an additional folder for code
                    if course_property == "CODING_SHEET":
                        code_folder = os.path.join(folder_path, f"Code-H{number}")
                        if not os.path.exists(code_folder):
                            os.makedirs(code_folder)
                            print(f"Created coding folder: '{code_folder}'")
                else:
                    print(f"Error while extracting the number from '{folder}'")

print("Success!")
