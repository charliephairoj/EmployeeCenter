# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('estimates', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='depth',
            field=models.IntegerField(default=0, null=True, db_column=b'depth'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='item',
            name='height',
            field=models.IntegerField(default=0, null=True, db_column=b'height'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='item',
            name='units',
            field=models.CharField(default=b'mm', max_length=20, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='item',
            name='width',
            field=models.IntegerField(default=0, null=True, db_column=b'width'),
            preserve_default=True,
        ),
    ]
