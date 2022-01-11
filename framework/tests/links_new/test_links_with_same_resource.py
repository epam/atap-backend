import itertools
from math import inf
from typing import List
from logging import getLogger

logger = getLogger("test_links_with_same_resource")

from selenium import webdriver
from urllib.parse import urlparse

from framework.element_locator import ElementLocator
from framework.element import Element
from framework.tests.links_new.lib import is_visible
from framework.libs.distance_between_elements import distance, contains


framework_version = 5

webdriver_restart_required = False
locator_required_elements = ["a"]
# !!!!! BP !!!!!!!!!
WCAG = "2.4.4"
name = "Ensures that links to the same resource that are located next to each other will be merged into one."
elements_type = "link"
test_data = [
    {
        "page_info": {"url": "links_new/same_resource/page_bug.html"},
        "expected_status": "FAIL",
        "expected_additional_content_length": {"elements": 1},
    },
    {"page_info": {"url": "links_new/same_resource/page_good.html"}, "expected_status": "PASS"},
    {"page_info": {"url": "links_new/same_resource/page_good_2.html"}, "expected_status": "PASS"},
]

EPSILON = 50


def _get_ancestors_of(driver, element, edge=0):
    """

    Args:
        element (Element)
        edge (int, optional): Slice index for ancestors. First ancestor is <html>. Defaults to 0.

    Returns:
        list: Sliced ancestors list of the element
    """
    ancestors = element.find_by_xpath("ancestor::*", driver)
    if -edge >= len(ancestors) - 1:  # exclude html and body
        edge = -(len(ancestors) - 2)

    return ancestors[edge:]


def _get_least_common_ancestor(driver, element_ancestors, other_element_ancestors):
    common_ancestors = [
        *sorted(
            set(element_ancestors) & set(other_element_ancestors),
            key=lambda anc: anc.get_element(driver).size["width"] * anc.get_element(driver).size["height"],
        )
    ]

    return common_ancestors and common_ancestors[0]


def _one_after_another_inside(driver, elem, other, ancestor):
    if not ancestor:
        return False

    def _is_sensible_child(element):
        return driver.execute_script(
            "return arguments[0].innerText.length || ['IMG', 'svg'].includes(arguments[0].tagName);",
            element.get_element(driver),
        )

    ancestor_ones_with_image_or_text = [
        child for child in ancestor.find_by_xpath("child::*", driver) if _is_sensible_child(child)
    ]

    try:
        # elem follows other, otherwise; they are images or contain text
        return (
            abs(ancestor_ones_with_image_or_text.index(elem) - ancestor_ones_with_image_or_text.index(other)) == 1
        )
    except ValueError:
        return False


def located_next_to(driver: webdriver.Firefox, element_1: Element, element_2: Element):
    """
    Checks that elements are close to each other visually or in the house(have a common ancestor)
    """

    least_common_ancestor = _get_least_common_ancestor(
        driver, _get_ancestors_of(driver, element_1, edge=-4), _get_ancestors_of(driver, element_2, edge=-4)
    )

    return distance(driver, element_1, element_2) < EPSILON or _one_after_another_inside(
        driver, element_1, element_2, least_common_ancestor
    )


def get_href(driver: webdriver.Firefox, link: Element) -> str:
    parsed_href = urlparse(link.get_attribute(driver, "href"))
    return f'{parsed_href.netloc}{parsed_href.path}{"#" + parsed_href.fragment if parsed_href.fragment else ""}'


def link_is_visible(driver: webdriver.Firefox, link: Element):
    return is_visible(link, driver) or any(is_visible(d, driver) for d in link.find_by_xpath("child::*", driver))


def check_visible(driver: webdriver.Firefox, link: Element):
    if not link_is_visible(driver, link):
        driver.execute_script(
            f"window.scrollTo(0, {link.get_element(driver).location['y'] - 0.5 * driver.get_window_size()['height']})"
        )
    return link_is_visible(driver, link)


def link_in_carousel(driver: webdriver.Firefox, link: Element):
    depth = 7
    return any(
        any(word in ancestor.source.lower() for word in ["carousel", "slider", "accordion"])
        for ancestor in _get_ancestors_of(driver, link)[:-depth:-1]
    )


def create_groups(driver: webdriver.Firefox, links: List[Element]):
    new_groups = []

    for link in links:
        if not link_in_carousel(driver, link) and not check_visible(driver, link):
            continue
        for new_group in new_groups:
            if any(located_next_to(driver, link, other) for other in new_group):
                new_group.append(link)
                break
        else:
            new_groups.append([link])

    return new_groups


def get_images(driver: webdriver.Firefox, element: Element):
    return element.safe_operation_wrapper(
        lambda e: e.find_by_xpath("descendant::*[self::img or self::svg]", driver), on_lost=lambda: []
    )


def search_intersection_image(driver: webdriver.Firefox, links: List[Element]):
    depth = 4
    for ancestor in _get_ancestors_of(driver, links[0])[:-depth:-1]:
        if ancestor in ["html", "body"]:
            continue
        images = get_images(driver, ancestor)
        if images:
            break
    else:
        return False
    return any(all(contains(driver, image, link) for link in links) for image in images)


def _sort_result_links(driver, links):
    links.sort(
        key=lambda l: (
            l["element"].safe_operation_wrapper(
                lambda e: e.get_element(driver).location["y"], on_lost=lambda: inf
            ),
            l["element"].safe_operation_wrapper(
                lambda e: e.get_element(driver).location["x"], on_lost=lambda: inf
            ),
        )
    )

    return links


def _get_img_links(driver, links):
    return [
        *sorted(
            [el for el in links if get_images(driver, el)],
            key=lambda e: e.get_element(driver).size["width"] * e.get_element(driver).size["height"],
            reverse=True,
        )
    ]


def _link_issue(data, resource):
    return {
        "element": data[0],
        "problem": f"This link is located next to another link that leads to the same "
        f"resource. Resource: {resource}",
        "severity": "FAIL",
    }


def _get_link_issue(driver, image_links, links, group):
    issue = None

    if image_links:
        issue = _link_issue(image_links, group)
    else:
        links = [i for i in links if i.get_text(driver).strip() and link_is_visible(driver, i)]
        if len(links) > 1 and search_intersection_image(driver, links):
            issue = _link_issue(links, group)

    return issue


def check_group_of_links(driver: webdriver.Firefox, grouped_links: itertools.groupby):
    incorrect_links = []
    for i, (group, items) in enumerate(grouped_links):
        logger.info(f"\rAnalyzing group of links {i + 1}", end="", flush=True)
        links = list(items)

        if not group or group == "/" or len(links) < 2:
            continue

        for links in create_groups(driver, links):
            if len(links) < 2 or len(links) == _get_img_links(driver, links):
                continue

            img_links = [img for img in _get_img_links(driver, links) if "logo" not in img.source]
            link_issue_to_report = _get_link_issue(driver, img_links, links, group)
            if link_issue_to_report:
                incorrect_links.append(link_issue_to_report)

    return _sort_result_links(driver, incorrect_links)


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    links = element_locator.get_all_by_xpath(webdriver_instance, "//a[@href]")
    result = {
        "status": "PASS",
        "message": "No links were found that lead to the same resource and are located next to each other.",
        "elements": [],
        "checked_elements": links,
    }
    if not links:
        result["status"] = "NOELEMENTS"
        result["message"] = "There are no links for testing."
        return result

    links.sort(key=lambda l: get_href(webdriver_instance, l))
    incorrect_links = check_group_of_links(
        webdriver_instance, itertools.groupby(links, lambda l: get_href(webdriver_instance, l))
    )

    if incorrect_links:
        result["status"] = "FAIL"
        result["message"] = (
            "Links were found that lead to the same resource and are located next to each other, but "
            "not combined into a single link."
        )
        result["elements"] = incorrect_links
    logger.info(f"Test result\n{result}")

    return result
