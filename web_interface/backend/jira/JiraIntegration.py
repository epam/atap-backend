import datetime
import re
from typing import List

from jira import JIRA, Issue, JIRAError

from framework.xlsdata import cached_wcag_table_info, get_data_for_issue
from web_interface.apps.issue.models import Example, ExampleScreenshot
from web_interface.apps.jira.models import JiraIntegrationParams
from web_interface.apps.jira.models import JiraRootIssue


class JiraIntegration:
    def __init__(self, jira_integration_params: JiraIntegrationParams, limit: int = 10):
        self.jira_integration_params = jira_integration_params
        self.jira = JIRA(jira_integration_params.host,
                         basic_auth=(jira_integration_params.username, jira_integration_params.token))
        self.limit_of_examples = limit

        self.processed_examples = 0
        self.reopened_issues = 0
        self.created_issues = 0
        self.duplicated_issues = 0

    def __del__(self):
        self.jira.close()

    def create_examples_in_jira(self, examples: List[Example]) -> None:
        for example in examples:
            root_issue = self._get_root_issue(example.err_id, create_issue_if_not_exist=True)
            if self._issue_is_closed(root_issue):
                self._reopen_issue(root_issue)
            if (len(self.jira.issue(root_issue.jira_task_key).fields.subtasks) < self.limit_of_examples
                    and self._task_contains_example(root_issue, example)):
                self._create_sub_task(root_issue, example)
            self.processed_examples += 1

    @staticmethod
    def clean_text(text):
        return re.sub(re.compile('<.*?>'), '', text) if text else ''

    @staticmethod
    def _check_and_update_assignee(issue: Issue) -> None:
        reporter = issue.fields.reporter
        if reporter is None:
            return
        assignee = issue.fields.assignee
        if assignee is None or assignee.accountId != reporter.accountId:
            issue.update(assignee={'accountId': reporter.accountId})
            if issue.fields.assignee.accountId != reporter.accountId:
                raise JIRAError(f'It was not possible to assign a ticket to the user {reporter.displayName}.')

    def _create_jira_issue(self, error_id: str):
        data = get_data_for_issue(error_id)
        reference = '\n'.join([cached_wcag_table_info[wcag]["reference"] for wcag in data['WCAG'].split(", ")
                               if wcag in cached_wcag_table_info])
        fields = [data['intro'], f"*Techniques*:\n{data['techniques']}",
                  f"*Recommendations*:\n{data['recommendations']}",
                  f"*Reference to standards*:\n{self.clean_text(reference)}"]

        issue = self.jira.create_issue(project=self.jira_integration_params.jira_project_key,
                                       summary=data['issue_title'],
                                       description="\n".join(fields),
                                       issuetype={'name': 'Bug'})
        self._check_and_update_assignee(issue)
        self.created_issues += 1
        return issue.key

    def _create_task(self, error_id: str) -> JiraRootIssue:
        issue_key = self._create_jira_issue(error_id)
        return JiraRootIssue.objects.create(jira_integration=self.jira_integration_params,
                                            error_id=error_id,
                                            jira_task_key=issue_key)

    def _get_root_issue(self, error_id: str, create_issue_if_not_exist=False) -> JiraRootIssue:
        task = JiraRootIssue.objects.filter(jira_integration=self.jira_integration_params, error_id=error_id).first()
        if task is None:
            task = self._create_task(error_id)
        elif create_issue_if_not_exist:
            self._create_issue_if_not_exist(task)
        return task

    def _create_sub_task(self, task: JiraRootIssue, example: Example) -> None:
        task.added_examples.add(example)
        task.save()
        issue_type = self.jira.issue_types()[0].name
        summary = f"Example {len(self.jira.issue(task.jira_task_key).fields.subtasks) + 1}"

        description = [f"*Pages*: {', '.join([page.url for page in example.pages.all()])}",
                       f"*Expected result*:\n{self.clean_text(example.expected_result)}",
                       f"*Actual result*:\n{self.clean_text(example.actual_result)}",
                       f"*HTML*:\n _{example.code_snippet}_",
                       f"*PATH*:\n _{example.problematic_element_selector}_"]

        sub_issue = self.jira.create_issue(project=self.jira_integration_params.jira_project_key,
                                           summary=summary,
                                           parent={"key": task.jira_task_key},
                                           description="\n".join(description),
                                           issuetype={'name': issue_type})
        self.created_issues += 1
        screenshots: List[ExampleScreenshot] = ExampleScreenshot.objects.filter(example=example)
        if screenshots:
            for screenshot in screenshots:
                self.jira.add_attachment(issue=sub_issue.key, attachment=screenshot.screenshot,
                                         filename=screenshot.screenshot.url)

        self._check_and_update_assignee(sub_issue)

    @staticmethod
    def _get_status(issue: Issue) -> str:
        return issue.fields.status.name

    def _issue_is_closed(self, task: JiraRootIssue) -> bool:  # issue is 'Done'
        issue = self.jira.issue(task.jira_task_key)
        closed_status = [transition['name'] for transition in self.jira.transitions(issue)][-1]
        return self._get_status(issue) == closed_status

    def _reopen_issue(self, task: JiraRootIssue) -> None:
        issue = self.jira.issue(task.jira_task_key)
        to_do_status = [transition['name'] for transition in self.jira.transitions(issue)][0]
        for subtask in issue.fields.subtasks:
            subtask.delete()
        task.added_examples.clear()
        task.save()
        self.jira.add_comment(issue.key, body=f"The task was reopened on {datetime.date.today()}.")
        self.jira.transition_issue(issue, transition=to_do_status)
        self.reopened_issues += 1

    def _task_contains_example(self, task: JiraRootIssue, example: Example) -> bool:
        if all(e.problematic_element_selector != example.problematic_element_selector
               and e.code_snippet != example.code_snippet for e in task.added_examples.all()):
            return True
        else:
            self.duplicated_issues += 1
            return False

    def _create_issue_if_not_exist(self, task: JiraRootIssue) -> None:
        try:
            self.jira.issue(task.jira_task_key)
        except JIRAError:
            key = self._create_jira_issue(task.error_id)
            task.jira_task_key = key
            task.added_examples.clear()
            task.save()
