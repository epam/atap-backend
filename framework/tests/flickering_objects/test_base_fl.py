import tempfile
import urllib.request
from typing import List

from PIL import Image
from selenium import webdriver
from urllib3.exceptions import HTTPError

from framework.activity import Activity
from framework.element import Element
from framework.element_locator import ElementLocator
from framework.await_page_load import *

locator_required_elements = []
framework_version = 2
depends = []
webdriver_restart_required = False
test_data = [
    {
        "page_info": {
            "url": "flicker/page_good_flickering_gifs.html"
        },
        "expected_status": "PASS",
        "expected_additional_content_length": {
            "gifs": 2
        }
    }
]


def get_gifs(dr: webdriver, elements: List[Element], name_folder: str):
    gifs = list()
    for element in elements:
        src = element.get_attribute(dr, "src")
        if src is not None and element.tag_name == "img" and src.endswith(".gif"):
            if not src.startswith("http"):
                if not dr.current_url.endswith(r"/"):
                    src = dr.current_url + "/" + src
                else:
                    src = dr.current_url + src
                # if not src.startswith("file"):
                #     src = dr.current_url[:-10:] + src[2::]
            path = save_gif(name_folder, src)
            if not path:
                continue

            gifs.append({
                "gif": element,
                "path": path
            })
    return gifs


def save_gif(name_folder: str, src) -> str:
    """
    Save a gif to the folder

    return path where the gif is stored
    return "" if saving is failed

    """
    assert src.startswith("http")
    assert src.endswith(".gif")
    path = f"{name_folder}/{GifNameGenerator.get_gif_name()}"
    try:
        urllib.request.urlretrieve(src, path)
    except HTTPError:
        print("An image can't be uploaded.")
        return ""
    try:
        if Image.open(path).info["duration"] == 0:
            return ""
    except OSError:
        """Case: "cannot identify image file" """
        return ""
    return path


class GifNameGenerator:
    count = 0

    @classmethod
    def get_gif_name(cls):
        cls.count += 1
        return "pic_{}.gif".format(cls.count)


def get_css_gifs(dr: webdriver, elements: List[Element], name_folder: str):
    css_gifs = list()
    for element in elements:
        selenium_el = element.get_element(dr)
        property_ = selenium_el.value_of_css_property("background-image")
        if not property_ or len(property_) < 10:
            continue
        src = property_[5:-2:]  # url("SRC")

        if element.tag_name != "img" and src.endswith(".gif"):
            if not src.startswith("http"):
                if not dr.current_url.endswith(r"/"):
                    src = dr.current_url + "/" + src
                else:
                    src = dr.current_url + src
                # if not src.startswith("file"):
                #     src = dr.current_url[:-10:] + src[2::]
            path = save_gif(name_folder, src)
            if not path:
                continue

            css_gifs.append({
                "gif": element,
                "path": path
            })
    return css_gifs


def test(webdriver_instance: webdriver.Chrome, activity: Activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    wait_for_page_load(webdriver_instance)
    path_folder = tempfile.TemporaryDirectory(prefix="images_")
    gifs = get_gifs(webdriver_instance,
                    element_locator.get_all_by_xpath(webdriver_instance, "//img"),
                    path_folder.name)
    css_gifs = get_css_gifs(webdriver_instance,
                        element_locator.get_all_by_xpath(webdriver_instance, "//*"),
                        path_folder.name)
    if not gifs and not css_gifs:
        return dict(status="NOELEMENTS", message="No elements on page", folder=path_folder)
    return dict(status="PASS", gifs=gifs + css_gifs, folder=path_folder)
