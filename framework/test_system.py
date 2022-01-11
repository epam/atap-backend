import logging
from typing import List, Optional
import importlib.util
from framework import axe_integration, xlsdata
import traceback
import os
import re

from framework import test

logger = logging.getLogger("framework.test_system")


def discover_tests(filter_test: Optional[List[str]], filter_category: Optional[List[str]]) -> List[test.Test]:
    logger.info("=>Loading tests")
    tests = list()
    test_cat_names = os.listdir("framework/"+test.TESTDIR_NAME)
    for test_cat_name in test_cat_names:
        if filter_category is not None and test_cat_name not in filter_category:
            continue

        test_cat_dir = os.path.join("framework/"+test.TESTDIR_NAME, test_cat_name)
        test_cat_file_names = os.listdir(test_cat_dir)
        for test_cat_file_name in test_cat_file_names:
            if test_cat_file_name.startswith("test_"):
                if filter_test is not None and test_cat_file_name[:-3] not in filter_test:
                    # print(f"===>SKIP")
                    continue
                test_cat_file = os.path.join(test_cat_dir, test_cat_file_name)
                logging.info(f"==>Loading test {test_cat_file_name}")
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"framework.{test.TESTDIR_NAME}.{test_cat_name}.{test_cat_file_name}"[:-3],
                        test_cat_file
                    )
                    test_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(test_module)
                    tests.append(test.Test(test_module, test_cat_file_name, test_cat_name))
                except SyntaxError:
                    logger.error(f"===>Syntax error")
                    logger.error(traceback.format_exc())
                except Exception as e:
                    logger.error(f"===>{e}")
                    logger.error(traceback.format_exc())

    logger.info(">Done")

    return tests


def get_available_tests(include_axe_tests: bool = False):
    tests = discover_tests(None, None)
    new_tests = []
    for test in tests:
        if not test.visible:
            continue
        test_data = xlsdata.get_data_for_issue(test.name)
        new_tests.append({
            'name': test.name,
            'human_name': test_data['issue_type'],
            'level': (xlsdata.cached_wcag_table_info[test.WCAG]['level']
                      if test.WCAG in xlsdata.cached_wcag_table_info else '---'),
            'conformancelevel': (xlsdata.cached_wcag_table_info[test.WCAG]['level']
                                 if test.WCAG in xlsdata.cached_wcag_table_info else '---'),
            'groups': test_data['groups'],
            'labels': test_data['labels']
        })

    if include_axe_tests:
        new_tests.extend(axe_integration.get_available_tests())
        new_tests = sorted(new_tests, key=lambda test_dict: test_dict['human_name'])
    return new_tests


def get_page_to_test_mapping():
    mapping = {}
    tests = discover_tests(None, None)
    for test in tests:
        if test.framework_version < test.MIN_FRAMEWORK_VERSION:
            continue
        if test.test_data is not None:
            for page in test.test_data:
                page_name = page["page_info"]["url"]
                if page_name not in mapping:
                    mapping[page_name] = list()
                mapping[page_name].append(test.name)
    return mapping


def load_tests_with_dependencies(filter_test, filter_category):
    tests = discover_tests(filter_test, filter_category)
    dependencies = set()
    for test in tests:
        dependencies.update(test.depends)

    logger.info(">Loading test dependencies")
    while True:
        for test in tests:
            dependencies.update(test.depends)
        for test in tests:
            if test.name in dependencies:
                dependencies.remove(test.name)

        dependencies = {dependency for dependency in dependencies if dependency.startswith("test_")}

        if len(dependencies) == 0:
            logger.info(">Done loading dependencies")
            break

        tests.extend(discover_tests(list(dependencies), None))

    logger.info(">Done loading all tests")
    return tests
