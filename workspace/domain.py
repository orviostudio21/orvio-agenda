from datetime import datetime, timedelta, time
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from .models import *

def money(value):
    return 'R$ ' + f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def total(queryset, field):
    return queryset.aggregate(value=Sum(field))['value'] or Decimal('0')

def series(items):
    peak = max([float(value) for label,value in items] + [1])
    return [{'label':label, 'value':float(value), 'display':money(value), 'percent':round(float(value) / peak * 100, 2)} for label,value in items]

def panel_item(obj, title, subtitle, value='', status=''):
    return {'pk':obj.pk, 'title':title, 'subtitle':subtitle, 'value':value, 'status':status}

def config(model, label, singular, icon, columns, headers, search, status=None, help=''):
    return {'model':model, 'label':label, 'new_label':singular, 'icon':icon, 'columns':columns, 'headers':headers, 'search':search, 'status':status, 'choices':list(model._meta.get_field(status).choices) if status else [], 'help':help, 'numeric':[i for i,field in enumerate(columns) if field in ('value','amount','price','balance','opening_balance','duration','limit','spent')]}


REGISTRY = {
 'appointments':config(Appointment,'Agendamentos','Novo agendamento','◷',['client','service','professional','start_at','status'],['Cliente','Serviço','Profissional','Horário','Status'],['client__name','service__name','professional'],status='status',help='O horário final é calculado pela duração do serviço. Conflitos do mesmo profissional são bloqueados.'),
 'clients':config(Client,'Clientes','Novo cliente','◎',['name','email','phone'],['Nome','E-mail','Telefone'],['name','email','phone'],help='Cadastre quem será atendido antes de agendar.'),
 'services':config(Service,'Serviços','Novo serviço','◇',['name','duration','price'],['Serviço','Duração (min)','Preço'],['name'],help='Duração de 5 a 480 minutos. Alterações não mudam horários de agendamentos existentes.'),
}

def dashboard_data(user):
    today = timezone.localdate()
    appointments = Appointment.objects.filter(owner=user).select_related('client','service')
    active = appointments.exclude(status='cancelled')
    day = active.filter(start_at__date=today)
    week_end = today + timedelta(days=6)
    week = active.filter(start_at__date__range=(today,week_end))
    slots = [(today+timedelta(days=i), active.filter(start_at__date=today+timedelta(days=i)).count()) for i in range(7)]
    peak = max([count for date,count in slots]+[1])
    chart = [{'label':date.strftime('%d/%m'),'value':count,'display':str(count),'percent':count/peak*100} for date,count in slots]
    confirmed = day.filter(status='confirmed').count()
    return {'today':today,'heading':'Seu dia, no horário certo.','insight':f'{day.count()} atendimentos hoje. {confirmed} já confirmados.', 'empty':not appointments.exists() and not Client.objects.filter(owner=user).exists(), 'metrics':[
      {'label':'Atendimentos hoje','value':day.count(),'note':'Agendamentos sem cancelados'},
      {'label':'Próximos 7 dias','value':week.count(),'note':f'Até {week_end:%d/%m}'},
      {'label':'Valor previsto hoje','value':money(total(day,'price')),'note':'Soma dos preços combinados'},
      {'label':'Clientes cadastrados','value':Client.objects.filter(owner=user).count(),'note':'No seu espaço de atendimento'},
    ], 'chart_title':'Sua semana em atendimentos','chart_subtitle':'Hoje e os próximos seis dias, sem cancelamentos','chart_legend':'Agendamentos','series':chart,'panels':[
      {'title':'Na agenda de hoje','subtitle':'Horários e pessoas, em ordem','kind':'appointments','items':[panel_item(a,a.client.name,f'{a.service.name} · {a.professional}',timezone.localtime(a.start_at).strftime('%H:%M'),a.get_status_display()) for a in day[:6]]},
      {'title':'Seus serviços','subtitle':'Duração e preço de referência','kind':'services','items':[panel_item(s,s.name,f'{s.duration} minutos',money(s.price)) for s in Service.objects.filter(owner=user)[:5]]},
    ]}

def seed_data(user):
    today = timezone.localdate()
    clients = [Client.objects.create(owner=user,name=name,email=f'cliente{i}@example.com',phone=f'(11) 98888-00{i:02}') for i,name in enumerate(['Ana Ribeiro','Bruno Castro','Carolina Melo','Diego Ferreira','Elisa Teixeira','Fernanda Luz'])]
    services = [Service.objects.create(owner=user,name=name,duration=minutes,price=Decimal(price)) for name,minutes,price in [('Consultoria inicial',60,'180'),('Sessão de acompanhamento',45,'140'),('Planejamento personalizado',90,'280'),('Revisão de resultados',30,'100')]]
    for i in range(12):
        start = timezone.make_aware(datetime.combine(today+timedelta(days=i//3),time(9+(i%3)*2,0)))
        s = services[i%4]
        Appointment.objects.create(owner=user,client=clients[i%6],service=s,professional='Marina Duarte' if i%2 else 'Rafael Costa',start_at=start,end_at=start+timedelta(minutes=s.duration),price=s.price,status='confirmed' if i%3 else 'scheduled')
