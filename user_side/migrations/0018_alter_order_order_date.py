# Generated by Django 5.1.5 on 2025-02-17 20:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0017_alter_productvariant_weight'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='order_date',
            field=models.DateField(auto_now=True),
        ),
    ]
