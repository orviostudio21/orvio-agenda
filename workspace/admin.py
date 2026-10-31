from django.contrib import admin
from .domain import REGISTRY
from .forms import form_for
from .models import Event


class OwnedAdmin(admin.ModelAdmin):
    """Assign ownership on creation and scope staff views and relation choices."""
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset if request.user.is_superuser else queryset.filter(owner=request.user)

    def get_form(self, request, obj=None, **kwargs):
        owner = obj.owner if obj else request.user
        base = form_for(self.model)

        class AdminForm(base):
            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, user=owner, **form_kwargs)

        return AdminForm


@admin.register(Event)
class EventAdmin(OwnedAdmin):
    list_display = ('description', 'owner', 'created_at')
    readonly_fields = ('description', 'owner', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


for item in REGISTRY.values():
    admin.site.register(item['model'], OwnedAdmin)
admin.site.site_header = 'Orvio Studio · Administração'
