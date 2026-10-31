from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from workspace import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('', views.dashboard, name='dashboard'),
    path('settings/', views.settings, name='settings'),
    path('demo/', views.demo, name='demo'),
    path('health/', views.health, name='health'),
    path('api/overview/', views.overview_api, name='overview-api'),
    path('records/<slug:kind>/', views.records, name='records'),
    path('records/<slug:kind>/new/', views.record_edit, name='record-new'),
    path('records/<slug:kind>/export/', views.export_csv, name='export'),
    path('records/<slug:kind>/<int:pk>/', views.record_detail, name='record-detail'),
    path('records/<slug:kind>/<int:pk>/edit/', views.record_edit, name='record-edit'),
    path('records/<slug:kind>/<int:pk>/delete/', views.record_delete, name='record-delete'),
]
