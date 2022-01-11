from common_steps import step_1, step_2, step_3, step_4, step_5, step_6, step_7, step_8, step_9, step_10, step_11, step_12
import os

from selenium import webdriver

if __name__ == "__main__":
    print("Beginning workflow test, starting webdriver...")
    driver = webdriver.Firefox()
    SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", default="http://localhost")
    SERVER_LOGIN = os.environ.get("SERVER_LOGIN", default="admin")
    SERVER_PASSWORD = os.environ.get("SERVER_PASSWORD", default="admin")

    try:
        print("Running workflow test in accordance with https://jira.epam.com/jira/browse/EPMACCHK-666")
        print("[STEP 1/12] Connect to the server, verify that the login page opens and there is no connection error to the frontend")
        login_field, password_field, login_button = step_1(driver, SERVER_ADDRESS)
        print("[STEP 2/12] Enter login and password, verify that they are accepted and there is no connection error to the backend")
        step_2(driver, login_field, password_field, login_button, SERVER_LOGIN, SERVER_PASSWORD)
        print("[STEP 3/12] Click 'Create New Project', verify that all expected data fields are present and fill them")
        project_name = step_3(driver)
        print("[STEP 4/12] Click 'Save', verify that the url check succeeds and that the save button is greyed out")
        step_4(driver)
        print("[STEP 5/12] Click 'Go to Sitemap', click 'Create Pages Automatically', click 'Create'. Verify that 'Sitemap generation is in progress' is displayed on the screen.")
        step_5(driver)
        print("[STEP 6/12] Wait for 'Sitemap generation is in progress' to disappear. Verify that at least one page appears in the list.")
        step_6(driver)
        print("[STEP 7/12] Select the first page and click 'Create New Job'. Give it a random name. Click on the 'Tests' tab. Select 'Fast Run'. Click on the 'Reports' tab and then on the 'Schedule' tab. Click 'Save'. Verify that there is no error.")
        job_name = step_7(driver)
        print("[STEP 8/12] Click on the 'Status' tab. Verify that the task is in the queue.")
        step_8(driver, job_name)
        print("[STEP 9/12] Verify that the task gets started.")
        step_9(driver, job_name)
        print("[STEP 10/12] Wait for the task to finish. Verify that it disappears from the queue.")
        step_10(driver, job_name)
        print("[STEP 11/12] Click on the 'Reports' tab. Verify that a report got created.")
        step_11(driver, job_name)
        print("[STEP 12/12] Click on the download icon. Click on 'Download Audit.docx'. Verify that a file begins downloading")
        step_12(driver)

        print("Workflow test succeeded!")
    finally:
        print("Closing webdriver...")
        driver.quit()
