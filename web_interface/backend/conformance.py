from typing import Union, List, Optional, Iterable

from django.db.models import QuerySet

from framework import xlsdata
from framework.xlsdata import cached_wcag_test_matching, cached_wcag_table_info, cached_vpat_data
from wcag_information.levels_and_versions import SC_NOT_COVERED_BY_TESTS
from wcag_information.section_dependency import DEPENDENCY_OF_SECTION_CHAPTER_WCAG
from web_interface.apps.framework_data.models import Test, TestResults
from web_interface.apps.report.models import (
    ConformanceLevel, SuccessCriteriaLevel, Section508Criteria, Section508Chapters, Issue
)


def update_data_levels(data_set: Union[QuerySet, List[SuccessCriteriaLevel], List[ConformanceLevel]],
                       all_issues: Union[QuerySet, List[Issue]], all_tests: Union[QuerySet, List[Test]]) -> None:
    for data in data_set:
        WCAG = data.WCAG if isinstance(data, ConformanceLevel) else data.criteria
        if WCAG in SC_NOT_COVERED_BY_TESTS and not Issue.objects.filter(wcag__contains=WCAG).exists():
            data.level = 'Not Identified' if isinstance(data, ConformanceLevel) else 'Select support level'
            data.remark = 'Unable to evaluate SC using automated tests. Manual testing needed'
            data.save()
            continue

        if WCAG not in cached_wcag_test_matching and not Issue.objects.filter(wcag__contains=WCAG).exists():
            continue

        affecting_issues = list()

        for issue in all_issues:
            if WCAG in issue.wcag.split(', ') and not issue.is_best_practice:
                affecting_issues.append(issue)

        names_tests_for_sc = cached_wcag_test_matching[WCAG].keys()

        tests_for_sc = all_tests.filter(name__in=names_tests_for_sc)

        if not tests_for_sc and not all_issues.filter(wcag__contains=WCAG).exists():
            data.level = 'Not Identified' if isinstance(data, ConformanceLevel) else 'Select support level'
            data.remark = 'Automated test was not run'
            data.save()
            continue

        if type(data) == ConformanceLevel:
            data.issues.clear()
            for affecting_issue in affecting_issues:
                data.issues.add(affecting_issue)

        tests_with_fail_status = tests_for_sc.filter(status='FAIL')
        tests_with_pass_status = tests_for_sc.filter(status='PASS')

        if affecting_issues:
            if (any(test.test_results.issues.filter(priority='Blocker') for test in tests_with_fail_status)
                    or weighted_error_percentage(tests_with_fail_status.union(tests_with_pass_status), WCAG) > 50):
                data.level = 'Does Not Support'
                if isinstance(data, ConformanceLevel):
                    data.remark = ''
                else:
                    data.remark = cached_vpat_data['wcag'][WCAG][data.product_type]['Does Not Support']
            else:
                data.level = 'Supports with Exceptions' if isinstance(data, ConformanceLevel) else 'Partially Supports'
                if isinstance(data, ConformanceLevel):
                    data.remark = ''
                else:
                    data.remark = cached_vpat_data['wcag'][WCAG][data.product_type]['Partially Supports']
        elif tests_with_pass_status:
            data.level = 'Supports'
            if isinstance(data, ConformanceLevel):
                data.remark = ''
            else:
                data.remark = cached_vpat_data['wcag'][WCAG][data.product_type]['Supports']
        else:
            data.level = 'Not Applicable'
            if isinstance(data, ConformanceLevel):
                data.remark = ''
            else:
                data.remark = cached_vpat_data['wcag'][WCAG][data.product_type]['Not Applicable']

        data.save()


def update_success_criteria_level(test_results: TestResults) -> None:
    all_issues = test_results.issues.all()
    all_tests = test_results.test_set.all()
    success_criteria_level_set = SuccessCriteriaLevel.objects.filter(test_results=test_results, product_type='Web')
    update_data_levels(success_criteria_level_set, all_issues, all_tests)


def update_conformance_level(test_results: TestResults) -> None:
    all_issues = test_results.issues.all()
    all_tests = test_results.test_set.all()
    conformance_data_set = ConformanceLevel.objects.filter(test_results=test_results)
    update_data_levels(conformance_data_set, all_issues, all_tests)


def fill_508(section_type: str,
             test_results: TestResults,
             exclude_number: str,
             applicable_chapters: Iterable[str],
             product_types: Iterable[str]) -> None:
    vpat_data = xlsdata.cached_vpat_data
    for chapter in vpat_data[section_type]:
        if chapter in applicable_chapters:
            applicable = True
        else:
            applicable = False
        chapter_model = Section508Chapters.objects.create(
            test_results=test_results,
            report_type=section_type,
            chapter=chapter,
            name=vpat_data[section_type][chapter]['name'],
            applicable=applicable
        )
        if chapter == exclude_number:
            for criteria in vpat_data[section_type][chapter]['criteria']:
                for product in product_types:
                    Section508Criteria.objects.create(
                        chapter=chapter_model,
                        criteria=criteria,
                        product_type=product,
                        level='Select support level',
                        remark=''
                    )
        else:
            for criteria in vpat_data[section_type][chapter]['criteria']:
                Section508Criteria.objects.create(
                    chapter=chapter_model,
                    criteria=criteria,
                    product_type='',
                    level='Select support level',
                    remark=''
                )


def update_level_for_section_chapter(
        test_results: TestResults, section: str, chapter: str, product_type: Optional[str] = 'Web'
) -> None:
    section508chapters__first = test_results.section508chapters_set.filter(
        chapter=chapter, report_type=section, test_results=test_results
    ).first()
    if section508chapters__first is None:
        return
    section_508_criteria_set = section508chapters__first.section508criteria_set.filter(
        product_type=product_type
    )

    criteria_dict = cached_vpat_data[section][chapter]['criteria']

    for criteria in section_508_criteria_set:
        if criteria.criteria not in DEPENDENCY_OF_SECTION_CHAPTER_WCAG[section][chapter]:
            continue

        success_criteria_level_set = SuccessCriteriaLevel.objects.filter(
            test_results=test_results,
            product_type=product_type,
            criteria__in=DEPENDENCY_OF_SECTION_CHAPTER_WCAG[section][chapter][criteria.criteria]
        )

        levels = [
            success_criteria.level
            for success_criteria in success_criteria_level_set
            if success_criteria.level != 'Select support level'
        ]
        if not levels:
            continue
        if all(level == 'Not Applicable' for level in levels):
            criteria.level = 'Not Applicable'
        elif all(level in ('Does Not Support', 'Not Applicable') for level in levels):
            criteria.level = 'Does Not Support'
        elif any(level in ('Partially Supports', 'Does Not Support') for level in levels):
            criteria.level = 'Partially Supports'
        else:
            criteria.level = 'Supports'
        criteria.remark = criteria_dict[criteria.criteria][criteria.product_type][criteria.level]
        fail_success_criteria = success_criteria_level_set.filter(level__in=('Does Not Support', 'Partially Supports'))
        for sc in fail_success_criteria:
            criteria.remark += '\n' + f'<b>{cached_wcag_table_info[sc.criteria]["name"]}</b>'
        criteria.save()


def percentage_of_problem_elements(test: Test) -> float:
    number_of_checked_elements = len(list(filter(None, test.checked_elements.split('\n'))))
    return 100 * test.example_set.count() / number_of_checked_elements if number_of_checked_elements else 0.


def weighted_error_percentage(tests: Union[QuerySet, List[Test]], wcag: str) -> float:
    for test in tests:
        if test.name not in cached_wcag_test_matching[wcag]:
            cached_wcag_test_matching[wcag][test.name] = {'weight': 1, 'percent': 50}
    try:
        percentage = sum(
            cached_wcag_test_matching[wcag][test.name]['weight'] *
            cached_wcag_test_matching[wcag][test.name]['percent'] * percentage_of_problem_elements(test)
            for test in tests
        ) / sum(
            cached_wcag_test_matching[wcag][test.name]['weight'] *
            cached_wcag_test_matching[wcag][test.name]['percent']
            for test in tests
        )
        return percentage
    except ZeroDivisionError:
        return 0.
