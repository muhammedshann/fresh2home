# Generated by Django 5.1.5 on 2025-02-14 12:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0002_alter_category_options_alter_products_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='profile',
            field=models.ImageField(blank=True, null=True, upload_to='profile_images/'),
        ),
    ]
