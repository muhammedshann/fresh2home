# Generated by Django 5.1.5 on 2025-03-02 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0037_remove_order_coupon_code_order_coupon'),
    ]

    operations = [
        migrations.AddField(
            model_name='complaint',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='profile_images/'),
        ),
    ]
