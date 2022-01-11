import json
from time import sleep

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Firefox

import framework.test
from framework import element
from framework import test_system
from framework import xlsdata
import uuid

with open('framework/axe_groupings.json', 'r', encoding='utf-8') as f:
    AXE_GROUPINGS = json.load(f)


class ImportedTest(framework.test.Test):
    def __init__(self, name, category, human_name, status, message, problematic_elements, checked_elements, WCAG):
        self.status = status
        self.category = category
        self.WCAG = WCAG
        self.name = name
        self.message = message
        self.problematic_elements = problematic_elements
        self.human_name = human_name
        self.framework_version = 3
        self.checked_elements = set(checked_elements)
        self.visible = True
        self.problematic_pages = []
        self.run_times = list()


def inject_axe(webdriver):
    with open('/axe.min.js', 'r', encoding='utf8') as axe_f:
        webdriver.execute_script(axe_f.read())


def get_available_tests():
    webdriver = Firefox()
    inject_axe(webdriver)
    result = webdriver.execute_script('return axe.getRules()')
    webdriver.quit()
    grouped_tests = []
    for test_group in AXE_GROUPINGS.values():
        grouped_tests.extend(test_group)

    print(f'Grouped tests: {grouped_tests}')

    tests = []
    for test in result:
        test_rule_id = test['ruleId']
        if test_rule_id in grouped_tests:
            continue
        issue_data = xlsdata.get_data_for_issue(test_rule_id)
        if issue_data['issue_type'].startswith('#'):
            print(f'No data for {test_rule_id}')
            continue

        axe_test_data = {
            'name': test_rule_id,
            'human_name': issue_data['issue_type'],
            'groups': issue_data['groups'],
            'labels': issue_data['labels']
        }

        print(f'Adding axe test {test_rule_id} as {axe_test_data["human_name"]}')
        tests.append(axe_test_data)

    return tests


def run_tests(webdriver_instance: Firefox, activity, tests_filter):
    webdriver_instance.set_script_timeout(120)
    activity.get(webdriver_instance)
    sleep(2)
    inject_axe(webdriver_instance)

    # Add all tests under group to axe filter
    for test_group_under, grouped_tests in AXE_GROUPINGS.items():
        if test_group_under in tests_filter:
            print(f'Activating grouped tests {grouped_tests} for {test_group_under}')
            tests_filter.extend(grouped_tests)

    axe_results = {}
    tries = 3
    while tries > 0:
        tries -= 1
        try:
            command = 'var callback = arguments[arguments.length - 1]; axe.run().then(results => callback(results))'
            axe_results = webdriver_instance.execute_async_script(command)
            if tests_filter is not None:
                for category in ('violations', 'inapplicable', 'passes', 'incomplete'):
                    axe_results[category] = filter(lambda res: res['id'] in tests_filter, axe_results[category])
            break
        except TimeoutException as e:
            if tries == 0:
                print('ERROR: Axe timed out 3 times!')
                raise e
            continue

    pseudo_tests = []
    axe_tests = []

    for test in axe_results['incomplete']:  # iterator after filter
        test['framework_status'] = 'FAIL'
        test['framework_severity'] = 'WARN'  # needs review
        axe_tests.append(test)

    for test in axe_results['violations']:  # iterator after filter
        test['framework_status'] = 'FAIL'
        test['framework_severity'] = 'FAIL'
        axe_tests.append(test)

    for test in axe_results['inapplicable']:  # iterator after filter
        test['framework_status'] = 'NOELEMENTS'
        for axe_test in axe_tests:
            if axe_test['id'] == test['id']:
                break
        else:
            axe_tests.append(test)

    for test in axe_results['passes']:  # iterator after filter
        test['framework_status'] = 'PASS'
        for axe_test in axe_tests:
            if axe_test['id'] == test['id']:
                break
        else:
            axe_tests.append(test)

    for axe_test in axe_tests:
        axe_test_id = axe_test['id']
        issue_data = xlsdata.get_data_for_issue(axe_test_id)
        if issue_data['issue_type'].startswith('#'):
            print(f'No data for {axe_test_id}')
            continue

        WCAG = issue_data['WCAG']

        problematic_elements = []
        checked_elements = []
        if axe_test['framework_status'] == 'FAIL':
            for node_id, node in enumerate(axe_test['nodes']):
                # TODO: Support iframes and shadow DOM
                try:
                    current_element = element.Element(None, webdriver_instance, selector_no_id=node['target'][0],
                                                      force_rebuild_selector=True)
                except element.ElementLostException:
                    continue

                node_impact = node['impact']
                print(node_impact)
                if node_impact is not 'null':
                    if current_element.tag_name == 'html':
                        continue
                    problematic_element = {
                        'element': current_element,
                        'source': node['html'],
                        'problem': node_impact,
                        'severity': axe_test['framework_severity'],
                        'error_id': axe_test_id,
                        'uuid': uuid.uuid4().hex
                    }
                    if 'pages' not in problematic_element:
                        problematic_element['pages'] = []
                    problematic_element['pages'].append(activity.url)
                    problematic_elements.append(problematic_element)
                checked_elements.append(current_element)

            if len(problematic_elements) == 0:
                problematic_elements.append({
                    'element': element.Element(webdriver_instance.find_element_by_tag_name('body'), webdriver_instance),
                    'error_id': axe_test_id,
                    'problem': 'Page does not pass aXe checks',
                    'pages': [activity.url],
                    'force_best_practice': 'best-practice' in axe_test['tags'],
                    'uuid': uuid.uuid4().hex
                })

        print(f'Appending axe test {axe_test_id}')
        pseudo_tests.append(ImportedTest(
            name=axe_test_id,
            category='aXe_tests',
            human_name=axe_test['description'],
            status=axe_test['framework_status'],
            message=axe_test['help'],
            problematic_elements=problematic_elements,
            checked_elements=checked_elements,
            WCAG=', '.join(WCAG)
        ))

    # Set grouped tests' error id to match parent test
    for test_group_under, grouped_tests in AXE_GROUPINGS.items():
        for grouped_test in grouped_tests:
            for pseudo_test in pseudo_tests:
                if pseudo_test.name == grouped_test:
                    for problematic_element in pseudo_test.problematic_elements:
                        problematic_element['error_id'] = test_group_under
                    print(f'Grouped test {grouped_test} under {test_group_under}')
                    break
            else:
                print(f'WARNING: Grouped test not found in results: {grouped_test}')
    for test in pseudo_tests:
        print(f'{test.name} - {test.status} ({len(test.problematic_elements)})')
    return pseudo_tests
