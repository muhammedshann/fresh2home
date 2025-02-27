from django.contrib import admin
from django.apps import apps

# Get all models from the 'user_side' app
user_side_models = apps.get_app_config('user_side').get_models()

# Register each model dynamically
for model in user_side_models:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass  # Skip if already registered
