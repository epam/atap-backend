import os
import traceback
from io import BytesIO
from math import floor
from time import sleep
from typing import List, Union, Optional, Tuple

from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

from framework.activity import Activity
from framework.await_page_load import wait_for_page_load
from framework.element import Element, ElementLostException
from framework.libs.element_rect import WebElementRect
from framework.screenshot.draw import Draw

THRESHOLD_PERCENTAGE = 0.01


class Screenshot:
    """
    Class with methods for working with screenshot on page.
    """

    def __init__(self, driver: webdriver.Firefox, elements: Union[List[Element], Element]):
        self.driver = driver
        if isinstance(elements, Element):
            self.element = elements
        else:
            self.elements = elements
        self.parent_element_detection = True

    def get_images(self, report_progress_callback=None, activity: Optional[Activity] = None) -> list:
        """
        A method of obtaining a list with images of transferred elements
        indicating the boundaries of each element in the image.
        ! Change in zooming technique: [level], typeof int -> zoom, typeof {str, int}
        Reason: ActionChains don't work with +- (within Checker)
        Example for interaction_sequence now: {..., "action": "zoom", "zoom_percent": 200,...}'

        """
        if activity is not None:
            activity.get(self.driver)
            wait_for_page_load(self.driver)

        self._scroll_to_top_left_of_the_page()
        images = []
        zoom_params = None
        for element_id, element in enumerate(self.elements):
            print(f"Taking screenshot for {element['element'].source[:100]} on {self.driver.current_url}")
            try:
                self.__reset_scroll_manually()
                if report_progress_callback is not None:
                    report_progress_callback(element_id, len(self.elements))

                if 'interaction_sequence' in element:
                    interaction_sequence = element['interaction_sequence']
                    try:
                        for interaction_object in interaction_sequence:
                            interaction_element = interaction_object['element']
                            if interaction_object['action'] == 'click':
                                interaction_element.click()
                            elif interaction_object['action'] == 'focus':
                                def focus(element):
                                    ActionChains(self.driver).move_to_element(element).perform()
                                interaction_element.safe_operation_wrapper(focus)
                            elif interaction_object['action'] == 'input':
                                def type(element):
                                    element.send_keys(interaction_object['text'])
                                interaction_element.safe_operation_wrapper(type)
                            elif interaction_object['action'] == 'zoom':
                                window_rect = self.driver.execute_script("return window.screen.valueOf();")
                                client_width, client_height = window_rect['width'], window_rect['height']
                                zoom = interaction_object['zoom_percent']
                                try:
                                    zoom = int(zoom)
                                    assert 25 <= zoom <= 500
                                    width, height = client_width, client_height
                                    width, height = map(lambda size: size / zoom * 100, (width, height))
                                    zoom_params = {'width': width, 'height': height}
                                    self.driver.set_window_rect(**zoom_params)
                                except (ValueError, AssertionError) as e:
                                    print(f"""ValueError {e} while performing interactions before taking screenshot for {element['element'].source[:100]}:
                                            \nPassed invalid value for zoom parameter, only string or integer between 25 and 500 expected""")

                    except ElementLostException:
                        print(f"Lost element while performing interactions before taking screenshot for {element['element'].source[:100]}")
                    except KeyError as e:
                        # A mistake on test developer's part, catching to not let 1 test break all screenshots
                        print(f"KeyError {e} while performing interactions before taking screenshot for {element['element'].source[:100]}")
                shown_element = self._show_element(element['element'].get_element(self.driver))
                if element['element'].get_element(self.driver).is_displayed():
                    # hide_cookie_popup(self.dr, activity, target_element=element['element'].get_element(self.driver))
                    single_image = self.single_element(element=element['element'], draw=True)
                else:
                    print(f"Element is not displayed after trying all methods - {element['element'].source[:100]}")
                    images.append(None)
                    continue

                if zoom_params:
                    zoom_params = self.driver.execute_script("return window.screen.valueOf();")
                    zoom_params = {key: value for key, value in zoom_params.items() if key in ['width', 'height']}
                    self.driver.set_window_rect(**zoom_params)
                if ('interaction_sequence' in element or shown_element) and activity is not None:
                    # Element interaction could have broken webdriver state
                    activity.get(self.driver)
                    wait_for_page_load(self.driver)

                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('0').key_up(Keys.CONTROL).perform()
                    self._scroll_to_top_left_of_the_page()

                if single_image is None:
                    images.append(None)
                    print(f"Element without coordinates or not visible - {element['element'].source[:100]}...")
                else:
                    # resize_image = self.__resize_image(single_image, one_size=one_size)
                    # if resize_image is not None:
                    #     images.append(resize_image)
                    images.append(single_image)
            except Exception:
                images.append(None)
                print(
                    f"Exception while taking a screenshot for {element['element'].source[:100]}:\n"
                    f"{traceback.format_exc()}")

        return images

    def _show_element(self, element: WebElement) -> bool:
        if element.is_displayed():
            print("Element is already displayed!")
            return False
        cur_element = element
        print(cur_element.get_attribute('outerHTML'))
        # print(cur_element.is_displayed())
        # print(cur_element == self.driver)

        element_sequence = list()

        # Sometimes weirdly constructed web pages break parent element detection, getting the code stuck in a loop
        MAX_DEPTH = 100
        iteration = 0
        while self.parent_element_detection:
            iteration += 1
            element_sequence.append(cur_element)
            if not cur_element.is_displayed():
                # src = cur_element.get_attribute('outerHTML')
                # src = src if len(src) < 100 else src[:100]
                # print(f"Making {src} visible")
                self.driver.execute_script("arguments[0].style.setProperty('display', 'block', 'important');",
                                           cur_element)
                self.driver.execute_script("arguments[0].style.setProperty('opacity', '100', 'important');",
                                           cur_element)
                self.driver.execute_script("arguments[0].style.setProperty('left', '0px');", cur_element)
                self.driver.execute_script("arguments[0].style.setProperty('top', '0px');", cur_element)
                self.driver.execute_script("arguments[0].removeAttribute('hidden');", cur_element)
                # print(cur_element.is_displayed())
                cur_element = cur_element.find_element_by_xpath("..")

            if cur_element.tag_name in ["html", "body"] or cur_element == self.driver:
                # print("Reached the root element, stopping")
                break

            if iteration > MAX_DEPTH:
                print("Parent element detection doesn't work on this page, not trying to make element chain visible")
                self.parent_element_detection = False
                break

        if not element.is_displayed():
            # print("Element is not displayed, forcing sizes of parent elements")

            for cur_element in reversed(element_sequence):
                # src = cur_element.get_attribute('outerHTML')
                # src = src if len(src) < 200 else src[:200]
                # print(f"Forcing size of {src}")
                self.driver.execute_script("arguments[0].style.height = '2000px';", cur_element)
                self.driver.execute_script("arguments[0].style.width = '2000px';", cur_element)
                if element.is_displayed():
                    # print("That did it! Element is now displayed")
                    break

        return True

    def _js_coords(self, element: WebElement, iteration=0):
        """
        Returns the coordinate element via JavaScript.
        """
        if iteration > 100:
            print("Parent element detection broken, giving up")
            return None, None
        c = self.driver.execute_script(
            "return arguments[0].getBoundingClientRect();", element
        )  # list with client rects
        # A shorter form for checking that the dictionary is not empty
        print(f"Got dict {c}")
        if c is None:
            return None, None
        x, y, w, h = c["x"], c["y"], c["width"], c["height"]

        if w * h > 0 and element.is_displayed():
            return [x, y, x + w, y + h], None
        elif w == 0 or h == 0:
            print("Returning js coords of parent")
            try:
                parent_element = element.find_element_by_xpath("./parent::*")
                return self._js_coords(parent_element, iteration + 1)[0], c
            except NoSuchElementException:
                print(f"Cannot get parent of element {element.tag_name}")
                raise
        else:
            return None, None

    def single_element(self, element: Element = None, draw: bool = False) -> Image:
        """
        Returns the cropped image of the element.
        Scrolling and getting coordinates through JavaScript is used.

        Parameters:
            element (Element)
            draw (bool): Draws an arrow with correction for free space near element if True.
        Returns:
            Image: Cropped element image.
        """
        if element is None:
            element = self.element
        el = element.get_element(self.driver)

        # scroll to element
        # self.dr.execute_script("arguments[0].scrollIntoView();", el)

        self.__scroll_to_element(el)

        actual_coords, rect = self.__get_actual_coords(el)
        image = Image.open(BytesIO(self.driver.get_screenshot_as_png())).convert("RGBA")

        if draw and rect is not None:
            image = Draw([rect['x'], rect['y'], rect['width'] + rect['x'], rect['height'] + rect['y']], image).draw()
        elif draw:
            image = Draw(actual_coords, image).draw()
        return self.__crop_image(image, actual_coords)

    def __reset_scroll_manually(self) -> None:
        body = self.driver.find_element_by_tag_name("body")
        iterations = 0
        try:
            while self.__get_actual_coords(body)[0][1] < -1:
                iterations += 1
                if iterations > 30:
                    print("Failed to reset page scroll, coordinates never reset. not resetting scroll")
                    return
                body.send_keys(Keys.PAGE_UP)
        except NoSuchElementException:
            print("Body element does not return a size, not resetting scroll")

    def __scroll_to_element(self, element: WebElement) -> None:
        self._scroll_to_top_left_of_the_page()
        sleep(0.5)
        original_position = self.__get_actual_coords(element)[0][1]  # TODO: fix error when method returns None

        position = element.location['y'] - 0.5 * self.driver.get_window_size()['height']
        print(f"Scrolling to {position}")
        self.driver.execute_script(f"window.scrollTo(0, {position})")
        sleep(0.5)
        actual_coords, rect = self.__get_actual_coords(element)  # TODO: fix error when method returns None

        # get coordinates from client rect
        if original_position + 1 > actual_coords[1] > original_position - 1:
            print("Element did not move, resetting scroll")
            self._scroll_to_top_left_of_the_page()
            sleep(1)
            print(actual_coords[1])

            cur_element = element
            iterations = 100
            while cur_element.tag_name not in ["html", "body"] and cur_element != self.driver:
                iterations -= 1
                if iterations < 0:
                    print("Cannot scroll to element using page down, aborting")
                    break
                try:
                    cur_element.send_keys(Keys.PAGE_DOWN)
                    break
                except ElementNotInteractableException:
                    cur_element = cur_element.find_element_by_xpath("..")
            iterations = 100
            while actual_coords[3] > self.driver.get_window_size()['height']:
                if iterations < 0:
                    print("Cannot scroll to element using page down, aborting")
                    break
                cur_element.send_keys(Keys.PAGE_DOWN)
                sleep(0.5)
                actual_coords, rect = self.__get_actual_coords(element)

                iterations -= 1

    def _scroll_to_top_left_of_the_page(self) -> None:
        self.driver.execute_script("window.scrollTo(0, 0)")

    def __get_actual_coords(self, element: WebElement):
        jsc = self._js_coords(element)
        if jsc is None:
            print("Js coords is none")
            return None
        coords, rect = jsc
        if coords is None:
            print("Coords is none, using rect")
            if rect is None:
                print("Rect is also none, skipping")
                return None
            actual_coords = [rect['x'], rect['x'] + rect['width'], rect['y'], rect['y'] + rect['height']]
        else:
            actual_coords = coords

        return actual_coords, rect

    @staticmethod
    def __resize_image(image: Image, one_size=False):
        """
        Method for resizing an image

        Used resample "BILINEAR" for better picture quality.

        :scale_percent: the percentage of the image size from the original
        :param image: image after cropping
        :return: resizing image
        """

        # scale_percent = 70
        # w = int(image.size[0] * scale_percent / 100)
        # h = int(image.size[1] * scale_percent / 100)
        if image.width < 1 or image.height < 1:
            return None
        if one_size:
            need_w = 500
            new_h = image.size[1] / (image.size[0] / need_w)
            return image.resize((need_w, int(new_h)), resample=Image.BILINEAR)
        return image

    @staticmethod
    def __crop_image(image: Image, coordinates: Tuple[int, int, int, int]) -> Image:
        """
        image.size[0] - width screenshot
        image.size[1] - height screenshot

        max - used to define the lower boundary
        min - used to define the upper  boundary
        safe distance - a safe distance for crop the image
        :param coordinates: coordinates
        :return: cropped image
        """
        x, y, x1, y1 = coordinates
        # print(f"CROPPING: {coordinates} from {image.size[0]}:{image.size[1]}")
        if x > image.width or y > image.height:
            print("Element out of bounds of image!")
            return None

        height, width = y1 - y, x1 - x
        if height > width:
            if height / image.height >= THRESHOLD_PERCENTAGE:
                return image
            new_height = floor(height / THRESHOLD_PERCENTAGE)
            new_width = image.width * new_height / image.height
        else:
            if width / image.width >= THRESHOLD_PERCENTAGE:
                return image
            new_width = floor(width / THRESHOLD_PERCENTAGE)
            new_height = image.height * new_width / image.width
        k = new_height / image.height
        if x < image.width - x1:
            crop_x1 = max(x - k * x, 0)
            crop_x2 = new_width + crop_x1
        else:
            crop_x2 = image.width - (image.width - x1) * (1 - k)
            crop_x1 = crop_x2 - new_width
        if y < image.height - y1:
            crop_y1 = max(y - k * y, 0)
            crop_y2 = new_height + crop_y1
        else:
            crop_y2 = image.height - (image.height - y1) * (1 - k)
            crop_y1 = crop_y2 - new_height
        if crop_y2 <= crop_y1 or crop_x2 <= crop_x1:
            print("Element has invalid coordinates (x1>x2/y1>y2), skipping")
            return image
        print(f"CROP: {crop_x1}:{crop_y1}, {crop_x2}:{crop_y2}")
        new_image = image.crop(box=(crop_x1, crop_y1, crop_x2, crop_y2))
        return new_image

    def __get_coordinates(self, element: Element) -> Optional[List]:
        """
        :param element: WebElement
        :return: list with coordinates element
        """
        element = element.get_element(self.driver)
        if element and element.size['width'] * element.size['height'] > 0 and element.is_displayed():
            return WebElementRect(element).coords()
        return None

    def it_infinity(self) -> bool:
        total = 0
        total_h = self.driver.execute_script("return document.body.scrollHeight")
        view = self.driver.execute_script("return window.innerHeight")

        iterations = 100
        while total < total_h:
            iterations -= 1
            if iterations < 0:
                print("Cannot scroll through entire document - assuming infinite page")
                return True
            total += view
            self.driver.execute_script(f"window.scrollTo(0, {total_h})")
            total_h = self.driver.execute_script("return document.body.scrollHeight")
            if total_h > 20000:
                return True
        return False

    @staticmethod
    def full_page(driver: webdriver.Firefox) -> Image:
        """
        Getting a picture with a screenshot of the entire page.
        """
        driver.execute_script(f"window.scrollTo({0}, {0})")
        total_width = driver.execute_script("return document.body.offsetWidth")
        total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
        viewport_width = driver.execute_script("return document.body.clientWidth")
        viewport_height = driver.execute_script("return window.innerHeight")
        rectangles = []
        i = 0
        if viewport_height <= 0 or viewport_width <= 0:
            raise Exception("Viewport area is zero, cannot screenshot!")
        while i < total_height:
            ii = 0
            top_height = i + viewport_height
            if top_height > total_height:
                top_height = total_height
            while ii < total_width:
                top_width = ii + viewport_width
                if top_width > total_width:
                    top_width = total_width
                rectangles.append((ii, i, top_width, top_height))
                ii = ii + viewport_width
            i = i + viewport_height
        stitched_image = Image.new('RGB', (total_width, total_height))
        previous = None
        counter = 0
        for rectangle in rectangles:
            if previous is not None:
                driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
            file_name = f"part_{counter}.png"
            counter += 1
            driver.get_screenshot_as_file(file_name)
            screenshot = Image.open(file_name)
            if rectangle[1] + viewport_height > total_height:
                offset = (rectangle[0], total_height - viewport_height)
            else:
                offset = (rectangle[0], rectangle[1])
            stitched_image.paste(screenshot, offset)
            del screenshot
            os.remove(file_name)
            previous = rectangle
        return stitched_image
