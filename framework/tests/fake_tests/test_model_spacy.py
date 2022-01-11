from framework.element_locator import ElementLocator


name = "Fake successful test"

depends = ["spacy_en_lg"]
locator_required_elements = []


def do_test(model, str_in):
    print(str_in)

    str_out = model(str_in)
    print(str_out)
    return str_out


def test(webdriver_instance, activity, element_locator: ElementLocator, dependencies):
    str_in = "Russia is home to Yandex one of the biggest IT companies in the world"


    str_out = dependencies["spacy_en_lg"].run(do_test, str_in)
    return {
        "status": "WARN",
        "message": str(str_out)
    }
