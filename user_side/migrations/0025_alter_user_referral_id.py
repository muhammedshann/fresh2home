# Generated by Django 5.1.5 on 2025-02-24 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0024_user_referral_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='referral_id',
            field=models.CharField(max_length=10, null=True, unique=True),
        ),
    ]
