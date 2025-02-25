# Generated by Django 5.1.5 on 2025-02-25 05:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0029_user_referred_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='user_side.productvariant'),
        ),
    ]
