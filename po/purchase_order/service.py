#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from administrator.models import User
from accounting.account import service as account_service
from po.models import PurchaseOrder, Item, Log


logger = logging.getLogger(__name__)


"""
Purchase Order Section
"""

def create(employee=None, **kwargs):
    """
    Create Purchase Order
    """
    # Check that the user is a user instance
    assert isinstance(employee, User), u"{0} should be a User instance".format(employee)
    
    po = PurchaseOrder.objects.create(employee=employee, **kwargs)
    
    return po

def post_create(employee=None, po=None, files=[]):
    """
    Called after PO and items creation

    1. Calculate totals
    2. Create and upload PDF
    3. Add PDF to files
    4. Add other files
    5. Create approval pass and salt
    6. Create Google Cal Event
    7.
    """

    po.calculate_totals()

    po.create_and_upload_pdf()

    # Add pdf to files list
    add_file(po=po, 
             file=po.pdf, 
             employee=employee)
                
    # Add files
    for file_obj in files:
        add_file(po=po, 
                 file_obj=S3Object.objects.get(pk=file_obj['id']),
                 employee=employee)

    # Create approval key and salt
    po.approval_key = po.create_approval_key()
    po.approval_salt = po.create_approval_key()

    po.save()

    # Create a calendar event
    try:
        po.create_calendar_event(employee)
    except Exception as e:
        message = "Unable to create calendar event because: {0}"
        message = message.format(e)
        type_label = "PURCHASE ORDER CALENDAR ERROR"
        POLog.create(message=message, purchase_order=po, user=employee, type=type_label)

    # Log Opening of an order
    message = "Purchase Order #{0} was created.".format(po.id)
    create_log(message, po, employee)

    try:
        po.email_approver()
        message = "Purchase Order #{0} sent for approval.".format(po.id)
        create_log(message, po, employee)
    except Exception as e:
        message = "Unable to email approver because: {0}"
        message = message.format(e)
        type_label = "PURCHASE ORDER EMAIL ERROR"
        POLog.create(message=message, purchase_order=po, user=employee, type=type_label)

    return po

def update(po, data, employee):
    """
    Update Purchase Order

    1. Get current user
    2. Update associated models
    3. Update Order terms and details
    4. Attach files
    5. Attach Payment Documents
    6. Update Status
    7. Update Items
    8. Calcuate a new total
    9. Create a new pdf
    """
    # Check po is a po instance
    assert isinstance(po, PurchaseOrder), u"{0} should be a PurchaseOrder instance".format(po)
    
    # Check that the user is a user instance
    assert isinstance(user, User), u"{0} should be a User instance".format(user)

    # Get the current user
    try:
        employee = self.context['request'].user
    except KeyError as e:
        employee = self.context['employee']
    
    po.current_user = employee

    # Section: Update order terms and details
    # 
    # We loop through properties, apply changes 
    # and log the changes        
    fields = ['vat',
                'discount',
                'deposit',
                'currency',
                'terms',
                'acknowledgement',
                'project',
                'room',
                'phase']
    for field in fields:
        old_val = getattr(po, field)
        new_val = data.pop(field, old_val)
        
        if new_val != old_val:
            setattr(po, field, new_val)

            self._log_change(field, old_val, new_val)

    receive_date = timezone('Asia/Bangkok').normalize(data.pop('receive_date'))
    if receive_date != po.receive_date:
        old_rd = po.receive_date
        po.receive_date = receive_date
        
        self._log_change('receive date', old_rd.strftime('%d/%m/%Y'), receive_date.strftime('%d/%m/%Y'))

    
    # Section: Update payment documents
    # 
    # We loop through properties, apply changes 
    # and log the changes
    if employee.has_perm('po.change_purchaseorder_deposit_document'):
        po.deposit_document = data.pop('deposit_document', po.deposit_document)

    if employee.has_perm('po.change_purchaseorder_balance_document'):
        po.balance_document = data.pop('balance_document', po.balance_document)

    #Update attached files
    files = data.pop('files', [])
    for file_obj in files:
        try:
            File.objects.get(file_id=file_obj['id'], purchase_order=po)
        except File.DoesNotExist:
            File.objects.create(file=S3Object.objects.get(pk=file_obj['id']),
                                purchase_order=po)

    
    # Process if status has changed
    new_status = data.pop('status', po.status)
    old_status = po.status

    if new_status.lower() != old_status.lower():

        # Check permissions
        if old_status.lower() == 'awaiting approval':
            if employee.has_perm('po.approve_purchaseorder'):
                po.approve(user=employee)

                self._log_change('status', old_status, new_status)
            else:
                logger.warn(u"{0} is not qualified.".format(employee.username))
        else:

            po.status = new_status

            if old_status.lower() != "ordered" and po.status.lower() == "received":
                self.receive_order(po, data)

            po.save()

            self._log_change('status', old_status, new_status)

    po.revision += 1

    po.calculate_totals()

    po.create_and_upload_pdf()

    po.save()

    try:
        po.update_calendar_event()
    except Exception as e:
        try:
            message = "Unable to create calendar event because: {0}"
            message = message.format(e)
            POLog.objects.create(message=message, purchase_order=po, user=employee)
        except ValueError as e:
            logger.warn(e)

    return po


"""
Purchase Order Item Section
"""

def create_item(purchase_order=None, supply=None, **kwargs):
    item = Item.objects.create(purchase_order=purchase_order, **kwargs)
    
    item.calculate_total()

    item.save()

    return item


"""
Misc
"""
def add_file(po, file, employee):
    File.objects.create(file=file,
                        purchase_order=po)

    u"File '{0}' added to Purchase Order {1}".format(file.filename, po.id)        
    create_log(message, po, employee)


def create_log(message, po, user):
    return POLog.create(message=message, purchase_order=po, user=employee)
