# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contacts', '__first__'),
        ('supplies', '__first__'),
        ('products', '__first__'),
        ('projects', '__first__'),
        ('media', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.TextField()),
                ('_delivery_date', models.DateTimeField()),
                ('longitude', models.DecimalField(null=True, max_digits=9, decimal_places=6)),
                ('latitude', models.DecimalField(null=True, max_digits=9, decimal_places=6)),
                ('last_modified', models.DateTimeField(auto_now=True, auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Estimate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('po_id', models.TextField(default=None, null=True)),
                ('company', models.TextField(default=b'Dellarobbia Thailand')),
                ('discount', models.IntegerField(default=0)),
                ('time_created', models.DateTimeField(auto_now_add=True)),
                ('delivery_date', models.DateTimeField(null=True, db_column=b'delivery_date')),
                ('status', models.TextField(default=b'ACKNOWLEDGED')),
                ('remarks', models.TextField(default=None, null=True, blank=True)),
                ('fob', models.TextField(null=True, blank=True)),
                ('shipping_method', models.TextField(null=True, blank=True)),
                ('subtotal', models.DecimalField(default=0, max_digits=15, decimal_places=2)),
                ('total', models.DecimalField(default=0, max_digits=15, decimal_places=2)),
                ('vat', models.IntegerField(default=0, null=True)),
                ('last_modified', models.DateTimeField(auto_now=True, auto_now_add=True)),
                ('deleted', models.BooleanField(default=False)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='contacts.Customer', null=True)),
                ('employee', models.ForeignKey(db_column=b'employee_id', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, null=True)),
                ('pdf', models.ForeignKey(related_name='+', to='media.S3Object', null=True)),
                ('project', models.ForeignKey(related_name='estimates', blank=True, to='projects.Project', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=20, null=True)),
                ('quantity', models.IntegerField()),
                ('unit_price', models.DecimalField(null=True, max_digits=15, decimal_places=2)),
                ('total', models.DecimalField(null=True, max_digits=15, decimal_places=2)),
                ('width', models.IntegerField(default=0, db_column=b'width')),
                ('depth', models.IntegerField(default=0, db_column=b'depth')),
                ('height', models.IntegerField(default=0, db_column=b'height')),
                ('units', models.CharField(default=b'mm', max_length=20, blank=True)),
                ('description', models.TextField()),
                ('is_custom_size', models.BooleanField(default=False, db_column=b'is_custom_size')),
                ('is_custom_item', models.BooleanField(default=False)),
                ('status', models.CharField(default=b'ACKNOWLEDGED', max_length=50)),
                ('comments', models.TextField(null=True, blank=True)),
                ('location', models.TextField(null=True, blank=True)),
                ('deleted', models.BooleanField(default=False)),
                ('inventory', models.BooleanField(default=False)),
                ('last_modified', models.DateTimeField(auto_now=True, auto_now_add=True)),
                ('estimate', models.ForeignKey(related_name='items', to='estimates.Estimate')),
                ('fabric', models.ForeignKey(related_name='estimate_item_fabric', blank=True, to='supplies.Fabric', null=True)),
                ('image', models.ForeignKey(related_name='estimate_item_image', blank=True, to='media.S3Object', null=True)),
                ('product', models.ForeignKey(related_name='estimate_item_product', to='products.Product')),
            ],
            options={
                'permissions': (('change_item_price', 'Can edit item price'), ('change_fabric', 'Can change fabric')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now=True, auto_now_add=True, db_column=b'log_timestamp')),
                ('delivery_date', models.DateField(null=True)),
                ('estimate', models.ForeignKey(to='estimates.Estimate')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Pillow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=10, db_column=b'type')),
                ('quantity', models.IntegerField(default=1)),
                ('fabric', models.ForeignKey(related_name='estimate_pillow_fabric', blank=True, to='supplies.Fabric', null=True)),
                ('item', models.ForeignKey(related_name='pillows', to='estimates.Item')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='delivery',
            name='estimate',
            field=models.ForeignKey(to='estimates.Estimate', null=True),
            preserve_default=True,
        ),
    ]
