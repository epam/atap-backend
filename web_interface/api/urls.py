from django.urls import path, include
from rest_framework.routers import DefaultRouter

from web_interface import yasg_urls
from web_interface.api.activity.views import ActivityViewSet
from web_interface.api.auth.views import CustomAuthToken, CheckerAPIKeyViewSet
from web_interface.api.auth_user.views import AuthUserAPIView, ChangePasswordAPIView
from web_interface.api.ci_plugin.views import CIPluginJobViewSet, CIPluginTaskViewSet
from web_interface.api.example.views import ExampleViewSet, IssueViewSet, ExampleScreenshotViewSet
from web_interface.api.framework_data.views import (
    TestResultsViewSet,
    AvailableTestViewSet,
    AvailableTestGroupViewSet,
    TestTimingView,
)
from web_interface.api.helpers.views import (
    UrlValidationAPIView,
    FrameworkMetadataAPIView,
    ApplicationInfoAPIView,
    MetaDataForIssueAPIView,
    AuthValidationAPIView,
)
from web_interface.api.job.views import JobViewSet
from web_interface.api.page.views import PageViewSet
from web_interface.api.project.views import ProjectViewSet
from web_interface.api.report.views import (
    VPATReportViewSet,
    AuditReportViewSet,
    IssueLabelViewSet,
    SuccessCriteriaLevelViewSet,
    Section508ChaptersViewSet,
    Section508CriteriaViewSet,
    ConformanceLevelViewSet,
    ExampleScreenshotView,
)
from web_interface.api.task.views import TaskViewSet, TaskReportsViewSet, SitemapTaskViewSet
from web_interface.api.task_planner.views import PlannedTaskViewSet
from web_interface.api.jira.views import JiraIntegrationParamViewSet, JiraValidationAPIView

router = DefaultRouter()
router.register("pages", PageViewSet, basename="pages")
router.register("activities", ActivityViewSet, basename="activities")
router.register("jobs", JobViewSet, basename="jobs")
router.register("projects", ProjectViewSet, basename="projects")
router.register("tasks", TaskViewSet, basename="tasks")
router.register("sitemap_tasks", SitemapTaskViewSet, basename="sitemap-tasks")
router.register("task_reports", TaskReportsViewSet, basename="task-reports")
router.register("success_criteria_levels", SuccessCriteriaLevelViewSet, basename="success-criteria-levels")
router.register("section_508_chapters", Section508ChaptersViewSet, basename="section-508-chapters")
router.register("section_508_criteria", Section508CriteriaViewSet, basename="section-508-criteria")
router.register("issue_label", IssueLabelViewSet, basename="issue-label")
router.register("audit_reports", AuditReportViewSet, basename="audit-reports")
router.register("test_results", TestResultsViewSet, basename="test-results")
router.register("available_test", AvailableTestViewSet, basename="available-test")
router.register("available_test_group", AvailableTestGroupViewSet, basename="available-test-group")
router.register("test_timing", TestTimingView, basename="test-timing")
router.register("issue", IssueViewSet, basename="issue")
router.register("example", ExampleViewSet, basename="example")
router.register("example_screenshot", ExampleScreenshotViewSet, basename="example-screenshot")
router.register("api_key", CheckerAPIKeyViewSet, basename="api-key")
router.register("ci_plugin_job", CIPluginJobViewSet, basename="ci-plugin-job")
router.register("ci_plugin_task", CIPluginTaskViewSet, basename="ci-plugin-task")
router.register("conformance_levels", ConformanceLevelViewSet, basename="conformance-levels")
router.register("task_planner", PlannedTaskViewSet, basename="task-planner")
router.register("jira_integration", JiraIntegrationParamViewSet, basename="jira-integration")

urlpatterns = [
    path("", include((router.urls, "api"))),
    path("doc/", include(yasg_urls)),
    path("api-token-auth/", CustomAuthToken.as_view(), name="api-token-auth"),
    path("auth-user/", AuthUserAPIView.as_view(), name="api-auth-user"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="api-change-password"),
    path("url-validation/", UrlValidationAPIView.as_view(), name="api-url-validation"),
    path("auth-validation/", AuthValidationAPIView.as_view(), name="api-auth-validation"),
    path("api-application-info/", ApplicationInfoAPIView.as_view(), name="api-application-info"),
    path("framework-metadata/", FrameworkMetadataAPIView.as_view(), name="api-framework-metadata"),
    path("metadata-for-issue/<str:err_id>/", MetaDataForIssueAPIView.as_view(), name="api-metadata-for-issue"),
    path("show_example_screenshot/<int:id>/", ExampleScreenshotView.as_view(), name="show-example-screenshot"),
    # path('vpat-report/', VPATReportViewSet.as_view({'get': 'list'}), name='api-vpat-report'),
    path(
        "vpat-report/<int:task_pk>/<int:vpat_report_pk>/",
        VPATReportViewSet.as_view({"get": "retrieve"}),
        name="api-vpat-report-detail",
    ),
    path("jira-validation/", JiraValidationAPIView.as_view(), name="api-jira-validation"),
]
