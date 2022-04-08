from typing import Optional, List

import django_filters
from django.db.models import QuerySet, F

from web_interface.apps.job.models import Job
from web_interface.apps.project.models import Project


class JobOrderingFilter(django_filters.OrderingFilter):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def filter(self, qs: QuerySet, value: Optional[List[str]]) -> QuerySet:
        if not value:
            return qs

        qs = super().filter(qs, value)

        if 'last_test' in value:
            qs = qs.order_by(F('last_test').asc(nulls_last=True))
        elif '-last_test' in value:
            qs = qs.order_by(F('last_test').desc(nulls_last=True))

        return qs


class ListFilter(django_filters.Filter):
    def filter(self, qs, value):
        if not value:
            return qs

        self.lookup_expr = "in"
        values = value.split(",")
        return super(ListFilter, self).filter(qs, values)


class JobAPIFilter(django_filters.FilterSet):
    project = django_filters.ModelChoiceFilter(queryset=Project.objects.all())
    task_status = ListFilter(field_name="last_task_status", label="Task Status")

    ordering = JobOrderingFilter(
        fields=(
            ("name", "name"),
            ("project__name", "project_name"),
            ("last_task_status", "task_status"),
            ("last_test", "last_test"),
        ),
    )

    class Meta:
        model = Job
        fields = ("project",)
