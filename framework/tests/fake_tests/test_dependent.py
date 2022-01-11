from framework.element_locator import ElementLocator


name = "Fake successful dependent test"
depends = ["test_dependency"]


def test(webdriver_instance, activity, element_locator: ElementLocator, dependencies):
    number = dependencies["test_dependency"]["number"]
    return {
        "status": "WARN",
        "message": f"Received number {number}",
        "elements": [
            {
                "source": "html > body",
                "problem": "bad body"
            }
        ]
    }
