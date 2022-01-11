from selenium import webdriver
from urllib.parse import urlparse
from framework.element_locator import ElementLocator
from framework.element import Element


name = "Ensures that elements behaving like links on click have 'role=link' attribute set"

locator_required_elements = ["button"]

framework_version = 2
WCAG = "4.1.2"
test_data = [
    {
        "page_info": {
            "url": "links/page_disguised_links_ok.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "links/page_disguised_links_fail.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 2
    }
]

MAX_A_CHECK_DEPTH = 40
MAX_DIV_ELEMENTS = 2


def test(webdriver_instance, activity, element_locator):
    test_object = DisguisedLinksTest(webdriver_instance, activity, element_locator)
    return test_object.test()


class DisguisedLinksTest:
    def __init__(self, webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator):
        self.webdriver_instance = webdriver_instance
        self.activity = activity
        self.activator = element_locator

    def test(self):

        self.activity.get(self.webdriver_instance)

        clickables = list(self.activator.get_activatable_elements(["button"]))

        print(f"Found {len(clickables)} clickables")

        disguised_links = list()

        elements_clicked = 0

        clickable_id = 0

        def click(clickable):
            nonlocal clickable_id
            nonlocal elements_clicked
            clickable_id += 1
            print(f"\rTrying clickable {clickable_id + 1}/{len(clickables)}", end="")

            clickable_element = clickable.get_element(self.webdriver_instance)
            if clickable.tag_name == "div":
                if len(clickable_element.find_elements_by_xpath(".//*")) > MAX_DIV_ELEMENTS:
                    return
                if len(clickable_element.find_elements_by_tag_name("a")):
                    return
                if len(clickable_element.find_elements_by_tag_name("button")) > 0:
                    return
            if clickable_element.get_attribute("role") == "link":
                # An appropriate role is present
                return
            # Check if contained in an <a> tag already
            contained_in_element = self.check_whether_contained_in(clickable_element)

            if contained_in_element == "a":
                return
            elif contained_in_element == "form":
                if clickable_element.get_attribute("type") == "submit":
                    # Submits should send us to a different page, this is allowed
                    return

            click_result = clickable.click(self.webdriver_instance)
            elements_clicked += 1
            if click_result['action'] == "NEWTAB":
                disguised_links.append({
                    "element": clickable,
                    "problem": "Element opened a new tab when clicked"
                })

            if click_result['action'] == "PAGECHANGE":
                disguised_links.append({
                    "element": clickable,
                    "problem": "Element switched page when clicked"
                })

        Element.safe_foreach(clickables, click)

        print()
        print(f"Done. Clicked {elements_clicked} elements")
        if len(disguised_links) > 0:
            return {
                "status": "FAIL",
                "message": f"Found {len(disguised_links)} disguised links",
                "elements": disguised_links
            }
        return {
            "status": "PASS",
            "message": "No disguised links found"
        }

    @staticmethod
    def check_whether_contained_in(element, stop_elements=None):
        if stop_elements is None:
            stop_elements = ["a", "form"]
        check_depth = 1
        current_element = element.find_element_by_xpath("..")
        while current_element.tag_name != "html":
            if current_element.tag_name in stop_elements:
                return current_element.tag_name
            if check_depth >= MAX_A_CHECK_DEPTH:
                return None
            current_element = current_element.find_element_by_xpath("..")
            check_depth += 1
        return None

    @staticmethod
    def is_same_page(url1, url2):
        url1 = urlparse(url1)
        url2 = urlparse(url2)
        return url1.scheme == url2.scheme and url1.netloc == url2.netloc and url1.path == url2.path
