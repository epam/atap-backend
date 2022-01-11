import re
import time

from selenium import webdriver
from selenium.common.exceptions import JavascriptException, UnexpectedAlertPresentException

URL_REGEX = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)


JS_GET_PERFORMANCE_DATA = """
    var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
    var network = performance.getEntries() || {};
    function decycle(obj, stack = []) {
        if (!obj || typeof obj !== 'object')
            return obj;
        
        if (stack.includes(obj))
            return null;
    
        let s = stack.concat([obj]);
    
        return Array.isArray(obj)
            ? obj.map(x => decycle(x, s))
            : Object.fromEntries(
                Object.entries(obj)
                    .map(([k, v]) => [k, decycle(v, s)]));
    }
    return network;
"""

MAX_TRIES_BETWEEN_REQUESTS = 10

TIMEOUT = 20


def wait_for_page_load(webdriver_instance: webdriver.Firefox):
    urls = []

    a = 30

    start = time.time()
    tries_without_requests = 0
    while tries_without_requests < MAX_TRIES_BETWEEN_REQUESTS and time.time() - start < TIMEOUT:
        a -= 1
        try:
            requests = webdriver_instance.execute_script(JS_GET_PERFORMANCE_DATA)
        except JavascriptException:
            continue
        except UnexpectedAlertPresentException:
            print("Alert present, not waiting any longer")
            return

        waiting_count = 0
        tries_without_requests += 1

        for request in requests:
            if URL_REGEX.match(request['name']) is None:
                continue
            if request['name'] not in urls:
                tries_without_requests = 0
                if 'responseEnd' in request:
                    urls.append(request['name'])
                    # print(f"READY {request['name']}")
                else:
                    # print(f"WAIT {request['name']}")
                    waiting_count += 1

        # print(f"still waiting for {waiting_count} requests")
        time.sleep(0.5)

    # print(f"Page loaded, delayed {time.time()-start}s")
