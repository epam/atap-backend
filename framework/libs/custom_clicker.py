class CustomClicker:
    def __init__(self, locator, webdriver_instance, stop_words):
        self.locator = locator
        self.driver = webdriver_instance
        self.stop_words = stop_words

    def click(self):
        print("=====>Start clicks")
        clicked_elements = []
        for element in self.locator.get_activatable_elements():
            txt = ":".join(str([element.get_element(self.driver).text,
                                element.get_element(self.driver).get_attribute('id'),
                                element.get_element(self.driver).get_attribute('value'),
                                element.get_element(self.driver).get_attribute('class'),
                                element.get_element(self.driver).get_attribute('name'),
                                element.get_element(self.driver).get_attribute('title')])).lower()
            if any([x in txt for x in self.stop_words]):
                element.click(self.driver)
                clicked_elements.append(
                    {
                        "source": element,
                        "problem": "Click this element, don't help"
                    }
                )
        return clicked_elements
