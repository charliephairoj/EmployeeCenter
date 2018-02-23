#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from decimal import *
import math
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import *
from django.db.models import Q, Sum, Max
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.lib.enums import TA_LEFT, TA_CENTER


logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class PayrollPDF(object):
    
    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]

    def __init__(self, payroll=None, start_date=None, end_date=None, *args, **kwargs):

        if payroll:
            self.payroll = payroll
            
        self.start_date = start_date
        self.end_date = end_date
            
        super(PayrollPDF, self).__init__(*args, **kwargs)
        
    def create(self, response=None):
        
        if response is None:
            response = 'Payroll_{0}-{1}.pdf'.format(self.start_date, self.end_date)
            self.filename = response
        
        doc = SimpleDocTemplate(response, 
                                pagesize=landscape(A4), 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        # Get records
        records = self.payroll.pay_records.order_by('employee__department', 'manager_stipend')

        stories.append(self._format_text("Employee Summary",
                                         font_size=30))
        stories.append(Spacer(0, 50))
        stories.append(self._create_primary_employee_summary(records))
        
        stories.append(PageBreak())
        
        stories.append(self._format_text("Employees Paid by Direct Deposit",
                                         font_size=30))
        stories.append(Spacer(0, 50))
        stories.append(self._create_direct_deposit_summary(records))
        
        stories.append(PageBreak())
        
        stories.append(self._format_text("Employees Paid in Cash",
                                         font_size=30))
        stories.append(Spacer(0, 50))
        stories.append(self._create_cash_summary(records))
        
        stories.append(PageBreak())
        
        stories.append(self._format_text("Employees in Cambodia",
                                         font_size=30))
        stories.append(Spacer(0, 50))
        stories.append(self._create_cambodia_summary(records))
        
        stories.append(PageBreak())
        
        stories.append(self._format_text("Employees in Thailand",
                                         font_size=30))
        stories.append(Spacer(0, 50))
        stories.append(self._create_thailand_summary(records))
        
        stories.append(PageBreak())
        
        stories.append(self._format_text("Attendance Summary",
                                         font_size=30))
        stories.append(Spacer(0, 50))
        stories.append(self._create_employee_attendance(records))
        
        doc.build(stories)
        
    def _create_primary_employee_summary(self, records):
        """Build an employee summary of pay records
        """
        total_gross = 0
        total_ss = 0
        total_net = 0
        index = 0
        
        current_department = None
        data = [['ID', 'Name', 'Department', 'Regular Days', 'OT Hours', 'Pay Rate', 'Gross Wage', 'Stipend', 'Manager', 'Social Security', 'Net Wage']]
        style_data = [('FONTSIZE', (0,0),(-1,0), 10),
                      ('FONT', (0,0), (-1,-1), 'Garuda'),
                      ('PADDING', (0, 0), (-1, -1), 0),
                      ('SPAN', (0, 1), (-1, 1)),
                      ('FONTSIZE', (0, 1),(-1, 1), 10),
                      ('ALIGNMENT', (0, 1), (-1, 1), 'CENTER'),
                      ('ALIGNMENT', (3, 1), (-1, -1), 'RIGHT'),
                      ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                      ('GRID', (0, 0), (-1, -5),  1, colors.CMYKColor(black=60))]
        row_heights = [40]
        
        for record in records:

            if record.employee.department != current_department:
                # Increase row count
                index += 1
                
                # Add new department subheader
                current_department = record.employee.department
                data.append([current_department, '', '', '', '', '', '', '', '', ''])
                
                # Set style and row height for subheader
                style_data += [('SPAN', (0, index), (-1, index)),
                               ('FONTSIZE', (0, index), (-1, index), 10),
                               ('ALIGNMENT', (0, index), (-1, index), 'CENTER')]
                               #('PADDING', (0, index + 2), (-1, index + 2), 10)]
                row_heights.append(30)
                                
            # Add data row to the array
            data.append([record.employee.id, 
                         record.employee.name,
                         record.employee.department,
                         "{0:,.2f}".format(record.regular_hours / Decimal('8')),
                         "{0:,.2f}".format(record.overtime_hours),
                         "{0:,.2f}".format(record.employee.wage),
                         "{0:,.2f}".format(record.gross_wage),
                         "{0:,.2f}".format(record.stipend),
                         "{0:,.2f}".format(record.manager_stipend),
                         "{0:,.2f}".format(record.social_security_withholding),
                         "{0:,.2f}".format(record.net_wage)])

            # Set row height
            row_heights.append(14)
            
            # Add totals
            total_gross += record.gross_wage + record.stipend + record.manager_stipend
            total_ss += record.social_security_withholding
            total_net += record.net_wage
            
            # Increase row count
            index += 1
            
        # Add total summary to bottom of data
        data += [['', ''],
                 ['Gross Wage + Stipend Total', '', '', total_gross],
                 ['Social Security Total', '', '',total_ss],
                 ['Net Wage Total', '', '', total_net]]
        
        total_rows = len(data)
        style_data += [('SPAN', (0, total_rows - 4), (2, total_rows - 4)),
                       ('SPAN', (0, total_rows - 3), (2, total_rows - 3)),
                       ('SPAN', (0, total_rows - 2), (2, total_rows - 2)),
                       ('SPAN', (0, total_rows - 1), (2, total_rows - 1))]
                                   
        row_heights += [20, 20, 20, 20]
        
        # Create and style table             
        table = Table(data, rowHeights=row_heights, repeatRows=1)
        style = TableStyle(style_data)
        
        table.setStyle(style)
        
        return table
        
    def _create_direct_deposit_summary(self, records):
        """Build an employee summary for direct deposit
        """
        # Filter records for direct deposit only
        records = records.filter(employee__payment_option='direct deposit')
        
        total_gross = 0
        total_ss = 0
        total_net = 0
        index = 0
        
        current_department = None
        data = [['ID', 'Name', 'Department', 'Net Wage', 'Bank', "Account Number", "Location"]]
        style_data = [('FONTSIZE', (0,0),(-1,0), 16),
                      ('FONT', (0,0), (-1,-1), 'Garuda'),
                      ('SPAN', (0, 1), (-1, 1)),
                      ('FONTSIZE', (0, 1),(-1, 1), 14),
                      ('ALIGNMENT', (0, 1), (-1, 1), 'CENTER'),
                      ('PADDING', (0, 0), (-1, -1), 10),
                      ('ALIGNMENT', (3, 1), (-1, -1), 'RIGHT'),
                      ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                      ('GRID', (0, 0), (-1, -5),  1, colors.CMYKColor(black=60))]
        row_heights = [40]
        
        for record in records:
            if record.employee.department != current_department:
                # Increase row count
                index += 1
                
                current_department = record.employee.department
                data.append([current_department])
                style_data += [('SPAN', (0, index), (-1, index)),
                               ('FONTSIZE', (0, index), (-1, index), 14),
                               ('ALIGNMENT', (0, index), (-1, index), 'CENTER')]
                               #('PADDING', (0, index + 2), (-1, index + 2), 10)]
                row_heights.append(30)
                
            data.append([record.employee.id, 
                         record.employee.name,
                         record.employee.department,
                         record.net_wage,
                         record.employee.bank,
                         record.employee.account_number,
                         record.employee.location])
            row_heights.append(14)

            # Add totals
            total_gross += record.gross_wage + record.stipend + record.manager_stipend
            total_ss += record.social_security_withholding
            total_net += record.net_wage
            
            # Increase row count
            index += 1
            
        # Add total summary to bottom of data
        data += [['', ''],
                 ['Gross Wage + Stipend Total', '', '', total_gross],
                 ['Social Security Total', '', '',  total_ss],
                 ['Net Wage Total', '', '', total_net]]
        
        total_rows = len(data)
        style_data += [('SPAN', (0, total_rows - 4), (2, total_rows - 4)),
                       ('SPAN', (0, total_rows - 3), (2, total_rows - 3)),
                       ('SPAN', (0, total_rows - 2), (2, total_rows - 2)),
                       ('SPAN', (0, total_rows - 1), (2, total_rows - 1))]
                       
        row_heights += [20, 20, 20, 20]
        
        table = Table(data, rowHeights=row_heights)
        style = TableStyle(style_data)
        
        table.setStyle(style)
        
        return table
        
    def _create_cash_summary(self, records):
        """Build an employee summary for cash
        """
        # Filter records for direct deposit only
        records = records.filter(employee__payment_option='cash')
        
        total_gross = 0
        total_ss = 0
        total_net = 0
        index = 0
        
        current_department = None
        data = [['ID', 'Name', 'Department', 'Net Wage', "Location"]]
        style_data = [('FONTSIZE', (0,0),(-1,0), 16),
                      ('FONT', (0,0), (-1,-1), 'Garuda'),
                      ('SPAN', (0, 1), (-1, 1)),
                      ('FONTSIZE', (0, 1),(-1, 1), 14),
                      ('ALIGNMENT', (0, 1), (-1, 1), 'CENTER'),
                      ('PADDING', (0, 0), (-1, -1), 10),
                      ('ALIGNMENT', (3, 1), (-1, -1), 'RIGHT'),
                      ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                      ('GRID', (0, 0), (-1, -5),  1, colors.CMYKColor(black=60))]
        row_heights = [40]
        
        for record in records:
            if record.employee.department != current_department:
                # Increase row count 
                index += 1
                
                current_department = record.employee.department
                data.append([current_department])
                style_data += [('SPAN', (0, index), (-1, index)),
                               ('FONTSIZE', (0, index), (-1, index), 14),
                               ('ALIGNMENT', (0, index), (-1, index), 'CENTER')]
                               #('PADDING', (0, index + 2), (-1, index + 2), 10)]
                row_heights.append(30)
                
            data.append([record.employee.id, 
                         record.employee.name,
                         record.employee.department,
                         record.net_wage,
                         record.employee.location])
            row_heights.append(14)
            
            # Add totals
            total_gross += record.gross_wage + record.stipend + record.manager_stipend
            total_ss += record.social_security_withholding
            total_net += record.net_wage
            
            # Increase row count
            index += 1

        # Add total summary to bottom of data
        data += [['', ''],
                 ['Gross Wage + Stipend Total', '', '', total_gross],
                 ['Social Security Total', '', '',  total_ss],
                 ['Net Wage Total', '', '', total_net]]
        
        total_rows = len(data)
        style_data += [('SPAN', (0, total_rows - 4), (2, total_rows - 4)),
                       ('SPAN', (0, total_rows - 3), (2, total_rows - 3)),
                       ('SPAN', (0, total_rows - 2), (2, total_rows - 2)),
                       ('SPAN', (0, total_rows - 1), (2, total_rows - 1))]
                       
        row_heights += [20, 20, 20, 20]
        
        table = Table(data, rowHeights=row_heights)
        style = TableStyle(style_data)
        
        table.setStyle(style)
        
        return table
        
    def _create_cambodia_summary(self, records):
        """Build an employee summary for direct deposit
        """
        # Filter records for direct deposit only
        records = records.filter(employee__location='cambodia')
        
        total_gross = 0
        total_ss = 0
        total_net = 0
        index = 0
        
        current_department = None
        data = [['ID', 'Name', 'Department', 'Net Wage', 'Payment', 'Bank', "Account Number", "Location"]]
        style_data = [('FONTSIZE', (0,0),(-1,0), 16),
                      ('FONT', (0,0), (-1,-1), 'Garuda'),
                      ('SPAN', (0, 1), (-1, 1)),
                      ('FONTSIZE', (0, 1),(-1, 1), 14),
                      ('ALIGNMENT', (0, 1), (-1, 1), 'CENTER'),
                      ('PADDING', (0, 0), (-1, -1), 10),
                      ('ALIGNMENT', (3, 1), (-1, -1), 'RIGHT'),
                      ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                      ('GRID', (0, 0), (-1, -5),  1, colors.CMYKColor(black=60))]
        row_heights = [40]
        
        for record in records:
            if record.employee.department != current_department:
                # Increase row count 
                index += 1
                current_department = record.employee.department
                data.append([current_department])
                style_data += [('SPAN', (0, index), (-1, index)),
                               ('FONTSIZE', (0, index), (-1, index), 14),
                               ('ALIGNMENT', (0, index), (-1, index), 'CENTER')]
                               #('PADDING', (0, index + 2), (-1, index + 2), 10)]
                row_heights.append(30)
                
            data.append([record.employee.id, 
                         record.employee.name,
                         record.employee.department,
                         record.net_wage,
                         record.employee.payment_option,
                         record.employee.bank,
                         record.employee.account_number,
                         record.employee.location])
            row_heights.append(14)
            
            # Add totals
            total_gross += record.gross_wage + record.stipend + record.manager_stipend
            total_ss += record.social_security_withholding
            total_net += record.net_wage
            
            # Increase row count
            index += 1
            
        # Add total summary to bottom of data
        data += [['', ''],
                 ['Gross Wage + Stipend Total', '', '', total_gross],
                 ['Social Security Total', '', '',  total_ss],
                 ['Net Wage Total', '', '', total_net]]
        
        total_rows = len(data)
        style_data += [('SPAN', (0, total_rows - 4), (2, total_rows - 4)),
                       ('SPAN', (0, total_rows - 3), (2, total_rows - 3)),
                       ('SPAN', (0, total_rows - 2), (2, total_rows - 2)),
                       ('SPAN', (0, total_rows - 1), (2, total_rows - 1))]
                       
        row_heights += [20, 20, 20, 20]

        table = Table(data, rowHeights=row_heights)
        style = TableStyle(style_data)
        
        table.setStyle(style)
        
        return table
        
    def _create_thailand_summary(self, records):
        """Build an employee summary for direct deposit
        """
        # Filter records for direct deposit only
        records = records.filter(employee__location='thailand')
        
        total_gross = 0
        total_ss = 0
        total_net = 0
        index = 0
        
        current_department = None
        data = [['ID', 'Name', 'Department', 'Net Wage', 'Payment', 'Bank', "Account Number", "Location"]]
        style_data = [('FONTSIZE', (0,0),(-1,0), 16),
                      ('FONT', (0,0), (-1,-1), 'Garuda'),
                      ('SPAN', (0, 1), (-1, 1)),
                      ('FONTSIZE', (0, 1),(-1, 1), 14),
                      ('ALIGNMENT', (0, 1), (-1, 1), 'CENTER'),
                      ('PADDING', (0, 0), (-1, -1), 10),
                      ('ALIGNMENT', (3, 1), (-1, -1), 'RIGHT'),
                      ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                      ('GRID', (0, 0), (-1, -5),  1, colors.CMYKColor(black=60))]
        row_heights = [40]
        
        for record in records:
            if record.employee.department != current_department:
                # Increase row count
                index += 1
                
                current_department = record.employee.department
                data.append([current_department])
                style_data += [('SPAN', (0, index), (-1, index)),
                               ('FONTSIZE', (0, index), (-1, index), 14),
                               ('ALIGNMENT', (0, index), (-1, index), 'CENTER')]
                               #('PADDING', (0, index + 2), (-1, index + 2), 10)]
                row_heights.append(30)
                
            data.append([record.employee.id, 
                         record.employee.name,
                         record.employee.department,
                         record.net_wage,
                         record.employee.payment_option,
                         record.employee.bank,
                         record.employee.account_number,
                         record.employee.location])
            row_heights.append(14)
            
            # Add totals
            total_gross += record.gross_wage + record.stipend + record.manager_stipend
            total_ss += record.social_security_withholding
            total_net += record.net_wage
            
            # Increase row count
            index += 1

        # Add total summary to bottom of data
        data += [['', ''],
                 ['Gross Wage + Stipend Total', '', '', total_gross],
                 ['Social Security Total', '', '',  total_ss],
                 ['Net Wage Total', '', '', total_net]]
        
        total_rows = len(data)
        style_data += [('SPAN', (0, total_rows - 4), (2, total_rows - 4)),
                       ('SPAN', (0, total_rows - 3), (2, total_rows - 3)),
                       ('SPAN', (0, total_rows - 2), (2, total_rows - 2)),
                       ('SPAN', (0, total_rows - 1), (2, total_rows - 1))]
                       
        row_heights += [20, 20, 20, 20]
        
        table = Table(data, rowHeights=row_heights)
        style = TableStyle(style_data)
        
        table.setStyle(style)
        
        return table
        
    def _create_employee_attendance(self, records):
        """Create and overall detailed summary of all attendances
        """
        data = [['ID', 'Card ID', 'Name', 
                 Table([['Date', 'Start Time', 'End Time', 'Hours', 'Overtime']], colWidths=100)]]
        
        for record in records:
            data.append([record.employee.id,
                         record.employee.card_id,
                         self._format_text(record.employee.name),
                         self._create_attendance_details(record)])
                         
        table = Table(data, colWidths=(100, 100, 100, 500), repeatRows=1)
        style = TableStyle([('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 1), (2, -1), 'TOP'),
                            ('PADDING', (0, 0), (-1, -1), 0),
                            ('GRID', (0, 0), (-1, -1),  1, colors.CMYKColor(black=60))
                            ])
        table.setStyle(style)
        
        return table
    
    def _create_attendance_details(self, record):
        
        data = []
        r_days = 0
        r_ot = 0
        sundays = 0
        sunday_ot = 0
        
        for a in record.attendances.all().order_by('date'):
            data.append([a.date, 
                         a.start_time.time() if a.start_time else '',
                         a.end_time.time() if a.end_time else '',
                         "{0:.2f}".format(Decimal(a.regular_time or 0)),
                         "{0:.2f}".format(Decimal(a.overtime or 0))])
                         #"{0:.2f}".format(a.gross_wage),
                         #"{0:.2f}".format(a.net_wage)])
                         
            if a.is_sunday:
                sundays += 1
                sunday_ot += a.overtime
            else:
                r_days += (a.regular_time or Decimal('0')) / Decimal('8')
                r_ot += a.overtime
            
        
        data.append(['', '', '', 'Regular', '{0:.2f}'.format(r_days)])
        data.append(['', '', '', 'Overtime', '{0:.2f}'.format(r_ot)])
        data.append(['', '', '', 'Sundays', '{0:.2f}'.format(sundays)])
        data.append(['', '', '', 'Sunday Overtime', '{0:.2f}'.format(sunday_ot)])
        
                    
        table = Table(data, colWidths=(100, 100, 100, 100, 100))
        style = TableStyle([('BOX', (3, -4), (-1, -1), 1, colors.CMYKColor(black=60))])
        table.setStyle(style)
        
        return table
        
        
    def _format_text(self, description, font_size=12):
        """
        Formats the description into a paragraph
        with the paragraph style
        """
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               leading=12,
                               wordWrap=None,
                               allowWidows=0,
                               alignment=1,
                               allowOrphans=0,
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        
        return Paragraph(description, style)
        
        
class AttendancePDF(object):
    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]
    cell_width = 35
    cell_height = 25

    def __init__(self, start_date=None, end_date=None, employees=[], *args, **kwargs):
            
        self.start_date = start_date
        self.end_date = end_date
        self.employees = employees
          
        super(AttendancePDF, self).__init__(*args, **kwargs)
        
    def create(self, response=None):
        
        if response is None:
            response = 'Payroll_{0}-{1}.pdf'.format(self.start_date, self.end_date)
            self.filename = response
        
        doc = SimpleDocTemplate(response, 
                                pagesize=landscape(A3), 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        
        
        stories.append(self._format_text("Attendance Summary",
                                         font_size=30))
        stories.append(Spacer(0, 50))
        stories.append(self._create_employee_attendance())
        doc.build(stories)

        return self.filename 

    def _create_employee_attendance(self):
        """Create and overall detailed summary of all attendances
        """


        dates = [self.start_date + timedelta(days=i) for i in xrange((self.end_date - self.start_date).days + 1)]
        dates_table = Table([[d.strftime("%b") for d in dates],
                             [d.strftime("%d") for d in dates]], colWidths=self.cell_width, rowHeights=20)
        dates_table.setStyle(TableStyle([('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                                         ('FONTSIZE', (0, 0), (-1, -1), 14),
                                         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                         ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                                         ('TOPPADDING', (0, 0), (-1, -1), 0),
                                         ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                                         ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                         ('LEFTPADDING', (0, 0), (-1, -1), 0),]))
        data = [['Employee', dates_table]]

        for employee in self.employees:

            try:
                id_data = [[self._format_text(employee.name)], [self.get_image(employee.image.generate_url(), width=90)]]
            except AttributeError as e:
                id_data = [[self._format_text(employee.name)], ['']]

            id_table = Table(id_data, rowHeights=(25,125))
        
            data.append([id_table, self._create_attendance_details(employee, dates)])
                         
        table = Table(data, colWidths=(100, self.cell_width * len(dates)), repeatRows=1)
        style = TableStyle([('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
                            ('FONT', (0, 0), (-1, -1), 'Tahoma'),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('GRID', (0, 0), (-1, -1),  1, colors.CMYKColor(black=60))
                            ])
        table.setStyle(style)
        
        return table
    
    def _create_attendance_details(self, employee, dates):
        
        predata = {}
        data = []
        r_days = 0
        r_ot = 0
        sundays = 0
        sunday_ot = 0
        
        attendances = employee.attendances.filter(date__gte=self.start_date, 
                                                  date__lte=self.end_date)

        logger.debug(employee.name)
        logger.debug(attendances.count())
        print '\n'

        for dd in dates:
            predata[dd] = None

        for a in attendances.order_by('date'):
            predata[a.date] = a

        for key in predata:
            a = predata[key]
            mdata = []
            a_styles = [('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('FONTSIZE', (0, 0), (-1, -1), 12),
                        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        #('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(yellow=50, cyan=50))
                        ('LINEAFTER', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60))

                        ]

            try:
                if a.vacation or a.sick_leave:
                    
                    if a.vacation:
                        mdata.append(['V'])
                        a_styles.append(('TEXTCOLOR', (0, 0), (-1, -1), colors.yellow))
                    elif a.sick_leave:
                        mdata.append(['S'])
                        a_styles.append(('TEXTCOLOR', (0, 0), (-1, -1), colors.orange))

                    a_styles.append(('SPAN', (0, 0), (-1, -1)))
                    for i in xrange(6 - len(mdata)):
                        mdata.append([''])

                else:
                    mdata.append([a.start_time.strftime('%H:%M')])
                    mdata.append([a.end_time.strftime('%H:%M')])
                    mdata.append([a.regular_time])
                    mdata.append([a.overtime])
                    mdata.append([a.doubletime])
                    mdata.append([a.sunday_overtime])
                    
            except AttributeError as e:
                logger.debug(e)
                a_styles.append(('TEXTCOLOR', (0, len(mdata)), (-1, -1), colors.red))
                a_styles.append(('SPAN', (0, len(mdata)), (-1, -1)))
                for i in xrange(6 - len(mdata)):
                    mdata.append(['N'])
                


            a_table = Table(mdata, rowHeights=self.cell_height, colWidths=self.cell_width)
            a_table.setStyle(TableStyle(a_styles))
            data.append(a_table)
            """
                         a.start_time.time() if a.start_time else '',
                         a.end_time.time() if a.end_time else '',
                         "{0:.2f}".format(Decimal(a.regular_time or 0)),
                         "{0:.2f}".format(Decimal(a.overtime or 0))])
                         #"{0:.2f}".format(a.gross_wage),
                         #"{0:.2f}".format(a.net_wage)])
                         
                         
            if a.is_sunday:
                sundays += 1
                sunday_ot += a.overtime
            else:
                r_days += (a.regular_time or Decimal('0')) / Decimal('8')
                r_ot += a.overtime
            
        
        data.append(['', '', '', 'Regular', '{0:.2f}'.format(r_days)])
        data.append(['', '', '', 'Overtime', '{0:.2f}'.format(r_ot)])
        data.append(['', '', '', 'Sundays', '{0:.2f}'.format(sundays)])
        data.append(['', '', '', 'Sunday Overtime', '{0:.2f}'.format(sunday_ot)])
        """
                    
        table = Table([data], colWidths=self.cell_width, rowHeights=self.cell_height*6)
        style = TableStyle([#('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(cyan=60)),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),])
        table.setStyle(style)
        
        return table
        
        
    def _format_text(self, description, font_size=12):
        """
        Formats the description into a paragraph
        with the paragraph style
        """
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               leading=12,
                               wordWrap=None,
                               allowWidows=0,
                               alignment=1,
                               allowOrphans=0,
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        
        return Paragraph(description, style)

    #helps change the size and maintain ratio
    def get_image(self, path, width=None, height=None, max_width=0, max_height=0):
        """Retrieves the image via the link and gets the
        size from the image. The correct dimensions for
        image are calculated based on the desired with or
        height"""
        try:
            #Read image from link
            img = utils.ImageReader(path)
        except:
            return None
        #Get Size
        imgWidth, imgHeight = img.getSize()
        #Detect if there height or width provided
        if width and height == None:
            ratio = float(imgHeight) / float(imgWidth)
            new_height = ratio * width
            new_width = width
        elif height and width == None:
            ratio = float(imgWidth) / float(imgHeight)
            new_height = height
            new_width = ratio * height
            if max_width != 0 and new_width > max_width:
                new_width = max_width
                new_height = (float(imgHeight) / float(imgWidth)) * max_width

        return Image(path, width=new_width, height=new_height)