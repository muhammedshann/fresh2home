# Generated by Django 5.1.5 on 2025-02-25 08:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0030_orderitem_variant'),
    ]

    operations = [
        migrations.CreateModel(
            name='Complaint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('IN_PROGRESS', 'In Progress'), ('RESOLVED', 'Resolved'), ('REJECTED', 'Rejected')], default='PENDING', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='complaints', to='user_side.orderitem')),
            ],
            options={
                'db_table': 'complaints',
            },
        ),
    ]
