import os
from . import common
from framework.element_locator import ElementLocator


name = "Fake successful test"

locator_required_elements = ["a"]


def test(webdriver_instance, activity, element_locator: ElementLocator):
    print(f"Hello from a successful fake test!")
    print(f"CWD:{os.getcwd()}")
    common.common_func()
    print(list(element_locator.get_activatable_elements()))
    return {
        "status": "PASS",
        "message": "Everything is fine!"
    }
