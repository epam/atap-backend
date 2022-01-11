import time

from selenium.webdriver.remote.webelement import WebElement
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import uuid


def _check_for_error_popup(driver):
    headers = driver.find_elements_by_tag_name("h1")
    for header in headers:
        if header.get_attribute("innerHTML") == "Error":
            assert False, "An error dialog popped up, probably a backend communication problem!"


def _find_element_with_contents(driver, tag_name, contents):
    elements_of_matching_type = driver.find_elements_by_tag_name(tag_name)
    for element in elements_of_matching_type:
        if element.get_attribute("innerHTML") == contents:
            return element
    else:
        assert False, f"<{tag_name}> element that says '{contents}' not found!"


def step_1(driver: webdriver.Firefox, address):
    driver.get(address)
    assert driver.title == "Accessibility Testing Automation Platform", "Failed to open ATAP"
    login_button = driver.find_elements_by_tag_name("button")
    assert len(login_button) == 2, f"There should be exactly 2 buttons, but there are {len(login_button)} - login page did not open!"
    login_button = login_button[1]
    assert login_button.get_attribute("innerHTML") == "Log In", "Button does not say 'Log In' - login page did not open!"
    input_fields = driver.find_elements_by_tag_name("input")
    assert len(input_fields) == 2, f"There should be exactly 2 input fields, but there are {len(input_fields)} - login page did not open!"
    login_field = input_fields[0]
    password_field = input_fields[1]
    return login_field, password_field, login_button


def step_2(driver: webdriver.Firefox, login_field: WebElement, password_field: WebElement, login_button: WebElement, login, password):
    login_field.send_keys(login)
    password_field.send_keys(password)
    login_button.click()
    _check_for_error_popup(driver)
    header = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.TAG_NAME, "h2"))
    )
    assert header.get_attribute("innerHTML") == "My Projects", "'My Projects' page did not open after login!"


def step_3(driver: webdriver.Firefox):
    _find_element_with_contents(driver, "button", "Create New Project").click()

    project_name = "Automatic Test Project "+str(uuid.uuid4())[:7]

    to_find_and_fill = {
        "Project Name": project_name,
        "Main URL": "https://epam.com",
        "Version": 1,
        "Project Description (scope)": "Test project scope",
        "Company Name": "Test company name",
        "Number of Testers": 1
    }

    for label in driver.find_elements_by_tag_name("label"):
        for field_name, field_value in to_find_and_fill.items():
            if label.get_attribute("innerHTML").startswith(field_name):
                field = driver.find_element_by_id(label.get_attribute("for"))
                field.send_keys(field_value)
                del to_find_and_fill[field_name]
                break

    assert len(to_find_and_fill) == 0, f"Did not find the following fields:{', '.join(to_find_and_fill)}"
    print(f"Generated project name: '{project_name}'")
    return project_name


def step_4(driver: webdriver.Firefox):
    save_button = _find_element_with_contents(driver, "button", "Save")
    save_button.click()
    try:
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element((By.XPATH, "//div[@role = 'progressbar']"))
        )
    except TimeoutException:
        assert False, "URL Checking appears to be stuck, 30s have passed with no results!"

    assert not save_button.is_enabled(), "Save button is still enabled, project did not save!"


def step_5(driver: webdriver.Firefox):
    _find_element_with_contents(driver, "button", "Go to Sitemap").click()
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "//h2[text() = 'Sitemap']"))
    )
    _find_element_with_contents(driver, "button", "Create Pages Automatically").click()
    _find_element_with_contents(driver, "button", "Create").click()

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[text() = 'Sitemap generation is in progress.']"))
        )
    except TimeoutException:
        assert False, "Sitemap generation did not start after 10s!"


def step_6(driver: webdriver.Firefox):
    try:
        WebDriverWait(driver, 600).until(
            EC.invisibility_of_element((By.XPATH, "//div[text() = 'Sitemap generation is in progress.']"))
        )
    except TimeoutException:
        assert False, "Sitemap generation did not complete in 10 minutes, something must be wrong"

    pages = driver.find_elements_by_xpath("//td[text() = 'https://epam.com']")
    assert len(pages) > 0, "Root page did not get created, sitemap appears to be broken!"


def step_7(driver: webdriver.Firefox):
    checkboxes = driver.find_elements_by_xpath("//button[@role = 'checkbox']")
    checkboxes[1].click()
    _find_element_with_contents(driver, "button", "Create New Job").click()
    job_name = "Automatic Test Job" + str(uuid.uuid4())[:7]
    driver.find_element_by_tag_name("input").send_keys(job_name)
    _find_element_with_contents(driver, "button", "Tests").click()

    driver.find_element_by_id(driver.find_element_by_xpath("//label[text() = 'Fast Run']").get_attribute("for")).click()

    driver.find_element_by_xpath("//header/ul/li/button[text() = 'Reports']").click()
    _find_element_with_contents(driver, "button", "Schedule").click()
    _find_element_with_contents(driver, "button", "Save").click()

    _check_for_error_popup(driver)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[text() = 'Jobs']"))
        )
    except TimeoutException:
        assert False, "Jobs page did not open, job creation might have failed"

    return job_name


def step_8(driver: webdriver.Firefox, job_name):
    _find_element_with_contents(driver, "button", "Status").click()
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//td[text() = '{job_name}']"))
        )
    except TimeoutException:
        assert False, "Job not found in queue!"


def step_9(driver: webdriver.Firefox, job_name):
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, f"//div[text()[contains(., '{job_name}')]]"))
        )
    except TimeoutException:
        assert False, "Job didn't get picked up by a worker in 60s, something must be wrong!"


def step_10(driver: webdriver.Firefox, job_name):
    try:
        WebDriverWait(driver, 1800).until(
            EC.invisibility_of_element((By.XPATH, f"//div[text()[contains(., '{job_name}')]]"))
        )
    except TimeoutException:
        assert False, "Job didn't finish in 30 minutes, it appears to be stuck!"

    assert len(driver.find_elements_by_xpath(f"//td[text() = '{job_name}']")) == 0, "Job did not disappear from the queue after completion!"


def step_11(driver: webdriver.Firefox, job_name):
    time.sleep(10)
    _find_element_with_contents(driver, "button", "Reports").click()
    try:
        WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.XPATH, f"//td[text() = '{job_name}']"))
        )
    except TimeoutException:
        assert False, "Report for job did not generate in 5 minutes, report generation appears to be broken!"


def step_12(driver: webdriver.Firefox):
    download_buttons = driver.find_elements_by_xpath("//tr/td/div/button")
    download_buttons[0].click()

    dropdown_buttons = driver.find_elements_by_xpath("//tr/td/div/ul/li")
    dropdown_buttons[0].click()

    time.sleep(2)
    _check_for_error_popup(driver)
