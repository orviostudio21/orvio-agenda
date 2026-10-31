
import csv
from io import StringIO
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.test import TestCase, Client as Browser
from django.urls import reverse
from django.utils import timezone
from .domain import REGISTRY, seed_data, dashboard_data
from .forms import form_for
from .models import *

class WorkspaceTests:
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('marina',password='A-strong-password-2026')
        cls.other = get_user_model().objects.create_user('rafael',password='A-strong-password-2026')
        seed_data(cls.user)
        seed_data(cls.other)

    def setUp(self):
        cache.clear()
        self.client.force_login(self.user)

    def test_private_routes_require_login(self):
        self.client.logout()
        for url in ['/', '/settings/', '/api/overview/']:
            self.assertEqual(self.client.get(url).status_code,302)

    def test_dashboard_and_api_render_real_data(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Orvio')
        self.assertNotRegex(response.content.decode(), r'height:[0-9]+,[0-9]+%')
        api = self.client.get('/api/overview/')
        self.assertEqual(api.status_code,200)
        self.assertEqual(len(api.json()['metrics']),4)

    def test_all_lists_details_and_forms_render(self):
        for kind,config in REGISTRY.items():
            obj = config['model'].objects.filter(owner=self.user).first()
            for url in [f'/records/{kind}/',f'/records/{kind}/new/',f'/records/{kind}/{obj.pk}/',f'/records/{kind}/{obj.pk}/edit/',f'/records/{kind}/{obj.pk}/delete/']:
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code,200)

    def test_foreign_objects_are_inaccessible(self):
        for kind,config in REGISTRY.items():
            obj = config['model'].objects.filter(owner=self.other).first()
            for suffix in ['', 'edit/', 'delete/']:
                url = f'/records/{kind}/{obj.pk}/'+suffix
                self.assertEqual(self.client.get(url).status_code,404)
                self.assertEqual(self.client.post(url,{}).status_code,404)
            self.assertTrue(config['model'].objects.filter(pk=obj.pk).exists())

    def test_foreign_relations_are_not_form_choices(self):
        for config in REGISTRY.values():
            model = config['model']
            obj = model(owner=self.user)
            form = form_for(model)(instance=obj,user=self.user)
            for field in form.fields.values():
                if hasattr(field,'queryset') and field.queryset is not None:
                    self.assertFalse(field.queryset.exclude(owner=self.user).exists())

    def test_owner_cannot_be_changed_by_post(self):
        kind,config = next(iter(REGISTRY.items()))
        obj = config['model'].objects.filter(owner=self.user).first()
        data = model_to_dict(obj)
        data['owner'] = self.other.pk
        for key,value in list(data.items()):
            if value is None:
                data[key] = ''
            elif hasattr(value,'isoformat'):
                data[key] = timezone.localtime(value).strftime('%Y-%m-%dT%H:%M') if isinstance(value,timezone.datetime) else value.isoformat()
        response = self.client.post(f'/records/{kind}/{obj.pk}/edit/',data)
        self.assertEqual(response.status_code,302)
        obj.refresh_from_db()
        self.assertEqual(obj.owner_id,self.user.pk)

    def test_csv_export_is_scoped(self):
        for kind,config in REGISTRY.items():
            response = self.client.get(f'/records/{kind}/export/')
            self.assertEqual(response.status_code,200)
            rows = list(csv.reader(StringIO(response.content.decode('utf-8-sig'))))
            self.assertEqual(len(rows),config['model'].objects.filter(owner=self.user).count()+1)

    def test_demo_is_idempotent_and_does_not_overwrite(self):
        counts = [c['model'].objects.filter(owner=self.user).count() for c in REGISTRY.values()]
        self.client.post('/demo/')
        self.assertEqual(counts,[c['model'].objects.filter(owner=self.user).count() for c in REGISTRY.values()])

    def test_new_account_starts_empty_and_can_seed(self):
        fresh = get_user_model().objects.create_user('new-account',password='Some-strong-pass-26')
        self.client.force_login(fresh)
        self.assertContains(self.client.get('/'),'Seu próximo capítulo')
        self.assertEqual(self.client.post('/demo/').status_code,302)
        self.assertTrue(all(c['model'].objects.filter(owner=fresh).exists() for c in REGISTRY.values()))

    def test_mutations_require_csrf(self):
        browser = Browser(enforce_csrf_checks=True)
        browser.force_login(self.user)
        self.assertEqual(browser.post('/demo/').status_code,403)

    def test_logout_is_post_only(self):
        self.assertEqual(self.client.get('/logout/').status_code,405)
        self.assertEqual(self.client.post('/logout/').status_code,302)

    def test_unknown_collections_404(self):
        self.assertEqual(self.client.get('/records/unknown/').status_code,404)

    def test_signup_rejects_weak_password(self):
        self.client.logout()
        response = self.client.post('/signup/',{'username':'weak','password1':'123','password2':'123'})
        self.assertEqual(response.status_code,200)
        self.assertFalse(get_user_model().objects.filter(username='weak').exists())

    def test_signup_and_login(self):
        self.client.logout()
        response = self.client.post('/signup/',{'username':'new-user','password1':'A-new-strong-pass-2026','password2':'A-new-strong-pass-2026'})
        self.assertEqual(response.status_code,302)
        self.client.post('/logout/')
        response = self.client.post('/login/',{'username':'new-user','password':'A-new-strong-pass-2026'})
        self.assertEqual(response.status_code,302)

    def test_password_change_preserves_session(self):
        response = self.client.post('/settings/',{'old_password':'A-strong-password-2026','new_password1':'Changed-strong-pass-26','new_password2':'Changed-strong-pass-26'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.client.get('/').status_code,200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Changed-strong-pass-26'))

    def test_login_rate_limit(self):
        self.client.logout()
        for i in range(20):
            self.client.post('/login/',{'username':'absent','password':'wrong'})
        self.assertEqual(self.client.post('/login/',{'username':'absent','password':'wrong'}).status_code,429)

    def test_admin_forms_have_owner_and_scoped_relations(self):
        from django.contrib import admin
        from django.test import RequestFactory
        superuser = get_user_model().objects.create_superuser('admin-review', password='Admin-test-password-26', email='admin@example.com')
        request = RequestFactory().get('/admin/')
        request.user = superuser
        for config in REGISTRY.values():
            model_admin = admin.site._registry[config['model']]
            form = model_admin.get_form(request)()
            self.assertEqual(form.instance.owner, superuser)
            for field in form.fields.values():
                if hasattr(field, 'queryset') and field.queryset is not None:
                    self.assertFalse(field.queryset.exclude(owner=superuser).exists())

    def test_health_checks_database(self):
        self.assertEqual(self.client.get('/health/').json(),{'status':'ok'})


class AgendaTests(WorkspaceTests, TestCase):
    def appointment_data(self, start=None, professional=None):
        existing = Appointment.objects.filter(owner=self.user).first()
        return {'client':existing.client_id,'service':existing.service_id,'professional':professional or existing.professional,'start_at':timezone.localtime(start or existing.start_at).strftime('%Y-%m-%dT%H:%M'),'price':'180','status':'confirmed'}

    def test_overlap_is_rejected(self):
        form = form_for(Appointment)(self.appointment_data(),user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('start_at',form.errors)

    def test_professional_is_normalized_before_overlap(self):
        existing = Appointment.objects.filter(owner=self.user).first()
        form = form_for(Appointment)(self.appointment_data(professional='  '+existing.professional.lower()+'  '),user=self.user)
        self.assertFalse(form.is_valid())

    def test_adjacent_appointment_is_allowed(self):
        existing = Appointment.objects.filter(owner=self.user).first()
        form = form_for(Appointment)(self.appointment_data(start=existing.end_at),user=self.user)
        self.assertTrue(form.is_valid(),form.errors)

    def test_cancelled_appointment_releases_slot(self):
        existing = Appointment.objects.filter(owner=self.user).first()
        existing.status = 'cancelled'
        existing.save()
        form = form_for(Appointment)(self.appointment_data(start=existing.start_at,professional=existing.professional),user=self.user)
        self.assertTrue(form.is_valid(),form.errors)

    def test_other_professional_can_use_same_time(self):
        form = form_for(Appointment)(self.appointment_data(professional='Nova profissional'),user=self.user)
        self.assertTrue(form.is_valid(),form.errors)

    def test_duration_snapshot_survives_catalog_edit(self):
        existing = Appointment.objects.filter(owner=self.user).first()
        original_end = existing.end_at
        existing.service.duration = 120
        existing.service.save()
        form = form_for(Appointment)(self.appointment_data(),instance=existing,user=self.user)
        self.assertTrue(form.is_valid(),form.errors)
        form.save()
        existing.refresh_from_db()
        self.assertEqual(existing.end_at,original_end)

    def test_negative_price_is_rejected(self):
        data = self.appointment_data(professional='Nova profissional')
        data['price'] = '-5'
        self.assertFalse(form_for(Appointment)(data,user=self.user).is_valid())

    def test_create_update_cancel_delete_appointment(self):
        data = self.appointment_data(professional='Teste funcional')
        response = self.client.post('/records/appointments/new/',data)
        self.assertEqual(response.status_code,302)
        obj = Appointment.objects.get(owner=self.user,professional='Teste Funcional')
        self.assertGreater(obj.end_at,obj.start_at)
        data['status'] = 'cancelled'
        self.assertEqual(self.client.post(f'/records/appointments/{obj.pk}/edit/',data).status_code,302)
        obj.refresh_from_db()
        self.assertEqual(obj.status,'cancelled')
        self.client.post(f'/records/appointments/{obj.pk}/delete/')
        self.assertFalse(Appointment.objects.filter(pk=obj.pk).exists())
