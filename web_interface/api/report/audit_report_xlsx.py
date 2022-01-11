from functools import reduce
from typing import Optional

import xlsxwriter
from bs4 import BeautifulSoup
from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import force_text
from xlsxwriter.compatibility import num_types, str_types
from xlsxwriter.utility import supported_datetime


class ExtendedCell:
    def __init__(self, value, cell_format=None, action=None):
        self.value = value
        self.cell_format = cell_format
        self.action = action

    def perform_action(self, obj: Optional['ExportXLSX'] = None):
        if obj:
            return self.action(obj)
        return self.action()


class ExportXLSX:
    row_index = 0
    rows = []
    headers = []
    workbook = None
    worksheet = None
    worksheet_name = None
    file_name = 'report'
    default_formats = {
        'body': {'border': 1},
        'header': {'bold': 1, 'border': 2},
        'percent': {'border': 1, 'num_format': '0%'}
    }
    formats = {}
    cell_formats = {}

    def __init__(self, items=None, headers=None, worksheet_name=None, file_name=None, request=None):
        self.items = items
        if headers:
            self.headers = headers
        if worksheet_name:
            self.worksheet_name = worksheet_name
        if file_name:
            self.file_name = file_name
        formats = self.default_formats.copy()
        formats.update(self.formats)
        self.formats = formats
        self._request = request

    def get_row(self, row):
        return row

    def get_cell(self, data):
        if data is None:
            return data
        if isinstance(data, bool):
            return data
        if isinstance(data, num_types):
            return data
        if isinstance(data, str_types):
            return data
        if supported_datetime(data):
            return data
        return force_text(data)

    def create_formats(self):
        for key, params in self.formats.items():
            self.cell_formats[key] = self.workbook.add_format(params)

    def render_header(self):
        for index, header in enumerate(self.headers):
            self.write(self.row_index, index, header, 'header')
            self.worksheet.set_column(index, index, max(len(header) * 1.2, 8))
        self.row_index += 1

    def render_body(self):
        if not self.items:
            return
        for item in self.items:
            for col_index, cell in enumerate(self.get_row(item)):
                if isinstance(cell, ExtendedCell):
                    if cell.action:
                        cell.perform_action(self)
                        continue
                    cell_format = cell.cell_format
                    cell = cell.value
                else:
                    cell_format = 'body'
                self.write(self.row_index, col_index, cell, cell_format)
            self.row_index += 1

    def render_footer(self):
        return

    def render(self):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{self.file_name}.xlsx"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        response['Cache-Control'] = 'no-cache'

        self.workbook = xlsxwriter.Workbook(response, {'in_memory': True, 'strings_to_urls': False})
        self.worksheet = self.workbook.add_worksheet(self.worksheet_name)

        self.row_index = 0
        self.create_formats()
        self.render_header()
        self.render_body()
        self.render_footer()

        self.workbook.close()

        return response

    def write(self, row, col, data, cell_format=None):
        if cell_format:
            cell_format = self.cell_formats.get(cell_format, None)
        self.worksheet.write(row, col, self.get_cell(data), cell_format)

    def merge_range(self, first_row, first_col, last_row, last_col, data, cell_format=None):
        if cell_format:
            cell_format = self.cell_formats.get(cell_format, None)
        self.worksheet.merge_range(first_row, first_col, last_row, last_col, self.get_cell(data), cell_format)


class AuditReportExportXLSX(ExportXLSX):
    headers = (
        'N',
        'Title',
        'Steps',
        'Expected results',
        'Actual results',
        'Note',
        'Code Snippet',
        'Type of disability',
        'Techniques',
        'Recommendation',
        'Reference to standard',  # auto filter
        'Priority',  # auto filter
        'Page',  # auto filter
        'Screenshot',
        'Label'  # auto filter
    )
    columns_width = {
        'N': 8,
        'Title': 25,
        'Steps': 25,
        'Expected results': 25,
        'Actual results': 25,
        'Note': 15,
        'Code Snippet': 25,
        'Type of disability': 15,
        'Techniques': 15,
        'Recommendation': 25,
        'Reference to standard': 8,
        'Priority': 8,
        'Page': 15,
        'Screenshot': 15,
        'Label': 8
    }
    formats = {
        'body': {'border': 1, 'text_wrap': True, 'valign': 'top'}
    }

    _issue_index = 0
    _issue_best_practice_index = 0
    _example_index = 0
    _example_best_practice_index = 0

    @staticmethod
    def remove_tags(text):
        if not text:
            return ''
        return BeautifulSoup(text, 'lxml').text

    @staticmethod
    def replace_tags(text):
        if not text:
            return ''
        replaces = ('&LT;', '<'), ('&GT;', '>'), ('&gt;', '>'), ('&lt;', '<')
        text = reduce(lambda x, args: x.replace(*args), replaces, text)
        return text.strip()

    def get_absolute_media_url(self, media_url):
        return self._request.build_absolute_uri(settings.MEDIA_URL + media_url)

    def get_show_example_screenshot_url(self, id, number, i):
        return self._request._current_scheme_host + '/api/show_example_screenshot/' + str(id) + f'/?filename={number}.{i}.jpg'

    def get_row(self, item, previous=None):
        # 'N'
        if not item.issue.is_best_practice:
            if previous and previous.issue_id != item.issue_id:
                self._issue_index += 1
                self._example_index = 0
            elif not previous:
                self._issue_index += 1
            self._example_index += 1
            N = f'1.{self._issue_index}.{self._example_index}'
            yield N
        else:
            if previous and previous.issue_id != item.issue_id:
                self._issue_best_practice_index += 1
                self._example_best_practice_index = 0
            elif not previous:
                self._issue_best_practice_index += 1
            self._example_best_practice_index += 1
            N = f'2.{self._issue_best_practice_index}.{self._example_best_practice_index}'
            yield N

        # 'Title'
        yield item.issue.name
        # 'Steps'
        yield self.remove_tags(item.steps)
        # 'Expected results'
        yield self.replace_tags(item.expected_result)
        # 'Actual results'
        yield self.replace_tags(item.actual_result)
        # 'Note'
        yield item.note or ''
        # 'Code Snippet'
        yield item.code_snippet
        # 'Type of disability'
        yield item.issue.type_of_disability
        # 'Techniques'
        yield self.remove_tags(item.issue.techniques)
        # 'Recommendation'
        yield item.recommendations or item.issue.recommendations or ''
        # 'Reference to standard'
        appendix = ('', 'BP, ')[item.issue.is_best_practice]
        wcag = item.issue.wcag
        yield f'{appendix}{wcag}' if wcag else ''
        # 'Priority'
        yield item.issue.priority
        # 'Page'
        yield '\n'.join(item.pages.values_list('url', flat=True))
        # 'Screenshot'
        yield '\n'.join(
            map(self.get_absolute_media_url, item.examplescreenshot_set.values_list('screenshot', flat=True))
        )
        # 'Label'
        yield '\n'.join(item.issue.labels.values_list('name', flat=True))

    def sorting_items(self):
        self.items = list(self.items)
        try:
            self.items = sorted(
                self.items,
                key=lambda x:
                (x.issue.is_best_practice, x.issue.priority, int(x.issue.wcag.split(',')[0].split('.')[0]),
                 int(x.issue.wcag.split(',')[0].split('.')[1]), int(x.issue.wcag.split(',')[0].split('.')[2]),
                 x.issue.err_id, x.order_in_issuegroup, x.id)
            )
        except ValueError:
            pass
        return self.items

    def render_header(self):
        for index, header in enumerate(self.headers):
            self.write(self.row_index, index, header, 'header')
            width = self.columns_width.get(header, max(len(header) * 1.2, 8))
            self.worksheet.set_column(index, index, width)

        self.row_index += 1

    def render_body(self):
        if not self.items:
            return
        self.sorting_items()
        previous = None
        for item in self.items:
            for col_index, cell in enumerate(self.get_row(item, previous)):
                if isinstance(cell, ExtendedCell):
                    if cell.action:
                        cell.perform_action(self)
                        continue
                    cell_format = cell.cell_format
                    cell = cell.value
                else:
                    cell_format = 'body'
                self.write(self.row_index, col_index, cell, cell_format)

            previous = item
            self.row_index += 1

        # set auto filters for columns, see self.headers
        self.worksheet.autofilter(0, 0, self.row_index, len(self.headers) - 1)
