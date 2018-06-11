#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import unicodecsv as csv
import pprint

from six import BytesIO
from rest_framework import renderers


logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4)


class SupplyLogCSVRenderer(renderers.BaseRenderer):
    media_type= '*/*'
    format="csv"
    headers = ['ID', 'Supply ID', 'Supply', 'Employee ID', 'Employee', 
               'Acknowledgement', 'Customer', 'Message', 'Action Type', 
               'Quantity', 'Cost', 'Timestamp']

    def render(self, data, media_type=None, renderer_context=None):
        """Render method

        Renders the log data from supply out to CSV.
        """
        # Set the content disposition so that 
        # the file downloads instead of displays
        renderer_context = renderer_context or {}
        response = renderer_context.get('response')
        response['Content-Disposition'] = 'attachment; filename="supply-log.csv"'

        csv_buffer = BytesIO()
        csv_writer = csv.writer(csv_buffer, encoding='utf-8') 
        csv_writer.writerow(self.headers)
        for row in [self._process_row(rd) for rd in data]:
            csv_writer.writerow(row)

        return csv_buffer.getvalue()

    def _process_row(self, data):
        data_to_return = []
        for k in data:
            if k.lower() == "supply" and data[k]:
                data_to_return.append(data[k]["id"])
                data_to_return.append(data[k]["description"])
            elif k.lower() == "employee" and data[k]:
                data_to_return.append(data[k]["id"])
                data_to_return.append(data[k]["name"])
            elif k.lower() == "employee" and data[k]:
                data_to_return.append(data[k]["id"])
                data_to_return.append(data[k]["customer"]["name"])
            elif k.lower() in ['employee', 'supply', 'acknowledgement'] and not data[k]:
                data_to_return.append('')
                data_to_return.append('')
            else: 
                data_to_return.append(data[k])

        return data_to_return