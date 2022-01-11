from selenium import webdriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException,\
                        ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from framework.element import Element
from framework.element_locator import ElementLocator
from framework.element_wrapper import ElementWrapper
from framework.element import ElementLostException
from framework.libs.custom_nlp import re_keywords
from framework.tests.edit_box.fake_data import fake_data
from framework.tests.edit_box.base_func import BaseFunc

from random import randint, choice
from re import sub


name = "Provides utility methods and globals for alerts tests.\
        Acts as parent class, operates driver, locator and deps data."
depends = []  # implicit dependency "spacy_en_lg"


class AlertsController:

    # possible box element types for identifying its label through 'for' attr
    ATTR_FOR = ('id', 'name')
    # input element types or special tags, use to choose the variant of action on elem
    # EXCL_TYPES is used to avoid some undesired elements
    EXCL_TYPES = ('hidden', 'search', 'submit', 'reset')
    TEXT_TYPES = ('text', 'tel', 'email', 'password', 'number', 'color', 'url', 'textarea')
    BTN_TYPES = ('button', 'checkbox', 'radio')
    RNG_TYPES = ('range',)
    DT_TYPES = ('datetime-local', 'year', 'month', 'week', 'date', 'time')
    FILE_TYPES = ('file', 'image')
    # global variables, used in many methods
    INPUTS = ('input', 'textarea', 'select')  
    ACTIONS = dict()
    CHANGED = set()
    BOXES_MESSAGE = dict()
    BOXES_DESCRIBED = set()
    WARN_ELEMENTS = []
    ALERT_TEXT = set()
    # specified globals, error messages and labels 
    COMMON_MESSAGE = {'wrong', 'enter', 'mistak', 'retri', 'requir', 'error', 'unsuccess',
                    'success', 'failur', 'invalid', 'bad', 'good', 'miss', 'alert', 'ok'}
    ARIA = ("aria-label", "aria-invalid", "aria-live", "aria-required", "required")
    ARIA_FOR = ("aria-describedby", "aria-labelledby")

    def __init__(self, driver, activity, locator, dependencies):
        self._dr = driver
        self._locator = locator
        self._act = activity
        self._dep = dependencies

    @property
    def _func(self):
        return BaseFunc(self._dr)
    
    def wrap(self, el):
        return ElementWrapper(el, self._dr)

    def source(self, el):
        try:
            return el.get_element(self._dr).get_attribute("outerHTML")
        except (ElementLostException, NoSuchElementException, StaleElementReferenceException):
            return "None"

    def visible(self, el: Element):
        try:
            return expected_conditions.visibility_of(el.get_element(self._dr))(self._dr)
        except (ElementLostException, StaleElementReferenceException):
            return False

    def set_elem_actions(self):
        offset = lambda slider: randint(0, int(slider.get_attribute('max')))
        option = lambda select: choice(Select(select).options).get_attribute('value')
        self.ACTIONS.update({_type: lambda t, data: t.send_keys(data) for _type in
                                                    self.TEXT_TYPES})
        self.ACTIONS.update({_type: lambda t: t.click() for _type in self.BTN_TYPES})
        self.ACTIONS.update({_type: lambda t: ActionChains(self._dr).
                                drag_and_drop_by_offset(t, xoffset=offset(t), yoffset=0).perform()
                                for _type in self.RNG_TYPES})
        self.ACTIONS.update({'select': lambda t: Select(t).select_by_value(option(t))})
        self.ACTIONS.update({_type: lambda t: NotImplemented for _type in self.DT_TYPES})  # not sure if needed
        self.ACTIONS.update({_type: lambda t: NotImplemented for _type in self.FILE_TYPES})  # not sure if needed
        self.ACTIONS.update(dict(undefined=lambda t: t))

    def interact(self, elem, param=''):
        """
        Method for unified way of element interaction 
        """
        _type = elem.get_attribute(self._dr, 'type') or elem.tag_name
        selector = elem.get_selector()
        try:
            elem = elem.get_element(self._dr)
        except (NoSuchElementException, ElementLostException, StaleElementReferenceException):
            pass
        try:
            WebDriverWait(self._dr, 1).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            action = self.ACTIONS.get(_type, self.ACTIONS['undefined'])            
            if _type in self.TEXT_TYPES:
                action(elem, param)
            else:
                action(elem)
            WebDriverWait(self._dr, 1).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            return
    
    def redirection(self, url: str, eigenelems: list):
        """
        Method ensures that redirection to
        another url address will be noticed.
        If url changes, gracefully restores page
        """
        try:
            WebDriverWait(self._dr, 4).until(
                expected_conditions.url_changes(url))
        except TimeoutException:
            return False
        try:
            for lost_elem in eigenelems:
                lost_elem.get_element(self._dr)
            return False
        except (NoSuchElementException, ElementLostException):
            self._act.get(self._dr)
            return True

    def missing_alert(self, el):
        """
        check for popup alert window
        return False if only was alert window with clear text and focus back to el
        """
        elem_vocab = self.elem_vocab(el, label=self.found_label(el))
        alert_text = self.ALERT_TEXT
        # FOUND valid text in alert
        text_flag = set(filter(lambda word: word in alert_text, elem_vocab))
        # focus_flag = self._dr.execute_script(f'return document.querySelector({el.selector}) ===\
                                            # document.activeElement;')
                                            # # TODO remember focus position right after alert
        if text_flag: # and focus_flag:
            del self.BOXES_MESSAGE[el.get_selector()]
            return False
        return True

    def missing_role(self, el):  # valid elements and types for assertive
        role_xpath = '//*[ancestor::*[@role="alert" or @aria-live] or @role="alert"]'
        role_elements = self._locator.get_all_by_xpath(self._dr, role_xpath)
        if not role_elements:
            return True
        role_elements = [elem.source for elem in role_elements]
        text = self.keywords_of_elem(el)
        if not text:
            return True
        elem_vocab = self.elem_vocab(el, label=self.found_label(el))
        # FOUND meaningful text in element with role alert (already is in text container)
        for sbox in self.BOXES_MESSAGE.keys():
            box = Element(self._dr.find_element_by_css_selector(sbox), webdriver_instance=self._dr)
            text_flag = set(filter(lambda word: word in self.BOXES_MESSAGE[sbox], elem_vocab))
            text_flag = text_flag or box.get_attribute(self._dr, 'aria-invalid')
            if text_flag and self.check_distance(el, box, maxdist=200):
                self.BOXES_DESCRIBED.add(sbox)
                if el.source in role_elements:
                    self.BOXES_MESSAGE[sbox] = 'del'  # now good box                    
        if 'del' in self.BOXES_MESSAGE.values():
            self.BOXES_MESSAGE = {sbox: msg for sbox, msg in self.BOXES_MESSAGE.items()
                                                                    if msg != 'del'} 
        text_flag = set(filter(lambda word: word in text, elem_vocab))
        if text_flag and el.source in role_elements:
            return False
        return True

    def missing_heading(self, el):
        h_tags = [f'self::h{level}' for level in range(1, 7)]
        h_xpath = f'//*[{" or ".join(h_tags)} or self::title]'
        headings = self._locator.get_all_by_xpath(self._dr, h_xpath)
        headings = [elem.source for elem in headings]
        if not el.source in headings:
            return True
        elem_vocab = self.elem_vocab(el)
        # FOUND error/succ text in heading: WARN, FOUND alongside text
        # from tag, its label or found aria in tag: PASS
        for sbox in self.BOXES_MESSAGE.keys():
            box = Element(self._dr.find_element_by_css_selector(sbox), webdriver_instance=self._dr)
            text_flag = set(filter(lambda word: word in self.BOXES_MESSAGE[sbox], elem_vocab))
            if text_flag:
                self.BOXES_DESCRIBED.add(sbox)
                self.BOXES_MESSAGE[sbox] = 'del'  # now good box
        if 'del' in self.BOXES_MESSAGE.values():
            self.BOXES_MESSAGE = {sbox: msg for sbox, msg in self.BOXES_MESSAGE.items()
                                                                    if msg != 'del'} 
        if text_flag:  # do not call other 'missings' for change
            return False
        return True

    def missing_aria(self, el):
        text_flag, aria_desc_attr = False, False
        aria_attr = any([el.get_attribute(self._dr, attr) is not None for attr in self.ARIA])
        elem_vocab = self.elem_vocab(el, label=self.found_label(el))
        # FOUND error/succ text within aria or tag with aria, if no text WARN
        text = self.keywords_of_elem(el)
        label = self.found_label(el, domain=self.CHANGED)
        if label:
            wrapped_label = self.wrap(label)
            label_text = self.keywords_of_elem(label)
            text = text.union(label_text)
            # check label aria-described
            aria_desc = {lab_attr:
                        [str(self.wrap(el)[attr]) for attr in self.ARIA_FOR]
                        for lab_attr in self.ATTR_FOR}
            for lab_attr in aria_desc:
                aria_common = [set(str(wrapped_label[lab_attr]).split()).
                                intersection(elem_attr.split()).
                                difference({'None',})
                                for elem_attr in aria_desc[lab_attr]]
                if any(aria_common):
                    aria_desc_attr = True

        for sbox in self.BOXES_MESSAGE.keys():
            box = Element(self._dr.find_element_by_css_selector(sbox), webdriver_instance=self._dr)
            text_flag = set(filter(lambda word: word in self.BOXES_MESSAGE[sbox], elem_vocab))
            text_flag = text_flag or box.get_attribute(self._dr, 'aria-invalid')
            if text_flag and self.check_distance(el, box, maxdist=300):
                self.BOXES_DESCRIBED.add(sbox)
                if aria_attr or aria_desc_attr:
                    if box.source == el.source:
                        self.BOXES_MESSAGE[sbox] = 'del'  # now good box
                    else:
                        box_aria = any([box.get_attribute(self._dr, attr) for attr in
                                                                    self.ARIA + self.ARIA_FOR])
                        if box_aria:
                            self.BOXES_MESSAGE[sbox] = 'del'  # one more good box
        if 'del' in self.BOXES_MESSAGE.values():
            self.BOXES_MESSAGE = {sbox: msg for sbox, msg in self.BOXES_MESSAGE.items()
                                                                    if msg != 'del'} 
        text_flag = set(filter(lambda word: word in text, elem_vocab))
        if text_flag and aria_attr or aria_desc_attr:
            return False
        return True

    def missing_hyperlink(self, el):
        a_xpath = '//a[starts-with(@href, "#")]'
        links = self._locator.get_all_by_xpath(self._dr, a_xpath)
        links = [elem.source for elem in links]
        if not el.source in links:
            return True
        elem_vocab = self.elem_vocab(el)
        for sbox in self.BOXES_MESSAGE.keys():
            box = Element(self._dr.find_element_by_css_selector(sbox), webdriver_instance=self._dr)
            # FOUND common words in a and el
            text_flag = set(filter(lambda word: word in self.BOXES_MESSAGE[sbox], elem_vocab))
            if text_flag and\
                box.get_attribute(self._dr, 'id') in el.get_attribute(self._dr, 'href'):
                self.BOXES_DESCRIBED.add(sbox)
                self.BOXES_MESSAGE[sbox] = 'del'  # now good box
        if 'del' in self.BOXES_MESSAGE.values():
            self.BOXES_MESSAGE = {sbox: msg for sbox, msg in self.BOXES_MESSAGE.items()
                                                                    if msg != 'del'} 
            return False
        return True

    def save_visible(self):
        """
        Method creates a dict of elements
        with visible text only, not table children
        {selector: element} 
        """
        xpath = "//body//*[normalize-space(text()) and\
                not(ancestor::table or self::script or self::code\
                                    or self::noscript)]"
        # there are also <embed> and many other tags with text...                                                
        elements = self._locator.get_all_by_xpath(self._dr, xpath)
        elements = [elem for elem in elements
                    if self.visible(elem)]
        elements = {self.source(elem): elem for elem in elements}
        return elements
    
    def filter_box_elems(self, box_elems):
        """
        Method returns modified box elements from dependency
        It excludes inputs with bad types
        So used to not to change the original for a few cases 
        """
        return list(
                filter(lambda box: box.get_attribute(self._dr, 'type')\
                            not in self.EXCL_TYPES,
                        box_elems))

    def detected_alert(self):
        alert_text = set()
        try:
            WebDriverWait(self._dr, 4).until(expected_conditions.alert_is_present(),
                                              "Timed out waiting for PA creation confirmation popup to appear.")
            alert = self._dr.switch_to.alert
            alert_text = set(alert.text.lower().split())
            alert.dismiss()
            self.ALERT_TEXT.update(alert_text)
        except TimeoutException:
            return {''}
        return alert_text
    
    def filter_lost_elements(self, elements: list):
        """
        Method supposed to be called before locating elements
        in addition to already located.
        It will filter lost elements in already located,
        if there was some page changes, so elements vanished from DOM.  
        """
        present_elements = []
        for element in elements:
            try:
                element.get_element(self._dr)
                assert self.visible(element)
                present_elements.append(element)
            except (NoSuchElementException, ElementLostException, AssertionError):
                continue
        return present_elements
    
    def get_changed_elements(self, genuine_elements: dict, box_elems: list):
        """
        Method returns all changed and new elements.
        Includes edit boxes and their <div> parents.
        Element supposed to be changed if there is an error on page
        """
        # there are also <embed> and many other tags with text...                                                
        # find all elements with new selectors or if their outerHTML changed
        changes = set(self.save_visible().values())
        box_elems = self.filter_box_elems(box_elems)
        changes = changes.union(box_elems)
        changes = {elem for elem in changes
                        if not genuine_elements.get(self.source(elem))}
        return changes

    def complete_form(self, inputs: list):
        """
        Method sends text data or make other actions
        to elements in box elements
        """
        for elem in inputs:
            _type = self.wrap(elem)['type']
            data = fake_data().get(_type, '')
            self.interact(elem, data)

    def _click_after_overlap(self, button: Element, new_elements: list):
        """
        Ensures button will be clicked after it was overlapped
        due to form action.
        Solution: click all clickable elements after changes
        """
        try:
            try:
                button.get_element(self._dr).click()
            except ElementClickInterceptedException:
                for elem in new_elements:
                    try:
                        elem.get_element(self._dr).click()
                    except ElementClickInterceptedException:
                        continue
                button.get_element(self._dr).click()
        except (ElementClickInterceptedException, ElementLostException, StaleElementReferenceException):
            return
            

    def submit_form(self, form: Element):
        """
        Method for quick submit a form if the has one submit button
        """
        submit = False
        if all(map(lambda elem: elem.get_attribute(self._dr, 'type')\
                        in self.EXCL_TYPES + (None,),
                    form.find_by_xpath(".//*", self._dr))):
            return False
        subm = form.find_by_xpath(".//input[@type='submit']", self._dr)
        btn = form.find_by_xpath(".//button[@type='submit']", self._dr)
        if subm and len(subm) == 1:
            self._click_after_overlap(subm[0], self.CHANGED)
            submit = True
        elif btn and len(btn) == 1:
            self._click_after_overlap(btn[0], self.CHANGED)
            submit = True
        else:
            return self.submit(form)
        return submit
        
    def submit(self, form: Element):
        """
        Method to go through elements and
        submit right buttons close to edit boxes
        This is called if 'submit_form' failes
        """
        min_dist, submit_dist = 300, 300
        submit = False
        inputs = form.find_by_xpath(".//*", self._dr)
        inputs = [elem for elem in inputs if elem.tag_name not in
                    ('div', 'p', 'ul', 'li') and self.visible(elem)]
        if not inputs:
            return False
        subm_candidates = [elem for elem in inputs if elem.\
                                get_attribute(self._dr, 'type') == 'submit' or
                                {'submit', 'send', 'ok'}.intersection(
                                self.elem_vocab(elem))]
        subm_range = {cand: min_dist for cand in subm_candidates}
        inputs = [elem for elem in inputs if elem.tag_name in self.INPUTS]
        last_elem = inputs[0]
        for subm in subm_candidates:
            submit_dist = min_dist
            wrapped_btn = self.wrap(subm)
            for elem in self.filter_box_elems(inputs):
                wrapped_elem = self.wrap(elem)
                distance = wrapped_elem.min_distance(wrapped_btn)
                if 0 < distance < min_dist:
                    last_elem = elem
                    submit_dist = distance
            subm_range[subm] = submit_dist
        try:
            subm_range = {subm: rng for subm, rng in subm_range.items() if rng < min_dist}
            url = self._dr.current_url
            for subm in subm_range:
                self._click_after_overlap(subm, self.CHANGED)
                self.detected_alert()
                self.redirection(url, self.CHANGED | {subm,})
                submit = True
            return submit
        except (ValueError, AttributeError, ElementLostException, NoSuchElementException):
            pass
        if not submit:
            try:
                form.get_element(self._dr).submit()
                last_elem.get_element(self._dr).send_keys(Keys.ENTER)
                submit = True
            except (ElementLostException, StaleElementReferenceException):
                pass
        return submit
    
    def keywords_of_elem(self, elem):
        """
        Method gets keywords from text
        """
        try:
            model = self._dep["spacy_en_lg"]
            
            text = sub('[^A-Za-z0-9]+', ' ', elem.get_text(self._dr))
            text = set(re_keywords(model, text))
        except ElementLostException:
            return set()
        return text

    def elem_vocab(self, elem, label=None, text_data=''):
        """
        Method collects keywords of elem div parent text and name attributes
        Checks for label as elem too
        """
        model = self._dep["spacy_en_lg"]
        if elem.tag_name != "label":
            div_parent = elem  # ?
            while not div_parent.tag_name not in ("div", "body"):
                div_parent = div_parent.get_parent(self._dr)
            elem = div_parent if div_parent.tag_name != "body" else elem
        try:
            attr_text = " ".join([elem.get_attribute(self._dr, attr) for attr in self.ATTR_FOR
                                if elem.get_attribute(self._dr, attr)])
            placeholder_text = elem.get_attribute(self._dr, 'placeholder')
            placeholder_text = placeholder_text if placeholder_text else ''
            text_data = f'{text_data} {attr_text} {placeholder_text} {elem.get_text(self._dr)}'
            text_data = text_data.lower()
        except ElementLostException:
            pass
        if label:
            return self.elem_vocab(label, text_data=text_data)
        vocab = {word for word in re_keywords(model, text_data)
                    if word.isalpha()}
        vocab = vocab.union(set(text_data.split()))
        return vocab

    def __possible_boxes(self, el):
        """
        Checks for possible edit box
        """
        by_keywords = self._func.contains_keywords(el)
        return by_keywords or el.tag_name in self.INPUTS

    def _existence_btn(self, element: Element):
        """
        Search a button next to an item
        """
        elements = element.find_by_xpath(".//*", self._dr)
        return any([el for el in elements if self._func.is_btn(el)])
    
    def __clarification(self, el: Element):
        """
        Method clarifies elem to be an example of edit_box or button
        """
        visible = self.visible(el)
        if not visible:
            return False
        try:
            send = self._func.send_text(el)
            exist_btn = self._existence_btn(el)
            child_form = el.find_by_xpath("./*[child::form]", self._dr)
            attr_text = el.get_attribute(self._dr, "text")
        except (ElementLostException, StaleElementReferenceException):
            return False
        return any([send, exist_btn, child_form, attr_text])

    def edit_box_base(self, parent: Element):
        """Collect found edit boxes from domain
        Domain is normally form elements
        """
        edit_boxes = []
        elements = parent.find_by_xpath(".//*[not(ancestor::table)]", self._dr)
        for elem in elements:
            if self.__possible_boxes(elem):
                if self.__clarification(elem):
                    edit_boxes.append(elem)
        return edit_boxes

    def _selector_intersection(self, cont1, cont2):
        scont1 = [elem.source for elem in cont1]
        scont2 = [elem.source for elem in cont2]
        scont = set(scont1).intersection(scont2)
        cont1.extend(cont2)
        res = {elem for elem in cont1 if elem.source in scont}        

        return res
    
    def check_distance(self, el, label, maxdist=150):
        """
        Checking the distance between elements using coordinates
        """
        wrapped_label = self.wrap(label)
        wrapped_element = self.wrap(el)
        min_distance = wrapped_element.min_distance(wrapped_label)
        flag_distance = 5 < min_distance < maxdist
        if flag_distance:
            return True
        return False
    
    def found_label(self, el, domain=None):
        """
        This method search labels for attribute
        If label without for, check distance for label
        returns label element or None if elem doesn't have it
        """
        if domain:
            labels = [label for label in domain
                        if label.tag_name in ('label', 'legend', 'span')]
        else:
            xpath = '//*[self::label or self::legend or self::span]'
            labels = self._locator.get_all_by_xpath(self._dr, xpath)
        wrapped_elem = self.wrap(el)
        _type = el.get_attribute(self._dr, 'type')
        for label in labels:
            wrapped_label = self.wrap(label)
            # label has for
            if wrapped_label["for"] and label != el:
                linked_flag = any([wrapped_label["for"] in str(wrapped_elem[attr])
                                    for attr in self.ATTR_FOR])
                if linked_flag:
                    return label
            # label is close enough, do not use with excluded types
            elif _type and _type not in self.EXCL_TYPES:
                if self.check_distance(el, label):
                    return label
        return None
