# Generated by Django 5.1.5 on 2025-02-24 07:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0027_remove_user_referral_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='referral_id',
            field=models.CharField(blank=True, max_length=10, null=True, unique=True),
        ),
    ]
