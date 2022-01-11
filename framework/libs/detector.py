import time

from selenium import webdriver

PERIOD = 10


class Detector:
    def __init__(self, web_driver: webdriver.Firefox):
        self.driver = web_driver
        self.variable_elements = self.__detect_variable_elements()

    def get_replica(self):
        return self.driver.execute_script("""
            function isVisible (ele) {
                var style = window.getComputedStyle(ele);
                return  style.width !== "0" && style.height !== "0" &&
                        style.opacity !== "0" && style.display!=='none' &&
                        style.visibility!== 'hidden';
            }

            var elements = [];
            function getSource(e) {
                var elems = e.querySelectorAll("*");
                Array.prototype.forEach.call(elems, elem => {
                    if (isVisible(elem)) {
                        elements.push(elem);
                    }
                });
            }
            getSource(document.body);
            return elements;    
        """)

    def __detect_variable_elements(self):
        time.sleep(3)

        start_time = time.time()
        previous = None
        differences = []
        while time.time() < start_time + PERIOD:
            replica = self.get_replica()

            if previous is None:
                previous = replica
            else:
                differences.extend([e for e in previous if e not in replica and e not in differences])
                previous = replica
        return differences
