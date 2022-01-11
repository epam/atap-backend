from selenium import webdriver
from selenium.common.exceptions import MoveTargetOutOfBoundsException, StaleElementReferenceException, \
    NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

from framework.activity import Activity
from framework.element import Element, ElementLostException
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper


framework_version = 0
name = "Ensures that For functionality that can be operated using a single pointer," \
       " at least one of the 4 points set by the WCAG is true"
WCAG = "2.5.2"

elements_type = "list"
test_data = [
    {
        "page_info": {
            "url": "pointers/page_good_pointer.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "pointers/page_bugs_pointer.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 3
    }
]


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator):
    """
     The main method that determines the behavior of the entire test.

    General test behavior:
        1. We click on each element and create a list with buttons, but discards all non-interactable buttons.
        2. We go through all the elements and create a dictionary with the coordinates of each.
        3. Next, we check all the buttons with a long press and move, and see if they worked.

        warnings also::
            * If the button has an onClick method that plays audio when clicked, the test will not see this.
    """
    bad_elements = []
    activity.get(webdriver_instance)
    return Pointer(webdriver_instance, activity, element_locator).result()


class Pointer:

    def __init__(self, driver: webdriver.Firefox, activity, locator):
        self._dr = driver
        self._ac = activity
        self._loc = locator
        self._w = WebDriverWait(self._dr, 10)

    def _wrap(self, element):
        return ElementWrapper(element, self._dr)

    def result(self):
        result = {
            "status": "PASS",
            "message": "",
            "elements": [],
            "checked_elements": [],
            "labels": []
        }

        buttons, checked = self._main()
        if buttons is None:
            result["status"] = "NOELEMENTS"
            result["message"] = "This page don't have buttons"
        elif buttons:
            result["status"] = "FAIL"
            result["elements"] = buttons
            result["message"] = "Page has problems with buttons"
        else:
            result["message"] = "All found buttons, work well."
        return result

    def get_elements(self):
        types = {"input", "div", "button", "a"}
        return self._loc.get_activatable_elements(element_types=types)

    def _main(self):
        bad_elements = []
        patient_zero = self._elements_coordinates()
        activatable_elements = self.get_elements()
        if not activatable_elements:
            return None, []
        print("Small preparations before starting")
        element_clicks = self.result_clicks(activatable_elements)

        print("Start testing")
        for el in element_clicks:
            changed = self.check_hold(el, patient_zero)
            self._ac.get(self._dr)
            if not changed:
                print("Found troubles element")
                bad_elements.append({
                    "element": el,
                    "problem": "Incorrect button click processing"
                })
        print("End testing")
        return bad_elements, activatable_elements

    def _elements_coordinates(self):
        """
        Dict with element and his coordinates
        """
        print("Search for elements and their coordinates")
        coords = self._dr.execute_script("""
            var elements_coords = [];
            var elements = Array.from(document.body.getElementsByTagName('*'));

            function get_coords(els){
                els.forEach(function(el) {
                    var coord = el.getClientRects()[0];
                    if (coord != undefined && coord['width'] * coord['height'] > 0){
                        console.log(el);
                        elements_coords.push({
                            'element': el,
                            'coords':  [coord['x'], coord['y'], coord['width'], coord['height']]
                        });
                    };
                });
            };

            get_coords(elements);
            return elements_coords;

        """)
        print("Search over, prepare list")
        if not coords:
            return []
        dict_coords = {}
        for e in coords:
            dict_coords[e["element"]] = e["coords"]
        print("Prepare complete")
        return dict_coords

    def check_hold(self, element: Element, scan: dict):
        """
        Checks the correct operation of the button
        """
        coords = self._wrap(element).coords
        distance = coords[0] + 50, coords[1] + 50
        print(distance)
        before_url = self._dr.current_url
        print("Check button with hold")

        try:
            print("Try hold")
            # FIXME: Freeze browser (geckodriver) after click links
            ActionChains(self._dr).drag_and_drop_by_offset(element.get_element(self._dr),
                                                           distance[0], distance[1]).perform()
        except (MoveTargetOutOfBoundsException, ElementLostException,
                NoSuchElementException, StaleElementReferenceException):
            return []
        if before_url != self._dr.current_url:
            return []
        print("Hold ok")
        scan_hold = self._elements_coordinates()
        return sorted(scan.values()) == sorted(scan_hold.values())

    def result_clicks(self, locator):
        """
        Discards all non-interactable buttons
        """
        elements = [el for el in locator]
        clicks = []
        for el in elements:
            if el.click(self._dr)["action"] not in {"NONE", "NONINTERACTABLE"}:
                clicks.append(el)
        return clicks









