from django.contrib import admin

from web_interface.apps.report.models import (
    Issue, Report, SummaryParams, ConformanceLevel, ConformanceLevelIssue,
    VpatReportParams, SuccessCriteriaLevel, Section508Chapters, Section508Criteria,
    IssueLabel
)


admin.site.register(Issue)
admin.site.register(Report)
admin.site.register(VpatReportParams)
admin.site.register(SummaryParams)

admin.site.register(SuccessCriteriaLevel)
admin.site.register(Section508Chapters)
admin.site.register(Section508Criteria)
admin.site.register(ConformanceLevelIssue)
admin.site.register(IssueLabel)


class ConformanceLevelAdmin(admin.ModelAdmin):
    list_display = ('WCAG', 'level', 'test_results')


class TestAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'support_status', 'checked_elements', 'test_results')


admin.site.register(ConformanceLevel, ConformanceLevelAdmin)
