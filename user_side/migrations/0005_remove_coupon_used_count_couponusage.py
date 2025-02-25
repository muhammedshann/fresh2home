# Generated by Django 5.1.5 on 2025-02-15 06:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0004_alter_coupon_options_coupon_used_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coupon',
            name='used_count',
        ),
        migrations.CreateModel(
            name='CouponUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('used_at', models.DateTimeField(auto_now_add=True)),
                ('coupon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.coupon')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'coupon_usage',
                'unique_together': {('user', 'coupon')},
            },
        ),
    ]
