# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-09-26 23:05
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_update_templates_with_cyverse'),
    ]

    operations = [
        migrations.AlterField(
            model_name='atmosphereuser',
            name='first_name',
            field=models.CharField(blank=True, max_length=64, verbose_name='first name'),
        ),
        migrations.AlterField(
            model_name='atmosphereuser',
            name='last_name',
            field=models.CharField(blank=True, max_length=256, verbose_name='last name'),
        ),
        migrations.AlterField(
            model_name='atmosphereuser',
            name='username',
            field=models.CharField(error_messages={b'unique': 'A user with that username already exists.'}, help_text='Required. 256 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=256, unique=True, validators=[django.core.validators.RegexValidator(b'^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.')], verbose_name='username'),
        ),
    ]
