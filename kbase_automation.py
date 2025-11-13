# kbase_automation.py
import os
import time
import json
import argparse
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, JavascriptException

# ---------------- USER CONFIG ----------------
# Set these environment variables or edit them manually before running.
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", r"/path/to/chromedriver")
BRAVE_BINARY_PATH = os.getenv("BRAVE_BINARY_PATH", r"/path/to/brave")
NARRATIVE_URL = os.getenv(
    "KBASE_NARRATIVE_URL", "https://narrative.kbase.us/narrative/YOUR_NARRATIVE_ID")
COOKIES_FILE = os.getenv("KBASE_COOKIES_FILE", "kbase_google_cookies.json")

# Optional advanced config
WAIT_POLL_SECONDS = int(os.getenv("KBASE_WAIT_POLL_SECONDS", "8"))
OUTPUT_PREFIX = os.getenv("KBASE_OUTPUT_PREFIX", "Auto_")
USER_DATA_DIR = os.getenv("BRAVE_USER_DATA_DIR", r"/path/to/brave/user/data")
PROFILE_DIR = os.getenv("BRAVE_PROFILE_DIR", "Default")
# ------------------------------------------------


def fetch_fastq_urls_from_ena(srx):
    """Fetch fastq FTP URLs for an SRX using ENA filereport API."""
    url = (f"https://www.ebi.ac.uk/ena/portal/api/filereport?"
           f"accession={srx}&result=read_run&fields=run_accession,fastq_ftp&download=true")
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"ENA request failed {r.status_code}")
    lines = r.text.strip().splitlines()
    if len(lines) <= 1:
        raise RuntimeError("No results from ENA for that accession.")
    headers = lines[0].split('\t')
    idx = {h: i for i, h in enumerate(headers)}
    results = []
    for ln in lines[1:]:
        cols = ln.split('\t')
        ftp_field = cols[idx['fastq_ftp']].strip()
        if ftp_field:
            parts = [p.strip() for p in ftp_field.split(';') if p]
            for p in parts:
                if p.startswith("ftp://"):
                    results.append("https://" + p[len("ftp://"):])
                else:
                    results.append(p)
    return list(dict.fromkeys(results))  # dedupe


def start_brave_driver(chromedriver_path, brave_path):
    options = webdriver.ChromeOptions()
    options.binary_location = brave_path
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")

    # Reuse logged-in Brave profile (optional)
    if os.path.exists(USER_DATA_DIR):
        options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
        options.add_argument(f"--profile-directory={PROFILE_DIR}")

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def save_cookies(driver, filename):
    cookies = driver.get_cookies()
    with open(filename, "w", encoding="utf-8") as fh:
        json.dump(cookies, fh, indent=2)
    print(f"[+] Saved cookies to {filename}")


def load_cookies(driver, filename):
    with open(filename, "r", encoding="utf-8") as fh:
        cookies = json.load(fh)
    driver.delete_all_cookies()
    for c in cookies:
        try:
            driver.add_cookie({
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".kbase.us")
            })
        except Exception:
            pass
    print(f"[+] Loaded cookies from {filename}")


def wait_for_job_completion(driver, timeout_minutes=30):
    """Poll until job shows 'Completed' or timeout."""
    timeout = time.time() + timeout_minutes * 60
    while time.time() < timeout:
        time.sleep(WAIT_POLL_SECONDS)
        try:
            if driver.find_elements(By.XPATH, "//*[contains(text(),'Completed')]"):
                print("[+] Job Completed.")
                return "completed"
            if driver.find_elements(By.XPATH, "//*[contains(text(),'Error')]"):
                print("[!] Job Error.")
                return "error"
            print("... waiting for job to finish")
        except Exception:
            pass
    print("[!] Timeout waiting for job.")
    return "timeout"


def find_app_panel(driver, app_title_partial):
    xpath = f"//*[contains(normalize-space(.), '{app_title_partial}')]"
    els = driver.find_elements(By.XPATH, xpath)
    for el in els:
        try:
            return el.find_element(By.XPATH, "./ancestor::div[contains(@class,'kb-app')]")
        except Exception:
            pass
    raise NoSuchElementException(f"App '{app_title_partial}' not found.")


def open_configure_in_panel(panel):
    try:
        btn = panel.find_element(
            By.XPATH, ".//button[contains(., 'Configure')]")
        btn.click()
        time.sleep(2)
    except NoSuchElementException:
        pass


def set_import_urls_in_panel(panel, urls):
    """Locate the URL(s) input area and safely set the URLs with visibility wait."""
    try:
        driver = panel.parent
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        element = WebDriverWait(panel.parent, 20).until(
            EC.visibility_of_any_elements_located(
                (By.XPATH,
                 ".//textarea | .//input[@type='text' or @type='url']")
            )
        )
        target = element[0]
        driver.execute_script("arguments[0].scrollIntoView(true);", target)
        time.sleep(1)
        target.click()
        time.sleep(0.5)
        target.clear()
        joined_urls = "\n".join(urls)
        target.send_keys(joined_urls)
        print(f"[+] Inserted URLs into {target.tag_name}")
        return True
    except Exception as e:
        print(f"[!] Could not automatically insert URLs: {e}")
        return False


def click_run_in_panel(panel):
    try:
        btn = panel.find_element(By.XPATH, ".//button[contains(., 'Run')]")
        btn.click()
        print("[+] Run clicked.")
    except Exception as e:
        print("Run click failed:", e)


def main(args):
    srx = args.srx.strip()
    print(f"[*] Fetching FASTQ URLs for {srx}")
    urls = fetch_fastq_urls_from_ena(srx)
    print(f"[+] Found URLs: {urls}")

    driver = start_brave_driver(CHROMEDRIVER_PATH, BRAVE_BINARY_PATH)
    driver.get("https://narrative.kbase.us")
    time.sleep(5)

    if os.path.exists(COOKIES_FILE):
        load_cookies(driver, COOKIES_FILE)
        driver.get(NARRATIVE_URL)
        print("[*] Waiting for KBase to load (30s)...")
        time.sleep(30)
    else:
        print("[*] No cookie file found. Please log in manually.")
        input("After logging in and reaching your Narrative, press Enter here...")
        save_cookies(driver, COOKIES_FILE)

    driver.get(NARRATIVE_URL)
    print("[*] Waiting for Narrative to fully load (30s)...")
    time.sleep(30)

    # Step 1: Import reads
    try:
        import_panel = find_app_panel(driver, "Import Paired-End Reads")
        driver.execute_script(
            "arguments[0].scrollIntoView(true);", import_panel)
        open_configure_in_panel(import_panel)
        if not set_import_urls_in_panel(import_panel, urls):
            input("[!] Paste URLs manually into the app, then press Enter...")
        click_run_in_panel(import_panel)
        print("[*] Waiting for Import job to complete...")
        status = wait_for_job_completion(driver, 40)
        if status != "completed":
            print("[!] Import failed.")
            return
    except Exception as e:
        print("Import step error:", e)
        return

    print("[+] Import finished successfully. The rest of the workflow can now run manually.")
    input("Press Enter to close the browser when ready.")
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("srx", help="SRX accession (e.g., SRX179497)")
    args = parser.parse_args()
    main(args)
