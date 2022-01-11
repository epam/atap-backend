import tempfile

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.libs.download_image import save_screen
from framework.tests.contrast.test_contrast import add_contours, create_groups_of_pixels, error_fragmentation


name = '''Ensures that contrast ratio for adjacent elements doesn't violate requirements (for pictures)'''
WCAG = '1.4.11'
framework_version = 5
webdriver_restart_required = False

elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "images/contrast/page_good.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "images/contrast/page_bugs.html"
        },
        "expected_status": "FAIL",
        "expected_additional_content_length": {
            "elements": 2
        }
    }
]

TAGS = ['img', 'video', 'i', 'svg']


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    return PicturesContrast(webdriver_instance, element_locator).result()


class PicturesContrast:
    def __init__(self, driver: webdriver, locator: ElementLocator):
        self._dr = driver
        self._loc = locator

    def _wrap(self, el):
        return ElementWrapper(el, self._dr)

    def result(self):
        result = {
            "status": "PASS",
            "message": "",
            "elements": [],
            "checked_elements": [],
            "labels": []
        }
        checked_elements, elements = self.search_pictures()
        if not checked_elements:
            result["status"] = "NOELEMENTS"
            result["message"] = "This page no problem with contrast"
        elif elements:
            result["status"] = "FAIL"
            result["elements"] = elements
            result["message"] = "Page has problems with contrast"
        result["checked_elements"] = checked_elements
        print(result)
        return result

    def get_computed_style(self, pseudo: str, element: WebElement) -> str:
        return self._dr.execute_script(
            f"return window.getComputedStyle(arguments[0], ':{pseudo}').getPropertyValue('content');",
            element
        )

    def search_pictures(self):
        bad_elements = []
        images = self._loc.get_all_of_type(self._dr, element_types=TAGS)
        images.extend([
            elem for elem in self._loc.get_all_by_xpath(self._dr, '//body//*')
            if (self.get_computed_style('before', elem.get_element(self._dr)) != 'none'
                or elem.get_element(self._dr).value_of_css_property('background-image') != 'none')
        ])
        count_img = len(images)
        for img_id, img in enumerate(images):
            image = self._wrap(img)
            attributes = image.framework_element.get_attributes(self._dr)
            if self.skip_images(image, attributes):
                continue

            screen = self.get_screen(image)
            if screen is None:
                continue

            print(f"Check for contrast {img_id + 1} image out of {count_img}")
            screen_with_contours = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            add_contours(screen.name, screen_with_contours.name)
            # resize_image(screen.name, 0.9)
            problems = create_groups_of_pixels(screen_with_contours.name)
            problem_files = error_fragmentation(screen.name, problems)
            screen_with_contours.close()
            screen.close()
            for colors, filename in problem_files.items():
                bad_elements.append({
                    "element": image.framework_element,
                    "problem": f"Bad contrast: colors={colors}",
                    "severity":
                        "WARN" if image.element.tag_name == 'img' or image.element.tag_name not in TAGS else "FAIL",
                    "screenshot": filename
                })
        return images, bad_elements

    def get_screen(self, image: ElementWrapper):
        try:
            return save_screen(image.framework_element, self._dr, safe_area=20)
        except SystemError:
            return None

    def skip_images(self, image, attributes):
        """
        Check that the image is decorative
        """
        def identify_logo():
            for element in [image.framework_element, image.framework_element.get_parent(self._dr),
                            image.framework_element.get_parent(self._dr).get_parent(self._dr)]:
                if element.source.find('logo') != -1 and len(
                        element.find_by_xpath(f"descendant::*[self::{' or self::'.join(TAGS)}]", self._dr)) <= 1:
                    return True
            return False
        return not image.is_visible or ('alt' in attributes and not attributes['alt']) or identify_logo()
