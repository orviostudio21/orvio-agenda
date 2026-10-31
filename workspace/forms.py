from django import forms
from django.db import models

def form_for(model):
    class OwnedForm(forms.ModelForm):
        class Meta:
            fields = '__all__'
            exclude = ('owner',)

        def _get_validation_exclusions(self):
            excluded = super()._get_validation_exclusions()
            excluded.discard('owner')
            return excluded

        def __init__(self, *args, user, **kwargs):
            super().__init__(*args, **kwargs)
            self.instance.owner = user
            for name, field in self.fields.items():
                if isinstance(field, forms.ModelChoiceField):
                    field.queryset = field.queryset.filter(owner=user)
                if isinstance(field, forms.DateTimeField):
                    field.widget = forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type':'datetime-local'})
                    field.input_formats = ['%Y-%m-%dT%H:%M']
                elif isinstance(field, forms.DateField):
                    field.widget = forms.DateInput(format='%Y-%m-%d', attrs={'type':'date'})
                if isinstance(field, forms.DecimalField):
                    field.widget.attrs.update(step='0.01')
                if isinstance(field.widget, forms.Textarea):
                    field.widget.attrs['rows'] = 4
    OwnedForm.Meta.model = model
    # ModelForm's metaclass needs the model when creating the class.
    Meta = type('Meta', (), {'model':model, 'exclude':('owner',)})
    return type(model.__name__+'Form', (OwnedForm,), {'Meta':Meta})
