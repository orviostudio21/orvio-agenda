from django.contrib import admin
from .domain import REGISTRY
from .models import Event
for item in REGISTRY.values():
    admin.site.register(item['model'])
admin.site.register(Event)
admin.site.site_header = 'Orvio Studio · Administração'
