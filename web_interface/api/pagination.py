from collections import OrderedDict

from rest_framework import pagination
from rest_framework.response import Response


class PageNumberPaginationExtended(pagination.PageNumberPagination):

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('current_page', self.page.number),
            ('total_pages', self.page.paginator.num_pages),
            ('results', data)
        ]))

    def get_paginated_response_schema(self, schema):
        paginated_response_schema = super().get_paginated_response_schema(schema)
        paginated_response_schema['properties'].update(
            {
                'current_page': {
                    'type': 'integer',
                    'example': 123,
                },
                'total_pages': {
                    'type': 'integer',
                    'example': 123
                }
            }
        )
        return paginated_response_schema
