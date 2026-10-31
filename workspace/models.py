from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

class Owned(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, editable=False)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    class Meta:
        abstract = True
        ordering = ['-created_at', '-pk']

    def validate_owner(self, *relations):
        for relation in relations:
            if getattr(self, relation+'_id', None) and getattr(self, relation).owner_id != self.owner_id:
                raise ValidationError({relation:'O registro deve pertencer ao seu espaço.'})

class Event(Owned):
    description = models.CharField('ação', max_length=300)
    def __str__(self):
        return self.description


class Client(Owned):
    name = models.CharField('nome', max_length=120)
    email = models.EmailField('e-mail')
    phone = models.CharField('telefone', max_length=30)
    notes = models.TextField('observações', blank=True, max_length=3000)
    class Meta(Owned.Meta):
        constraints = [models.UniqueConstraint(fields=['owner','email'], name='unique_client_email')]
    def __str__(self):
        return self.name

class Service(Owned):
    name = models.CharField('serviço', max_length=100)
    duration = models.PositiveIntegerField('duração em minutos', default=60, validators=[MinValueValidator(5)])
    price = models.DecimalField('preço', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    description = models.TextField('descrição', blank=True, max_length=2000)
    class Meta(Owned.Meta):
        constraints = [models.CheckConstraint(condition=Q(duration__gte=5) & Q(duration__lte=480), name='valid_service_duration'), models.CheckConstraint(condition=Q(price__gte=0), name='nonnegative_service_price')]
    def clean(self):
        if self.duration is not None and self.duration > 480:
            raise ValidationError({'duration':'Use uma duração de até 480 minutos.'})
    def __str__(self):
        return self.name

class Appointment(Owned):
    STATUS = [('scheduled','Agendado'), ('confirmed','Confirmado'), ('completed','Concluído'), ('cancelled','Cancelado')]
    client = models.ForeignKey(Client, verbose_name='cliente', on_delete=models.PROTECT)
    service = models.ForeignKey(Service, verbose_name='serviço', on_delete=models.PROTECT)
    professional = models.CharField('profissional', max_length=100)
    start_at = models.DateTimeField('início')
    end_at = models.DateTimeField('fim', editable=False)
    price = models.DecimalField('preço combinado', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    status = models.CharField('status', choices=STATUS, max_length=15, default='scheduled')
    notes = models.TextField('observações', blank=True, max_length=2000)
    class Meta(Owned.Meta):
        ordering = ['start_at','pk']
        constraints = [models.CheckConstraint(condition=Q(end_at__gt=models.F('start_at')), name='appointment_positive_duration'), models.CheckConstraint(condition=Q(price__gte=0), name='nonnegative_appointment_price')]
        indexes = [models.Index(fields=['owner','professional','start_at','end_at'])]
    def clean(self):
        self.validate_owner('client','service')
        self.professional = ' '.join(self.professional.split()).title()
        if self.start_at and self.service_id:
            # Snapshot the duration. Editing a service must not rewrite old appointments.
            previous = Appointment.objects.filter(pk=self.pk).first() if self.pk else None
            changed = not previous or previous.start_at != self.start_at or previous.service_id != self.service_id
            if changed:
                self.end_at = self.start_at + timedelta(minutes=self.service.duration)
            if self.status != 'cancelled':
                overlap = Appointment.objects.filter(owner_id=self.owner_id, professional__iexact=self.professional, start_at__lt=self.end_at, end_at__gt=self.start_at).exclude(status='cancelled')
                if self.pk:
                    overlap = overlap.exclude(pk=self.pk)
                if overlap.exists():
                    raise ValidationError({'start_at':'Este profissional já tem um agendamento neste intervalo.'})
    def __str__(self):
        return f'{self.client} · {self.service}'
