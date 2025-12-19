from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings

# ---------------------------
# Custom user manager
# ---------------------------
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not password:
            raise ValueError("Superuser должен иметь пароль")
        return self.create_user(email, password, **extra_fields)


# ---------------------------
# Role
# ---------------------------
class Role(models.Model):
    rolename = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.rolename

    class Meta:
        db_table = 'role'
        managed = True


# ---------------------------
# Custom User
# ---------------------------
class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    role = models.ForeignKey(Role, models.DO_NOTHING, blank=True, null=True)
    dateofbirth = models.DateField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "surname"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.name} {self.surname} <{self.email}>"

    class Meta:
        db_table = "User"
        managed = True


# ---------------------------
# Order
# ---------------------------
# from django.core.exceptions import ValidationError

# class Order(models.Model):
#     creationdate = models.DateTimeField(auto_now_add=True)
#     client = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders', null=True, blank=True, db_column='clientid')
#     car = models.ForeignKey('Car', on_delete=models.PROTECT, null=True, blank=True, db_column='carid')
#     master = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders_as_master', null=True, blank=True, db_column='masterid')
#     part = models.ForeignKey('Part', on_delete=models.PROTECT, null=False, blank=False, db_column='partid', default=5)
#     service = models.ForeignKey('Service', on_delete=models.PROTECT, null=False, blank=False, db_column='serviceid', default=1)
#     payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True, db_column='paymentid')
#     status = models.ForeignKey('Status', on_delete=models.PROTECT, null=True, blank=True, db_column='status')
#     notes = models.TextField(blank=True, null=True)

#     class Meta:
#         db_table = 'Order'
#         managed = True
#         ordering = ['-creationdate']

#     def __str__(self):
#         return f"Order #{self.pk} — {self.client or 'без клиента'}"

#     def clean(self):
#         if not self.part:
#             raise ValidationError("Необходимо указать запчасть.")
#         if not self.service:
#             raise ValidationError("Необходимо указать услугу.")

from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings

class Order(models.Model):
    creationdate = models.DateTimeField(auto_now_add=True, db_index=True)  # сортировка по дате
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        null=True,
        blank=True,
        db_column='clientid',
        db_index=True  # выборки по клиенту
    )
    car = models.ForeignKey(
        'Car',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column='carid',
        db_index=True  # выборки по машине
    )
    master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders_as_master',
        null=True,
        blank=True,
        db_column='masterid',
        db_index=True  # выборки по мастеру
    )
    part = models.ForeignKey(
        'Part',
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        db_column='partid',
        default=5,
        db_index=True  # выборки по запчасти
    )
    service = models.ForeignKey(
        'Service',
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        db_column='serviceid',
        default=1,
        db_index=True  # выборки по услуге
    )
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='paymentid',
        db_index=True  # выборки по оплате
    )
    status = models.ForeignKey(
        'Status',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column='status',
        db_index=True  # выборки по статусу
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Order'
        managed = True
        ordering = ['-creationdate']
        indexes = [
            models.Index(fields=['creationdate']),
            models.Index(fields=['client']),
            models.Index(fields=['master']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Order #{self.pk} — {self.client or 'без клиента'}"

    def clean(self):
        if not self.part:
            raise ValidationError("Необходимо указать запчасть.")
        if not self.service:
            raise ValidationError("Необходимо указать услугу.")


# ---------------------------
# Client
# ---------------------------
class Client(models.Model):
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    phone = models.CharField(unique=True, max_length=20)
    email = models.CharField(unique=True, max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.name} {self.surname}"

    class Meta:
        db_table = 'client'
        # managed = False


# ---------------------------
# Master
# ---------------------------
class Master(models.Model):
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    email = models.CharField(unique=True, max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.name} {self.surname}"

    class Meta:
        db_table = 'master'
        # managed = False


# ---------------------------
# Part
# ---------------------------
class Part(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='parts/', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'part'
        managed = True

# ---------------------------
# Service
# ---------------------------
class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'service'
        # managed = False


# ---------------------------
# Payment
# ---------------------------
class Payment(models.Model):
    date = models.DateTimeField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    paymentmethod = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.paymentmethod} ({self.amount})"

    class Meta:
        db_table = 'payment'
        # managed = False


# ---------------------------
# Status
# ---------------------------
class Status(models.Model):
    statusname = models.CharField(unique=True, max_length=50, blank=True, null=True)

    def __str__(self):
        return self.statusname

    class Meta:
        db_table = 'status'
        # managed = False


# ---------------------------
# Action log
# ---------------------------
class Actionlog(models.Model):
    userid = models.ForeignKey(User, models.DO_NOTHING, db_column='userid', blank=True, null=True)
    action = models.TextField(blank=True, null=True)
    action_timestamp = models.DateTimeField(blank=True, null=True)
    table_name = models.CharField(max_length=100, blank=True, null=True)
    operation = models.CharField(max_length=10, blank=True, null=True)
    row_id = models.IntegerField(blank=True, null=True)
    row_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.userid} — {self.action}"

    class Meta:
        db_table = 'actionlog'
        # managed = False


# ---------------------------
# Car
# ---------------------------
class Car(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='cars/', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'car'
        managed = True


# ---------------------------
# Clientarchive
# ---------------------------
class Clientarchive(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.name} {self.surname}"

    class Meta:
        db_table = 'clientarchive'
        # managed = False
