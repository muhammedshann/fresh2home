# Generated by Django 5.1.5 on 2025-02-17 04:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0005_remove_coupon_used_count_couponusage'),
    ]

    operations = [
        migrations.CreateModel(
            name='store',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store', models.CharField(max_length=20)),
                ('pincode', models.CharField(max_length=7)),
                ('status', models.BooleanField(default=False)),
            ],
        ),
    ]
