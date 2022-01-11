import re
from datetime import date

from django.db import transaction, models
from django.db.models import IntegerField, Prefetch, Subquery
from django.db.models.functions import Cast
from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend, DateTimeFromToRangeFilter, FilterSet
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, filters, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.views import APIView

from framework import xlsdata
from wcag_information.levels_and_versions import TABLE_A, TABLE_AA, TABLE_AAA, WCAG_A_2_1, WCAG_AA_2_1
from web_interface.api.project.permissions import get_available_projects
from web_interface.api.report.audit_report_xlsx import AuditReportExportXLSX
from web_interface.api.report.serializers import (
    VpatReportParamsSerializer, AuditReportSerializer, IssueLabelSerializer,
    SuccessCriteriaLevelSerializer, Section508ChaptersSerializer, Section508CriteriaSerializer,
    AuditReportPagesSerializer, ConformanceLevelSerializer, ExampleScreenshotSerializer
)
from web_interface.apps.issue.models import Example, ExampleScreenshot
from web_interface.apps.job.models import Job
from web_interface.apps.page.models import Page
from web_interface.apps.report.models import (
    VpatReportParams, SuccessCriteriaLevel, Section508Chapters, Section508Criteria, ConformanceLevel, Issue, IssueLabel
)
from web_interface.apps.task.models import Task


class SuccessCriteriaLevelViewSet(viewsets.ModelViewSet):
    queryset = SuccessCriteriaLevel.objects.order_by('pk')
    serializer_class = SuccessCriteriaLevelSerializer


class Section508ChaptersViewSet(viewsets.ModelViewSet):
    queryset = Section508Chapters.objects.order_by('pk')
    serializer_class = Section508ChaptersSerializer


class Section508CriteriaViewSet(viewsets.ModelViewSet):
    queryset = Section508Criteria.objects.order_by('pk')
    serializer_class = Section508CriteriaSerializer


class IssueLabelViewSet(viewsets.ModelViewSet):
    queryset = IssueLabel.objects.order_by('pk')
    serializer_class = IssueLabelSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['read_only', 'test_results']


class ReportsFilter(FilterSet):
    date_started = DateTimeFromToRangeFilter()

    class Meta:
        model = Task
        fields = ['date_started', 'target_job__name']


class AuditReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Task.objects.prefetch_related(
        Prefetch('test_results__conformancelevel_set',
                 queryset=ConformanceLevel.objects.prefetch_related('issues'),
                 to_attr='prefetched_conformance_levels')
    ).order_by('pk')
    serializer_class = AuditReportSerializer
    prefetched_issues_query_fields = {
        'label_id': 'labels__pk__in',
        'priority': 'priority__in'
    }

    def prefetch_filter_queryset(self, queryset):
        """Filter queryset prefetched issue field"""
        query_params = self.request.query_params
        filter_kwargs = {}
        for field, values in query_params.items():
            lookup_field = self.prefetched_issues_query_fields.get(field, None)
            values = values.split(',') if values else None
            if lookup_field and values:
                filter_kwargs[lookup_field] = values
        queryset = queryset.prefetch_related(
            Prefetch('test_results__issues',
                     queryset=Issue.objects.prefetch_related('labels', 'examples').filter(**filter_kwargs),
                     to_attr='prefetched_issues')
        )
        return queryset

    def filter_queryset(self, queryset):
        queryset = queryset.filter(target_job__project__in=get_available_projects(self.request.user))
        queryset = self.prefetch_filter_queryset(queryset)
        return super().filter_queryset(queryset)

    @swagger_auto_schema(responses={status.HTTP_200_OK: AuditReportPagesSerializer})
    @action(methods=['GET'], detail=True)
    def pages(self, request, pk=None):
        instance = self.get_object()
        example_qs = Example.objects.filter(test_results=instance.test_results)
        queryset = Page.objects.filter(example__id__in=Subquery(example_qs.values('id')))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AuditReportPagesSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AuditReportPagesSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=no_body, responses={status.HTTP_200_OK: 'File response in .xlsx format'})
    @action(methods=['GET'], detail=True)
    def download_as_xlsx(self, request, pk=None):
        instance = self.get_object()
        # TODO needs optimization
        issues_ids = [issue.id for issue in instance.test_results.prefetched_issues]
        items = Example.objects.select_related('issue').filter(
            issue_id__in=issues_ids, severity='FAIL'
        ).order_by('issue__is_best_practice')

        d = instance.date_started if instance.date_started is not None else date.today()
        file_name = f'Report_{instance.target_job.project.name}_{instance.target_job.name}_{d.year}-{d.month}-{d.day}'
        file_name = re.sub(r'[^a-zA-Z0-9_ \-\.]', '', file_name)

        response = AuditReportExportXLSX(
            items=items,
            worksheet_name='Issues',
            file_name=file_name,
            request=self.request
        ).render()
        return response


class ConformanceLevelViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = ConformanceLevelSerializer
    queryset = ConformanceLevel.objects.all()


class ExampleScreenshotView(APIView):
    @swagger_auto_schema(responses={status.HTTP_200_OK: ExampleScreenshotSerializer})
    def get(self, request, id):
        example_screenshot = ExampleScreenshot.objects.get(id=id)
        if not example_screenshot or example_screenshot.example.issue.task.target_job.project not in get_available_projects(request.user):
            raise Http404
        filename = request.GET.get('filename', example_screenshot.screenshot.url)
        html = f'<html><body><img src="{example_screenshot.screenshot.url}"><br><a download="{filename}" ' \
               f'href="{example_screenshot.screenshot.url}">Download</a></body></html>'
        return HttpResponse(html)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class VPATReportViewSet(ViewSet):
    serializer = VpatReportParamsSerializer

    @swagger_auto_schema(responses={status.HTTP_200_OK: VpatReportParamsSerializer})
    def retrieve(self, request, task_pk, vpat_report_pk):
        job = Job.objects.filter(task__pk=task_pk, vpatreportparams__pk=vpat_report_pk)
        if not job.exists() or job.get().project not in get_available_projects(request.user):
            raise Http404
        vpat_data = xlsdata.cached_vpat_data
        with transaction.atomic():
            vpat_report_params = VpatReportParams.objects.get(pk=vpat_report_pk)
            task = Task.objects.get(pk=task_pk)
            wcag_levels = SuccessCriteriaLevel.objects.filter(test_results_id=task.test_results_id).order_by('criteria')
            wcag_keys = list(wcag_levels.values_list('criteria', flat=True))
            wcag_keys = list(dict.fromkeys(wcag_keys))  # delete duplicates
            wcag_keys = sorted(
                wcag_keys,
                key=lambda x: (int(x.split('.')[0]), int(x.split('.')[1]), int(x.split('.')[2]))
            )
            wcag = {'A': [], 'AA': [], 'AAA': []}
            order = ('Web', 'Electronic Docs', 'Software', 'Authoring Tool', 'Closed')
            whens = [
                models.When(product_type=value, then=sort_index)
                for sort_index, value in enumerate(order)
            ]
            levels_fields = ('id', 'criteria', 'level', 'product_type', 'remark', 'support_level', 'test_results_id')
            for key in wcag_keys:
                if key in TABLE_A or (key in WCAG_A_2_1 and 'WCAG 2.1 A' in vpat_report_params.standart):
                    levels = SuccessCriteriaLevel.objects.filter(
                        test_results_id=task.test_results_id, criteria=key,
                        product_type__in=vpat_report_params.product_types
                    ).annotate(_sort_index=models.Case(*whens, output_field=models.IntegerField()))
                    levels = levels.order_by('_sort_index')
                    wcag['A'].append(
                        {
                            'number': key,
                            'title': vpat_data['wcag'][key]['title'],
                            'levels': levels.values(*levels_fields)
                        }
                    )
                if key in TABLE_AA or (key in WCAG_AA_2_1 and 'WCAG 2.1 AA' in vpat_report_params.standart):
                    levels = SuccessCriteriaLevel.objects.filter(
                        test_results_id=task.test_results_id, criteria=key,
                        product_type__in=vpat_report_params.product_types
                    ).annotate(_sort_index=models.Case(*whens, output_field=models.IntegerField()))
                    levels = levels.order_by('_sort_index')
                    wcag['AA'].append(
                        {
                            'number': key,
                            'title': vpat_data['wcag'][key]['title'],
                            'levels': levels.values(*levels_fields)
                        }
                    )
                if key in TABLE_AAA:
                    levels = SuccessCriteriaLevel.objects.filter(
                        test_results_id=task.test_results_id, criteria=key,
                        product_type__in=vpat_report_params.product_types
                    ).annotate(_sort_index=models.Case(*whens, output_field=models.IntegerField()))
                    levels = levels.order_by('_sort_index')
                    wcag['AAA'].append(
                        {
                            'number': key,
                            'title': vpat_data['wcag'][key]['title'],
                            'levels': levels.values(*levels_fields)
                        }
                    )

            section_chapters = Section508Chapters.objects.filter(
                test_results_id=task.test_results_id
            ).annotate(chapter_as_integer=Cast('chapter', IntegerField())).order_by('chapter_as_integer')
            chapters_508 = []
            chapters_EN = []
            product_types = vpat_report_params.product_types + ['']
            whens = [
                models.When(product_type=value, then=sort_index)
                for sort_index, value in enumerate(order + ('',))
            ]
            for chapter in section_chapters:
                chapters_criteria = Section508Criteria.objects.filter(chapter=chapter).order_by('criteria')
                chapters_keys = list(chapters_criteria.values_list('criteria', flat=True))
                chapters_keys = list(dict.fromkeys(chapters_keys))  # delete duplicates
                criteria = []
                for key in chapters_keys:
                    levels = Section508Criteria.objects.filter(
                        chapter=chapter, criteria=key, product_type__in=product_types
                    ).annotate(_sort_index=models.Case(*whens, output_field=models.IntegerField()))
                    levels = levels.order_by('_sort_index')
                    criteria.append(
                        {
                            'criteria': key,
                            'levels': levels.values('id', 'chapter_id', 'criteria', 'level', 'product_type', 'remark')
                        }

                    )
                if chapter.report_type == '508':
                    chapters_508.append(
                        {'id': chapter.id,
                         'note': chapter.note,
                         'number': chapter.chapter,
                         'title': chapter.name,
                         'criteria': criteria}
                    )
                else:
                    chapters_EN.append(
                        {'id': chapter.id,
                         'note': chapter.note,
                         'number': chapter.chapter,
                         'title': chapter.name,
                         'criteria': criteria}
                    )
        serializer = self.serializer(
            vpat_report_params,
            context=dict(
                test_results=task.test_results_id,
                wcag=wcag,
                chapters_508=chapters_508,
                chapters_EN=chapters_EN
            )
        )
        return Response(serializer.data)
