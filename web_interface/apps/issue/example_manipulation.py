from typing import Optional

from framework import xlsdata
from web_interface.apps.framework_data.models import Test, AvailableTest
from web_interface.apps.issue.models import Example
from web_interface.apps.report.models import Issue, IssueLabel

ORIG_DATA_TEMPLATE = {
    'priority': 'Major',
    'techniques': '',
    'intro': '',
    'type_of_disability': '',
    'issue_title': 'NEW ISSUE',
    'recommendations': '',
    'WCAG': '1.1.1',
    'issue_type': '',
    'WCAG-BP': 'WCAG',
    'expected_result': '',
    'actual_result': '',
    'groups': [],
    'labels': []
}


def add_labels_to_issue(issue: Issue, labels: Optional[list]) -> None:
    """Add existed labels from metadata to Issue object"""
    for label_name in labels or ():
        issue_label, _ = IssueLabel.objects.get_or_create(name=label_name, read_only=True, test_results=None)
        issue.labels.add(issue_label)


def group_and_annotate(test_results):
    # print('Grouping and annotating')
    examples = Example.objects.prefetch_related('pages').filter(test_results=test_results)
    for example in examples:
        pages = example.pages.all()

        if example.steps is None:
            if pages:
                url = example.pages.first().url
                example.steps = '1. Open the page <a href="' + url + '">' + url + '</a>'
            if len(pages) == 2:
                example.note = (
                        'Also applicable to <a href="' +
                        example.pages.last().url + '">' +
                        example.pages.last().url + '</a>  page'
                )
            elif len(pages) > 2:
                urls = []
                for page in pages[1:]:
                    urls.append('<a href="' + page.url + '">' + page.url + '</a>')
                example.note = 'Also applicable to ' + ', '.join(urls) + ' pages'
        # Don't count examples from passed tests
        try:
            if example.severity != 'FAIL':
                example.save()
                continue
        except AttributeError:
            pass

        # If only WARN issues of this err_id exist, don't create an issue group
        if not Example.objects.filter(test_results=test_results, err_id=example.err_id, severity='FAIL').exists():
            continue
        if 'empty_template' not in example.err_id and '_copy_' not in example.err_id:
            orig_data = xlsdata.get_data_for_issue(example.err_id)
        elif '_copy_' in example.err_id:
            orig_data = xlsdata.get_data_for_issue('_'.join(example.err_id.split('_')[0:-2]))
        else:
            orig_data = ORIG_DATA_TEMPLATE
        references = ''
        for paragraph in orig_data['WCAG'].split(', '):
            try:
                references += '<p>' + xlsdata.cached_wcag_table_info[paragraph]['reference'] + '</p>'
            except KeyError:
                pass

        issue, created = Issue.objects.get_or_create(
            err_id=example.err_id,
            test_results=test_results,
            defaults={
                'priority': orig_data['priority'],
                'techniques': get_techniques_as_links(orig_data['techniques']),
                'intro': orig_data['intro'],
                'type_of_disability': orig_data['type_of_disability'],
                'name': orig_data['issue_title'],
                'references': references,
                'recommendations': orig_data['recommendations'],
                'wcag': orig_data['WCAG'],
                'issue_type': orig_data['issue_type'],
                'is_best_practice': orig_data['WCAG-BP'] == 'BP' if not example.force_best_practice else True
            }
        )
        if created or not issue.labels.count():
            add_labels_to_issue(issue=issue, labels=orig_data['labels'])

        example.issue = issue

        example.save()


def get_techniques_as_links(techniques):
    techniques = techniques.split('\n')
    techniques_links = list()
    for technique in techniques:
        techniques_links.append('<a title="' + technique + '" href="' + technique + '">' + technique + '</a>')
    return '\n'.join(techniques_links)


def get_available_problem_types() -> tuple:
    problem_types_WCAG = []
    problem_types_BP = []
    test_names = AvailableTest.objects.all().values_list("name", flat=True)
    for key, value in xlsdata.cached_problem_type_data.items():
        if key.startswith("test_") and key not in test_names:
            continue
        issue_type = {
            'err_id': key,
            'name': value['issue_title'],
            'WCAG': value['WCAG'],
            'expected_result': value['expected_result'],
            'actual_result': value['actual_result'],
            'type_of_disability': value['type_of_disability'],
            'techniques': value['techniques'],
            'recommendations': value['recommendations'],
            'labels': value['labels'],
            'priority': value['priority'],
            'intro': value['intro']
        }
        if value['WCAG-BP'] == 'WCAG':
            problem_types_WCAG.append(issue_type)
        else:
            problem_types_BP.append(issue_type)

    return sorted(problem_types_WCAG, key=lambda k: k['WCAG']), sorted(problem_types_BP, key=lambda k: k['WCAG'])


def create_issue_obj_from_metadata(err_id, task, force_best_practice):
    orig_data = get_original_data(err_id)
    references = ''
    for paragraph in orig_data['WCAG'].split(', '):
        try:
            references += '<p>' + xlsdata.cached_wcag_table_info[paragraph]['reference'] + '</p>'
        except KeyError:
            pass

    issue = Issue.objects.create(
        err_id=err_id,
        test_results=task.test_results,
        priority=orig_data['priority'],
        techniques=get_techniques_as_links(orig_data['techniques']),
        intro=orig_data['intro'],
        type_of_disability=orig_data['type_of_disability'],
        name=orig_data['issue_title'],
        references=references,
        recommendations=orig_data['recommendations'],
        wcag=orig_data['WCAG'],
        issue_type=orig_data['issue_type'],
        is_best_practice=orig_data['WCAG-BP'] == 'BP' if force_best_practice is None else force_best_practice
    )

    add_labels_to_issue(issue=issue, labels=orig_data['labels'])
    return issue


def add_example_to_issue(issue):
    err_id = issue.err_id
    orig_data = get_original_data(err_id)

    if 'test_' in err_id or err_id == 'empty_template':
        test_name = err_id
    else:
        test_name = xlsdata.cached_wcag_test_matching[orig_data['WCAG']][issue.err_id]['test']
    if test_name == '':
        test_name = err_id
    test = Test.objects.get(name=test_name, test_results=issue.test_results)

    example = Example.objects.create(
        err_id=err_id,
        test=test,
        severity='FAIL',
        issue=issue,
        test_results=issue.test_results,
        expected_result=orig_data['expected_result'],
        actual_result=orig_data['actual_result']
    )
    return example


def get_original_data(err_id):
    orig_data = ORIG_DATA_TEMPLATE
    if 'empty_template' not in err_id:
        orig_data = xlsdata.get_data_for_issue(err_id)
    return orig_data


def find_issue_for_warn(err_id, is_best_practice, task):
    orig_data = get_original_data(err_id)
    issues = Issue.objects.filter(test_results=task.test_results,
                                  is_best_practice=is_best_practice,
                                  err_id=err_id,
                                  name=orig_data['issue_title'])
    return issues.first()


def create_new_issue(err_id, task, force_best_practice=False):
    orig_data = get_original_data(err_id)
    try:
        if 'test_' in err_id:
            test_name = err_id
        else:
            test_name = xlsdata.cached_wcag_test_matching[orig_data['WCAG']][err_id]['test']
    except KeyError:
        test_name = err_id
    test_name = test_name if test_name != '' else err_id

    try:
        test, created = Test.objects.get_or_create(
            name=test_name,
            test_results=task.test_results,
            defaults={
                'status': 'FAIL',
                'support_status': '',
                'checked_elements': '',
                'problematic_pages': '',
                'manually': True,
            }
        )
        print(test.name)
    except Test.MultipleObjectsReturned:
        test = Test.objects.filter(name=test_name, test_results=task.test_results).first()
        created = False

    if not created:
        test.status = 'FAIL'
        test.save()

    issue = create_issue_obj_from_metadata(err_id, task, force_best_practice)
    return issue
