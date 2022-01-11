from selenium import webdriver
from framework.element import Element
from framework.element_locator import ElementLocator


name = "Ensures that the <p> element is correctly used for marking up text"
WCAG = '1.3.1'
framework_version = 4
webdriver_restart_required = False

elements_type = "text"
test_data = [
    {
        "page_info": {
            "url": "page_good_paragraph.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "page_bugs_paragraph.html"
        },
        "expected_status": "FAIL",
        "expected_problem_count": 1
    }
]


# depends = ['test_shortcut_list']


def test(webdriver_instance: webdriver.Chrome, activity, element_locator: ElementLocator):
    elements = list()
    result = 'Problems with paragraphs not found'
    status = 'PASS'

    elements_with_paragraphs_inside = list()
    # lists = dependencies['test_shortcut_list']['elements']

    activity.get(webdriver_instance)
    text_with_brs = find_text_with_br(element_locator, webdriver_instance)
    p_as_title = p_has_title_style(element_locator, webdriver_instance)
    #possible_paragraphs = find_element_with_text_without_styles(webdriver_instance)

    for br in text_with_brs:
        elements.append({'element': br, 'problem': '<br> separators are used between text content, paragraphs (<p>) are better to use.'})
    for p in p_as_title:
        elements.append({'element': p, 'problem': 'Bold, italic text and font-size are not used to style <p> elements as a heading.'})
    #temporary useless
    # for p in possible_paragraphs:
    #     elements.append({'element': p, 'problem': 'For marking large text make better use of paragraphs (<p>). See WCAG: 1.3.1'})

    all_p = element_locator.get_all_of_type(webdriver_instance, ["p"])
    if len(all_p) == 0:
        status = "NOELEMENTS"

    if elements:
        status = "FAIL"
        result = 'Some problems with paragraphs was found'

    if p_as_title:
        status = "FAIL"

    return {
        "status": status,
        "message": result,
        "elements": elements,
        "checked_elements": all_p
    }


def is_a_lot_of_text_between_br(el, webdriver_instance):
    is_paragraph = False
    element = el.get_element(webdriver_instance)
    children = element.find_elements_by_xpath("*")
    source = element.get_attribute('outerHTML')
    deleted = list()
    for child in children:
        if child.tag_name != 'br':
            deleted.append(child.get_attribute('outerHTML'))
    for deleted_item in deleted:
        source = source.replace(deleted_item, '')
    paragraphs = source.split('<br')
    for paragraph in paragraphs:
        if len(paragraph) > 300:
            is_paragraph = True
    return is_paragraph


def find_text_with_br(element_locator, webdriver_instance):
    elements_with_br = list()
    elements = element_locator.get_all_of_type(webdriver_instance, ['br'])

    def check_brs(element):
        if element.tag_name == 'br':
            parent = element.get_parent(webdriver_instance)
            if parent not in elements_with_br:
                source = ''.join(parent.source.split())
                if not (source.count('<br>') == 1 and ((source[source.find('br>') + 3] == '<') or (source[source.find('<br>') - 1] == '>'))):
                    if is_a_lot_of_text_between_br(parent, webdriver_instance):
                        elements_with_br.append(parent)
    Element.safe_foreach(elements, check_brs)
    return elements_with_br


def p_has_title_style(element_locator, webdriver_instance):
    problem_elements = list()
    elements = element_locator.get_all_of_type(webdriver_instance, ["p"])
    body_font = webdriver_instance.find_element_by_xpath('/html/body').value_of_css_property('font-size')
    body_font = float(body_font.replace('px', ''))

    def check_styles(element):
        if element.get_element(webdriver_instance).size['height'] > 10:
            font_weight = element.get_element(webdriver_instance).value_of_css_property('font-weight')
            bold = (int(font_weight) > 400)
            italic = (element.get_element(webdriver_instance).value_of_css_property('font-style') == 'italic')
            font_size = float(element.get_element(webdriver_instance).value_of_css_property('font-size').replace('px', ''))
            big_font = (font_size > body_font)
            if (bold or italic) and big_font:
                problem_elements.append(element)

    Element.safe_foreach(elements, check_styles)
    return problem_elements

# not use now
def find_element_with_text_without_styles(webdriver_instance):
    elements = webdriver_instance.find_elements_by_xpath('/html/body//*')
    possible_paragraphs = list()
    for element in elements:
        if (len(element.text) > 150) and element.tag_name != 'p':
            if not element.get_attribute('aria-hidden') and element.size['width'] > 40:
                possible_paragraphs.append(Element(element, webdriver_instance))
    return possible_paragraphs
