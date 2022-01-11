from selenium.common.exceptions import InvalidSelectorException
import requests
from bs4 import BeautifulSoup
import framework.libs.clean as clean


stop_list = [
    "full story",
    "full",
    "read more about",
    "read more",
    "learn more",
    "click here",
    "see all",
    "show more",
    "show all",
    "read all",
    "see more",
    "more",
    "all",
    "here",
]


def get_children(driver, elem):
    return elem.find_by_xpath("./child::*", driver)


def get_longdesc(driver, image):
    data = None
    longdesc = driver.execute_script("return arguments[0].longDesc;", image.get_element(driver))
    if longdesc == "":
        return longdesc

    try:
        data = requests.get(longdesc)
    except (
        requests.exceptions.MissingSchema,
        requests.exceptions.InvalidURL,
        requests.exceptions.InvalidSchema,
    ) as exc:
        print("\nrequests exception of longdesc", exc)
        return ""

    text = data.text
    if longdesc.find("#") != -1:
        id_word = longdesc[longdesc.find["#"] + 1 :]
        soup = BeautifulSoup(text, "html.parser")
        elem = soup.find(id=id_word)
        return elem.text
    return clean.clean_html(text, True, True, True)


def get_associated_text(driver, element, body):
    id_associated_first = element.get_attribute(driver, "aria-labelledby")
    id_associated_second = element.get_attribute(driver, "aria-describedby")
    id_link = element.get_attribute(driver, "id")
    associated_text = ""

    if id_associated_first or id_associated_second:
        if id_associated_first and id_associated_second:
            id_associated_first += " " + id_associated_second
        elif id_associated_second:
            id_associated_first = id_associated_second

        if id_link:
            id_associated_first = id_associated_first.replace(id_link, "")

        id_associated_first = [id for id in id_associated_first.split(" ") if id and id != " "]

        for id in id_associated_first:
            associated_text += body.get_element(driver).find_element_by_id(id).text
            associated_text += " "

    return associated_text


def get_ancestor_with_children(driver, elem):
    """looking for the nearest ancestor who has several children"""

    ancestor = elem
    while len(get_children(driver, ancestor.get_parent(driver))) < 2:
        ancestor = ancestor.get_parent(driver)
    return ancestor.get_parent(driver)


def fig_caption_text(image, driver):
    ancestor = get_ancestor_with_children(driver, image)

    return (
        ancestor.find_by_xpath("child::figcaption", driver)[0].get_text(driver)
        if ancestor.tag_name == "figure"
        else ""
    )


def get_description_image(driver, image, body, dict_flag=False):
    print("\nget_description_image")
    associated_text = get_associated_text(driver, image, body)
    print("\nassociated_text", associated_text)

    alt = image.get_attribute(driver, "alt") or ""
    print("alt", alt)
    aria_label = image.get_attribute(driver, "aria-label") or ""
    print("aria_label", aria_label)
    title = image.get_attribute(driver, "title") or ""
    print("title", title)
    caption_text = fig_caption_text(image, driver)
    print("caption_text", caption_text)
    longdesc = get_longdesc(driver, image)
    print("longdesc", longdesc)

    if dict_flag:
        description = {"associated_text": associated_text.lower()} if associated_text else {}
        description["alt"] = alt and alt.lower()
        description["aria-label"] = aria_label and aria_label.lower()
        description["title"] = title and title.lower()
        description["figcaption"] = caption_text and caption_text.lower()
        description["longdesc"] = longdesc and longdesc.lower()
    else:
        description = " ".join(
            f"{associated_text} {alt} {aria_label} {title} {caption_text} {longdesc}".split()
        ).lower()
    print("\ndescription", description)

    return description


def get_elem_text_without_link(driver, elem):
    """"Selection of the link parent text(without the text of other links)"""

    descendants = elem.find_by_xpath("descendant::*", driver)
    html = elem.source
    for child in descendants:
        if child.tag_name == "a":
            html = html.replace(child.source, "")
    return set(clean.clean_html(html, True, True, True).split(" "))


def header_text(driver, children, obj, definition):
    """Find title text for a given object"""

    for child1, child2 in zip(children, children[1:]):
        if child2 == obj and (child1.tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]):
            text = set(clean.clean_html(child1.get_text(driver), True, True, True).split(" "))
            text.discard("")
            if text:
                definition.update(text)
                return definition
    return definition


def parse_table(driver, string, table, looking_elem):
    """Getting the name of a column and row for an element that is a table cell"""

    children_str = get_children(driver, string)
    index = 0
    for i, child in enumerate(children_str):
        if child == looking_elem:
            index = i
    name_str = children_str[0].get_text(driver)
    columns = get_children(driver, table)
    names = get_children(driver, columns[0])
    column_name = ""
    if names[index].tag_name == "th":
        column_name = names[index].get_text(driver)
    return set(clean.clean_html(column_name, True, True, True).split(" ")) | set(
        clean.clean_html(name_str, True, True, True).split(" ")
    )


def definition_link(driver, link_element, body):
    """ Finding text that explains the purpose of the link"""

    ignore = False
    descendants = link_element.find_by_xpath("descendant::*", driver)
    parent = link_element.get_parent(driver)
    grandparent = parent.get_parent(driver)
    try:
        parent_grandparent = grandparent.get_parent(driver)
    except InvalidSelectorException:
        parent_grandparent = None

    text = ""
    hidden_text = ""
    description_image = ""
    for descendant in descendants:
        if descendant.tag_name == "span":
            hidden_text += clean.clean_html(descendant.source, True, True, True)
        if descendant.tag_name == "img":
            description_image += get_description_image(driver, descendant, body)

    aria_label_link = link_element.get_attribute(driver, "aria-label")
    if not aria_label_link:
        aria_label_link = ""

    if aria_label_link == "close":
        role = link_element.get_attribute(driver, "role")
        if role == "button":
            ignore = True

    role = link_element.get_attribute(driver, "role")
    if role == "button" and link_element.get_text(driver).lower() == "log in":
        return {}, True

    text = clean.clean_html(link_element.source, True, False, False)
    title = link_element.get_attribute(driver, "title")
    if not title:
        title = ""

    associated_text = get_associated_text(driver, link_element, body)

    value = link_element.get_attribute(driver, "data-click-value")
    if value is None:
        value = ""
    else:
        href = value[value.find('href":') + 7 :]
        href = href[: href.find('"')]
        v = value[value.find('value":') + 7 :]
        v = v[: v.find('"')]
        value = f"{href} {v}"

    definition = f"{text} {description_image} {hidden_text} {aria_label_link} {title} {associated_text} {value}"
    definition = definition.lower()
    for word in stop_list:
        definition = definition.replace(word, " ")
    definition = set(clean.clean_html(definition, True, True, True).split(" "))
    definition.discard("")

    if parent.tag_name == "td" and parent_grandparent is not None:
        definition.update(parse_table(driver, grandparent, parent_grandparent, parent))

    if len(definition) <= 2:
        parent_text = get_elem_text_without_link(driver, parent)
        parent_text.discard("")
        if len(parent_text):
            definition.update(parent_text)
        # for a list of links
        elif parent.tag_name == "li" and len(parent.find_by_xpath("//a", driver)) > 1:
            definition.update(
                set(
                    clean.clean_html(
                        parent.find_by_xpath("//a", driver)[0].get_text(driver), True, True, True
                    ).split(" ")
                )
            )

        if len(definition) > 2:
            return definition, ignore

        if (
            parent.tag_name == "li"
            and grandparent.tag_name in ["ul", "ol"]
            and len(get_children(driver, parent)) == 1
        ):
            grandparent_text = grandparent.get_parent(driver).get_text(driver)
            if len(grandparent_text):
                definition.update(grandparent_text)
                return definition, ignore
            elif parent_grandparent is not None:
                children = get_children(driver, parent_grandparent)
                if len(children) == 1:
                    text = parent_grandparent.get_text(driver).replace(grandparent.get_text(driver), " ")
                    text = set(clean.clean_html(text, True, True, True).split(" "))
                    text.discard("")
                    if len(text):
                        definition.update(text)
                        return definition, ignore
                    children = get_children(driver, children[0])
                    for child in children:
                        if len(child.get_text(driver)):
                            definition.update(
                                set(clean.clean_html(child.get_text(driver), True, True, True).split(" "))
                            )
                        return definition, ignore
                else:
                    len_definition = len(definition)
                    definition = header_text(driver, children, grandparent, definition)
                    if len(definition) > len_definition:
                        return definition, ignore

        children = get_children(driver, parent)
        parents = get_children(driver, grandparent)
        if len(children) > 1:
            definition = header_text(driver, parents, parent, definition)
    return definition, ignore