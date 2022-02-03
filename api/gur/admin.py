from django.apps import apps
from django.contrib.gis import admin


for model in apps.get_app_config('gur').get_models():
    try:
        admin.site.register(model)
    except:
        pass
