import random
from framework.element_locator import ElementLocator
import time

name = "Fake successful dependency test"


def test(webdriver_instance, activity, element_locator: ElementLocator):
    number = random.randint(1, 100)
    print(f"Dependee thought of the number {number}")
    time.sleep(10)
    print(f"Dependee finished")
    return {
        "status": "NOELEMENTS",
        "message": f"Thought of number {number}!",
        "number": number
    }
