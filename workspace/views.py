import csv
from datetime import date, datetime
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, ProtectedError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .domain import REGISTRY, dashboard_data, seed_data
from .forms import form_for
from .models import Event

def config_for(kind):
    if kind not in REGISTRY:
        raise Http404
    return REGISTRY[kind]

def display(value):
    if value is None or value == '':
        return '—'
    if isinstance(value, Decimal):
        return 'R$ ' + f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    if isinstance(value, datetime):
        from django.utils.timezone import localtime
        return localtime(value).strftime('%d/%m/%Y · %H:%M')
    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')
    if isinstance(value, bool):
        return 'Sim' if value else 'Não'
    return str(value)

def object_rows(objects, config):
    rows = []
    for obj in objects:
        cells = []
        for field in config['columns']:
            method = getattr(obj, f'get_{field}_display', None)
            value = method() if method else getattr(obj, field)
            cells.append(display(value))
        rows.append({'object':obj, 'cells':cells})
    return rows

def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Conta criada. Seu espaço está pronto.')
        return redirect('dashboard')
    return render(request, 'registration/signup.html', {'form':form})

@login_required
def dashboard(request):
    return render(request, 'workspace/dashboard.html', dashboard_data(request.user))

@login_required
def records(request, kind):
    config = config_for(kind)
    objects = config['model'].objects.filter(owner=request.user)
    query = request.GET.get('q', '').strip()[:100]
    if query:
        condition = Q()
        for field in config['search']:
            condition |= Q(**{field+'__icontains':query})
        objects = objects.filter(condition)
    status = request.GET.get('status', '')
    if status and config.get('status'):
        objects = objects.filter(**{config['status']:status})
    page = Paginator(objects, 15).get_page(request.GET.get('page'))
    return render(request, 'workspace/list.html', {'kind':kind, 'config':config, 'rows':object_rows(page,config), 'page':page, 'query':query, 'status':status})

@login_required
def record_detail(request, kind, pk):
    config = config_for(kind)
    obj = get_object_or_404(config['model'], owner=request.user, pk=pk)
    fields = []
    for field in obj._meta.fields:
        if field.name not in ('owner','id'):
            method = getattr(obj, f'get_{field.name}_display', None)
            fields.append((field.verbose_name, display(method() if method else getattr(obj,field.name))))
    return render(request, 'workspace/detail.html', {'kind':kind, 'object':obj, 'config':config, 'fields':fields})

@login_required
def record_edit(request, kind, pk=None):
    config = config_for(kind)
    obj = get_object_or_404(config['model'], owner=request.user, pk=pk) if pk else config['model'](owner=request.user)
    Form = form_for(config['model'])
    if request.method == 'POST':
        # Serializing each owner's writes also closes booking races on PostgreSQL.
        # SQLite serializes writes itself; busy writes fail rather than double-book.
        from django.contrib.auth import get_user_model
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if pk:
                obj = get_object_or_404(config['model'], owner=request.user, pk=pk)
            form = Form(request.POST, instance=obj, user=request.user)
            if form.is_valid():
                try:
                    saved = form.save()
                    Event.objects.create(owner=request.user, description=f'{"Atualizou" if pk else "Criou"}: {saved}')
                    messages.success(request, 'Alterações salvas.')
                    return redirect('record-detail', kind=kind, pk=saved.pk)
                except ValidationError as exc:
                    form.add_error(None, exc)
    else:
        form = Form(instance=obj, user=request.user)
    return render(request, 'workspace/form.html', {'kind':kind, 'config':config, 'form':form, 'object':obj, 'editing':bool(pk)})

@login_required
def record_delete(request, kind, pk):
    config = config_for(kind)
    obj = get_object_or_404(config['model'], owner=request.user, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                label = str(obj)
                obj.delete()
                Event.objects.create(owner=request.user, description=f'Excluiu: {label}')
            messages.success(request, 'Registro excluído.')
            return redirect('records', kind=kind)
        except ProtectedError:
            messages.error(request, 'Este registro tem vínculos. Remova ou altere os registros associados primeiro.')
            return redirect('record-detail', kind=kind, pk=pk)
    return render(request, 'workspace/delete.html', {'kind':kind, 'object':obj})

@login_required
def export_csv(request, kind):
    config = config_for(kind)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="orvio-{kind}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(config['headers'])
    for row in object_rows(config['model'].objects.filter(owner=request.user), config):
        # Prevent spreadsheet formulas in user-supplied cells.
        writer.writerow([("'"+v if v.lstrip().startswith(('=','+','-','@','\t','\r')) else v) for v in row['cells']])
    return response

@login_required
@require_POST
def demo(request):
    from django.contrib.auth import get_user_model
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        if any(c['model'].objects.filter(owner=request.user).exists() for c in REGISTRY.values()):
            messages.info(request, 'Os dados de exemplo só podem ser adicionados a um espaço vazio.')
        else:
            seed_data(request.user)
            Event.objects.create(owner=request.user, description='Adicionou dados de demonstração')
            messages.success(request, 'Dados fictícios adicionados. Você pode editar e excluir todos eles.')
    return redirect('dashboard')

@login_required
def settings(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Senha atualizada.')
        return redirect('settings')
    return render(request, 'workspace/settings.html', {'form':form, 'events':Event.objects.filter(owner=request.user)[:15]})

@login_required
def overview_api(request):
    data = dashboard_data(request.user)
    return JsonResponse({'metrics':data['metrics'], 'series':data['series']})

def health(request):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    return JsonResponse({'status':'ok'})
