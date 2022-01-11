import time

from selenium import webdriver

from framework.await_page_load import wait_for_page_load
from framework.test_system import load_tests_with_dependencies

ELEMENTS_TO_COUNT = ["a", "img", "button", "input", "form", "table", "div", "span"]


def get_page_size(url):
    webdriver_instance = webdriver.Firefox()
    results = dict()
    load_start_time = time.time()
    print(f"Opening {url}")
    webdriver_instance.get(url)
    print(f"Waiting for the page to fully load...")
    wait_for_page_load(webdriver_instance)

    results["page_load_time"] = time.time() - load_start_time

    print("Counting all elements...")
    results["all_elements_count"] = len(webdriver_instance.find_elements_by_xpath("//*"))

    for element_type in ELEMENTS_TO_COUNT:
        print(f"Counting {element_type} elements...")
        results[element_type] = len(webdriver_instance.find_elements_by_xpath(f"//{element_type}"))

    print("DONE")

    webdriver_instance.quit()

    return results


def simulate_testing(tests_to_run, pages_with_size_data, test_time_data, thread_num=4):
    test_queue = list()
    finished_tests = list()

    threads = [None]*thread_num

    print(f"Loading test data...")
    tests_with_data = load_tests_with_dependencies(tests_to_run, None)

    for page_with_size_data in pages_with_size_data:
        for activity_id in range(page_with_size_data["activity_count"]):
            for test_with_data in tests_with_data:
                if test_with_data.name not in test_time_data:
                    print(f"WARNING: no time data for {test_with_data.name}!")
                    time = 60
                else:
                    time = test_time_data[test_with_data.name]["time_constant"] + test_time_data[test_with_data.name]["time_per_element"]*page_with_size_data['all_elements_count']

                test_queue.append({
                    "name": f"{test_with_data.name}_{page_with_size_data['name']}_{activity_id}",
                    "time": time,
                    "depends": [f"{dep}_{page_with_size_data['name']}_{activity_id}" for dep in test_with_data.depends]
                })

    simulated_time = 0

    def get_next_test():
        first_test = None
        while True:
            if len(test_queue) == 0:
                return None
            test = test_queue.pop(0)
            if first_test is None:
                first_test = test
            elif test['name'] == first_test['name']:
                test_queue.append(test)
                return None
            for dependency in test['depends']:
                if dependency not in finished_tests:
                    test_queue.append(test)
                    break
            else:
                return test

    def update_threads_with_tests():
        for thread_id in range(len(threads)):
            if threads[thread_id] is None:
                test = get_next_test()
                if test is not None:
                    print(f"Thread {thread_id} picked up {test['name']} for {test['time']}s")
                    test['start_time'] = simulated_time
                    threads[thread_id] = test


    update_threads_with_tests()
    while len([thread_test for thread_test in threads if thread_test is not None]) > 0:
        min_advance_time = 99999999
        for thread_test in threads:
            if thread_test is not None:
                min_advance_time = min(min_advance_time, thread_test['start_time'] + thread_test['time'])

        simulated_time = min_advance_time

        for thread_id, thread_test in enumerate(threads):
            if thread_test is not None:
                if thread_test['start_time'] + thread_test['time'] <= simulated_time:
                    print(f"Thread {thread_id} finished {thread_test['name']}")
                    threads[thread_id] = None
                    finished_tests.append(thread_test['name'])

        update_threads_with_tests()

    print(f"Simulation finished, took {simulated_time}")
    return simulated_time
