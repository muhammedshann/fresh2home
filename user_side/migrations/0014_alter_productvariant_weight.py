# Generated by Django 5.1.5 on 2025-02-17 17:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0013_alter_productvariant_weight'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productvariant',
            name='weight',
            field=models.IntegerField(choices=[(250, '250 Grams'), (500, '500 Grams'), (750, '750 Grams'), (1000, '1 Kilogram')]),
        ),
    ]
