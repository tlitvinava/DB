from django.shortcuts import render
from core.utils import is_client, is_master, is_admin
from django.forms.models import model_to_dict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Service, Part, Car

from django.contrib.auth.decorators import login_required, user_passes_test

def _readonly_for_user(user):
    return getattr(user, 'role', None) and user.role.rolename in ['client', 'master']



@login_required
@user_passes_test(is_client)
def client_dashboard(request):
    return render(request, "client_dashboard.html")

@login_required
@user_passes_test(is_master)
def master_dashboard(request):
    return render(request, "master_dashboard.html")

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    return render(request, "admin_dashboard.html")

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Order, Client, Car, Status

@login_required
def order_list(request):
    orders = Order.objects.all()
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related(
            "client", "car", "master", "part", "payment", "service", "status"
        ),
        pk=pk
    )
    return render(request, "orders/order_detail.html", {"order": order})


from .forms import OrderForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from core.models import Order, Status
from core.forms import OrderForm

from django.contrib import messages

@login_required
def order_create(request):
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.client = request.user
            order.creationdate = timezone.now()
            try:
                order.status_id = 2 
            except Status.DoesNotExist:
                messages.error(request, "Статус 'в обработке' не найден.")
                return render(request, "orders/order_form.html", {"form": form})
            order.save()
            messages.success(request, "Заказ успешно создан.")
            
            Actionlog.objects.create(
                userid=request.user if request.user.is_authenticated else None,
                action=f"Создан заказ #{order.pk}",
                action_timestamp=timezone.now(),
                table_name="Order",
                operation="insert",
                row_id=order.pk,
                row_data=model_to_dict(order)
            )
            
            return redirect("client_orders")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле {field}: {error}")
    else:
        form = OrderForm()
    return render(request, "orders/order_form.html", {"form": form})


@login_required
def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.status = request.POST.get("status")
        order.save()
        return redirect("order_detail", pk=order.pk)
    return render(request, "orders/order_form.html", {"order": order})

@login_required
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.delete()
    return redirect("order_list")


from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return render(request, 'home.html', {
        'username': request.user.name 
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Sum
from django.forms import ModelForm
from django.core.paginator import Paginator

from .decorators import admin_required
from .models import (
    Master, Part, Service, Status, Payment, Car,
    Order, Actionlog, User
)


class MasterForm(ModelForm):
    class Meta:
        model = Master
        fields = ['name', 'surname', 'email']


class PartForm(ModelForm):
    class Meta:
        model = Part
        fields = ['name', 'description', 'price', 'image']

class ServiceForm(ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price']


class StatusForm(ModelForm):
    class Meta:
        model = Status
        fields = ['statusname']


class PaymentForm(ModelForm):
    class Meta:
        model = Payment
        fields = ['paymentmethod']


class CarForm(ModelForm):
    class Meta:
        model = Car
        fields = ['name', 'description', 'image']

def log_action(user, table_name, operation, row_id=None, row_data=None):
    try:
        Actionlog.objects.create(
            userid=user if user.is_authenticated else None,
            action=f"{operation} on {table_name}",
            action_timestamp=timezone.now(),
            table_name=table_name,
            operation=operation,
            row_id=row_id,
            row_data=row_data or {}
        )
    except Exception:
        pass


@admin_required
def admin_panel(request):
    stats = {
        'orders_count': Order.objects.count(),
        'masters_count': User.objects.filter(role_id=2).count(),
        'parts_count': Part.objects.count(),
        'services_count': Service.objects.count(),
        'cars_count': Car.objects.count(),
    }
    return render(request, 'admin_panel/admin_panel.html', {'stats': stats})


def paginate_queryset(request, queryset, per_page=5):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


@admin_required
def masters_list(request):
    qs = Master.objects.all().order_by('surname', 'name')
    page = paginate_queryset(request, qs, per_page=5)
    return render(request, 'admin_panel/masters_list.html', {'page': page})


@admin_required
def master_create(request):
    if request.method == 'POST':
        form = MasterForm(request.POST)
        if form.is_valid():
            master = form.save()
            log_action(request.user, 'master', 'create', row_id=master.pk, row_data={'name': master.name, 'surname': master.surname})
            messages.success(request, 'Мастер создан')
            return redirect('masters_list')
    else:
        form = MasterForm()
    return render(request, 'admin_panel/master_form.html', {'form': form, 'action': 'Создать'})


@admin_required
def master_edit(request, pk):
    master = get_object_or_404(Master, pk=pk)
    if request.method == 'POST':
        form = MasterForm(request.POST, instance=master)
        if form.is_valid():
            master = form.save()
            log_action(request.user, 'master', 'update', row_id=master.pk, row_data={'name': master.name, 'surname': master.surname})
            messages.success(request, 'Мастер обновлён')
            return redirect('masters_list')
    else:
        form = MasterForm(instance=master)
    return render(request, 'admin_panel/master_form.html', {'form': form, 'action': 'Редактировать'})


@admin_required
def master_delete(request, pk):
    master = get_object_or_404(Master, pk=pk)
    if request.method == 'POST':
        row_data = {'name': master.name, 'surname': master.surname}
        master.delete()
        log_action(request.user, 'master', 'delete', row_data=row_data)
        messages.success(request, 'Мастер удалён')
        return redirect('masters_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': master, 'type': 'Мастер'})


# -------------------------
# Parts CRUD
# -------------------------
# # Parts
# @login_required
# def parts_list(request):
#     qs = Part.objects.all().order_by('name')
#     page = paginate_queryset(request, qs, per_page=5)
#     readonly = _readonly_for_user(request.user)
#     return render(request, 'admin_panel/parts_list.html', {'page': page})

@login_required
def parts_list(request):
    query = request.GET.get("q")
    sort = request.GET.get("sort")

    qs = Part.objects.all()

    if query:
        qs = qs.filter(name__icontains=query)

    if sort == "desc":
        qs = qs.order_by("-name")
    else:
        qs = qs.order_by("name")

    page = paginate_queryset(request, qs, per_page=5)
    readonly = _readonly_for_user(request.user)
    return render(request, "admin_panel/parts_list.html", {"page": page, "query": query, "sort": sort})

@admin_required
def part_create(request):
    if request.method == 'POST':
        form = PartForm(request.POST, request.FILES)  
        if form.is_valid():
            part = form.save()
            log_action(request.user, 'part', 'create', row_id=part.pk, row_data={'name': part.name})
            messages.success(request, 'Запчасть создана')
            return redirect('parts_list')
    else:
        form = PartForm()
    return render(request, 'admin_panel/part_form.html', {'form': form, 'action': 'Создать'})


@admin_required
def part_edit(request, pk):
    part = get_object_or_404(Part, pk=pk)
    if request.method == 'POST':
        form = PartForm(request.POST, request.FILES, instance=part)  
        if form.is_valid():
            part = form.save()
            log_action(request.user, 'part', 'update', row_id=part.pk, row_data={'name': part.name})
            messages.success(request, 'Запчасть обновлена')
            return redirect('parts_list')
    else:
        form = PartForm(instance=part)
    return render(request, 'admin_panel/part_form.html', {'form': form, 'action': 'Редактировать'})



@admin_required
def part_delete(request, pk):
    part = get_object_or_404(Part, pk=pk)
    if request.method == 'POST':
        row_data = {'name': part.name}
        part.delete()
        log_action(request.user, 'part', 'delete', row_data=row_data)
        messages.success(request, 'Запчасть удалена')
        return redirect('parts_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': part, 'type': 'Запчасть'})


# -------------------------
# Services CRUD
# -------------------------
# # Services
# @login_required
# def services_list(request):
#     qs = Service.objects.all().order_by('name')
#     page = paginate_queryset(request, qs, per_page=5)
#     readonly = _readonly_for_user(request.user)
#     return render(request, 'admin_panel/services_list.html', {'page': page})

@login_required
def services_list(request):
    query = request.GET.get("q")
    sort = request.GET.get("sort")

    qs = Service.objects.all()

    if query:
        qs = qs.filter(name__icontains=query)

    if sort == "desc":
        qs = qs.order_by("-name")
    else:  
        qs = qs.order_by("name")

    page = paginate_queryset(request, qs, per_page=5)
    readonly = _readonly_for_user(request.user)
    return render(request, "admin_panel/services_list.html", {"page": page, "query": query, "sort": sort})

@admin_required
def service_create(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            log_action(request.user, 'service', 'create', row_id=service.pk, row_data={'name': service.name})
            messages.success(request, 'Услуга создана')
            return redirect('services_list')
    else:
        form = ServiceForm()
    return render(request, 'admin_panel/service_form.html', {'form': form, 'action': 'Создать'})


@admin_required
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            service = form.save()
            log_action(request.user, 'service', 'update', row_id=service.pk, row_data={'name': service.name})
            messages.success(request, 'Услуга обновлена')
            return redirect('services_list')
    else:
        form = ServiceForm(instance=service)
    return render(request, 'admin_panel/service_form.html', {'form': form, 'action': 'Редактировать'})


@admin_required
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        row_data = {'name': service.name}
        service.delete()
        log_action(request.user, 'service', 'delete', row_data=row_data)
        messages.success(request, 'Услуга удалена')
        return redirect('services_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': service, 'type': 'Услуга'})


@admin_required
def statuses_list(request):
    qs = Status.objects.all().order_by('statusname')
    page = paginate_queryset(request, qs, per_page=5)
    return render(request, 'admin_panel/statuses_list.html', {'page': page})


@admin_required
def status_create(request):
    if request.method == 'POST':
        form = StatusForm(request.POST)
        if form.is_valid():
            status = form.save()
            log_action(request.user, 'status', 'create', row_id=status.pk, row_data={'statusname': status.statusname})
            messages.success(request, 'Статус создан')
            return redirect('statuses_list')
    else:
        form = StatusForm()
    return render(request, 'admin_panel/status_form.html', {'form': form, 'action': 'Создать'})


@admin_required
def status_edit(request, pk):
    status = get_object_or_404(Status, pk=pk)
    if request.method == 'POST':
        form = StatusForm(request.POST, instance=status)
        if form.is_valid():
            status = form.save()
            log_action(request.user, 'status', 'update', row_id=status.pk, row_data={'statusname': status.statusname})
            messages.success(request, 'Статус обновлён')
            return redirect('statuses_list')
    else:
        form = StatusForm(instance=status)
    return render(request, 'admin_panel/status_form.html', {'form': form, 'action': 'Редактировать'})


@admin_required
def status_delete(request, pk):
    status = get_object_or_404(Status, pk=pk)
    if request.method == 'POST':
        row_data = {'statusname': status.statusname}
        status.delete()
        log_action(request.user, 'status', 'delete', row_data=row_data)
        messages.success(request, 'Статус удалён')
        return redirect('statuses_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': status, 'type': 'Статус'})


# @admin_required
# def payments_list(request):
#     qs = Payment.objects.all().order_by('-date')
#     page = paginate_queryset(request, qs, per_page=5)
#     return render(request, 'admin_panel/payments_list.html', {'page': page})



# @admin_required
# def payment_create(request):
#     if request.method == 'POST':
#         form = PaymentForm(request.POST)
#         if form.is_valid():
#             payment = form.save()
#             log_action(request.user, 'payment', 'create', row_id=payment.pk, row_data={'amount': str(payment.amount)})
#             messages.success(request, 'Платёж создан')
#             return redirect('payments_list')
#     else:
#         form = PaymentForm()
#     return render(request, 'admin_panel/payment_form.html', {'form': form, 'action': 'Создать'})


# @admin_required
# def payment_edit(request, pk):
#     payment = get_object_or_404(Payment, pk=pk)
#     if request.method == 'POST':
#         form = PaymentForm(request.POST, instance=payment)
#         if form.is_valid():
#             payment = form.save()
#             log_action(request.user, 'payment', 'update', row_id=payment.pk, row_data={'amount': str(payment.amount)})
#             messages.success(request, 'Платёж обновлён')
#             return redirect('payments_list')
#     else:
#         form = PaymentForm(instance=payment)
#     return render(request, 'admin_panel/payment_form.html', {'form': form, 'action': 'Редактировать'})


# @admin_required
# def payment_delete(request, pk):
#     payment = get_object_or_404(Payment, pk=pk)
#     if request.method == 'POST':
#         row_data = {'amount': str(payment.amount)}
#         payment.delete()
#         log_action(request.user, 'payment', 'delete', row_data=row_data)
#         messages.success(request, 'Платёж удалён')
#         return redirect('payments_list')
#     return render(request, 'admin_panel/confirm_delete.html', {'object': payment, 'type': 'Платёж'})

@admin_required
def payments_list(request):
    """
    Список платежей. Сортировка по названию метода оплаты.
    """
    qs = Payment.objects.all().order_by('paymentmethod')
    page = paginate_queryset(request, qs, per_page=5)
    return render(request, 'admin_panel/payments_list.html', {'page': page})


@admin_required
def payment_create(request):
    """
    Создание платежа — сохраняем только paymentmethod.
    """
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            # логируем метод оплаты
            log_action(
                request.user,
                'payment',
                'create',
                row_id=payment.pk,
                row_data={'paymentmethod': payment.paymentmethod}
            )
            messages.success(request, 'Платёж создан')
            return redirect('payments_list')
    else:
        form = PaymentForm()
    return render(request, 'admin_panel/payment_form.html', {'form': form, 'action': 'Создать'})


@admin_required
def payment_edit(request, pk):
    """
    Редактирование платежа — только метод оплаты.
    """
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save()
            log_action(
                request.user,
                'payment',
                'update',
                row_id=payment.pk,
                row_data={'paymentmethod': payment.paymentmethod}
            )
            messages.success(request, 'Платёж обновлён')
            return redirect('payments_list')
    else:
        form = PaymentForm(instance=payment)
    return render(request, 'admin_panel/payment_form.html', {'form': form, 'action': 'Редактировать'})


@admin_required
def payment_delete(request, pk):
    """
    Удаление платежа — логируем метод оплаты перед удалением.
    """
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        row_data = {'paymentmethod': payment.paymentmethod}
        payment.delete()
        log_action(request.user, 'payment', 'delete', row_data=row_data)
        messages.success(request, 'Платёж удалён')
        return redirect('payments_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': payment, 'type': 'Платёж'})

@login_required
def cars_list(request):
    query = request.GET.get("q")
    sort = request.GET.get("sort")

    qs = Car.objects.all()

    if query:
        qs = qs.filter(name__icontains=query)

    if sort == "desc":
        qs = qs.order_by("-name")
    else:
        qs = qs.order_by("name")

    page = paginate_queryset(request, qs, per_page=5)
    readonly = _readonly_for_user(request.user)
    return render(request, "admin_panel/cars_list.html", {"page": page, "query": query, "sort": sort})

@admin_required
def car_create(request):
    if request.method == 'POST':
        form = CarForm(request.POST, request.FILES)  
        if form.is_valid():
            car = form.save()
            log_action(request.user, 'car', 'create', row_id=car.pk, row_data={'name': car.name})
            messages.success(request, 'Машина создана')
            return redirect('cars_list')
    else:
        form = CarForm()
    return render(request, 'admin_panel/car_form.html', {'form': form, 'action': 'Создать'})


@admin_required
def car_edit(request, pk):
    car = get_object_or_404(Car, pk=pk)
    if request.method == 'POST':
        form = CarForm(request.POST, request.FILES, instance=car) 
        if form.is_valid():
            car = form.save()
            log_action(request.user, 'car', 'update', row_id=car.pk, row_data={'name': car.name})
            messages.success(request, 'Машина обновлена')
            return redirect('cars_list')
    else:
        form = CarForm(instance=car)
    return render(request, 'admin_panel/car_form.html', {'form': form, 'action': 'Редактировать'})


@admin_required
def car_delete(request, pk):
    car = get_object_or_404(Car, pk=pk)
    if request.method == 'POST':
        row_data = {'name': car.name}
        car.delete()
        log_action(request.user, 'car', 'delete', row_data=row_data)
        messages.success(request, 'Машина удалена')
        return redirect('cars_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': car, 'type': 'Машина'})


from django.contrib.auth import get_user_model
from django.db.models import Count
from core.models import Order

User = get_user_model()

@admin_required
def statistics(request):
    orders_count = Order.objects.count()
    orders_by_status = (
        Order.objects
        .values('status__statusname')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    top_masters = (
        Order.objects
        .filter(master__role_id=2)
        .values('master__id', 'master__name', 'master__surname')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    context = {
        'orders_count': orders_count,
        'orders_by_status': orders_by_status,
        'top_masters': top_masters,
    }
    return render(request, 'admin_panel/statistics.html', context)


# @admin_required
# def logs(request):
#     qs = Actionlog.objects.all().order_by('-action_timestamp')
#     page = paginate_queryset(request, qs, per_page=50)
#     return render(request, 'admin_panel/logs.html', {'page': page})

@admin_required
def logs(request):
    qs = Actionlog.objects.select_related("userid").order_by('-action_timestamp')
    page = paginate_queryset(request, qs, per_page=50)
    return render(request, 'admin_panel/logs.html', {'page': page})


@login_required
@user_passes_test(is_client)
def client_dashboard(request):
    orders = Order.objects.filter(clientid=request.user).select_related('car', 'status')

    return render(request, "client_dashboard.html", {
        "orders": orders
    })


from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.http import HttpResponseForbidden
from core.models import Order

@login_required
def master_orders(request):
    user = request.user
    if getattr(user, 'role_id', None) != 2:
        return HttpResponseForbidden("Доступ разрешён только мастерам.")

    orders_qs = (
        Order.objects
        .select_related('car', 'client', 'status', 'service', 'part')
        .filter(master_id=user.id)  
        .order_by('-creationdate')
    )

    paginator = Paginator(orders_qs, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)

    return render(request, 'master/orders_list.html', {'orders': orders})


from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from core.models import Order, Status

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from core.models import Order, Status

@login_required
def admin_orders(request):
    user = request.user
    if getattr(user, 'role_id', None) != 1:
        return HttpResponseForbidden("Доступ разрешён только администратору.")

    
    orders = Order.objects.select_related(
        'client', 'car', 'status', 'service', 'part', 'master'
    ).order_by('-creationdate')

    return render(request, 'admin_panel/admin_orders.html', {'orders': orders})


@login_required
def change_order_status(request, order_id):
    user = request.user
    if getattr(user, 'role_id', None) != 1:
        return HttpResponseForbidden("Доступ разрешён только администратору.")

    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        new_status_id = request.POST.get("status_id")
        if new_status_id:
            order.status_id = new_status_id
            order.save()
            return redirect('admin_orders')

    statuses = Status.objects.all()
    return render(request, 'admin_panel/change_status.html', {'order': order, 'statuses': statuses})


from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def masters_list(request):
    masters_qs = User.objects.filter(role_id=2).order_by('surname', 'name')
    paginator = Paginator(masters_qs, 10) 
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    return render(request, "admin_panel/masters_list.html", {"page": page})


from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from core.models import Order

@login_required
def client_orders(request):
    user = request.user
    if getattr(user, 'role_id', None) != 3:
        return HttpResponseForbidden("Доступ разрешён только клиентам.")

    orders_qs = (
        Order.objects
        .select_related('car', 'status', 'service', 'part', 'master')
        .filter(client_id=user.id)  
        .order_by('-creationdate')
    )

    return render(request, 'client/orders_list.html', {'orders': orders_qs})

# 
# from django.shortcuts import render, redirect, get_object_or_404
# from django.db import connection, transaction, IntegrityError
# from django.utils import timezone
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required, user_passes_test
# from django.forms import ModelForm
# from django.core.paginator import Paginator
# from django.http import Http404, HttpResponseForbidden
# from django.core.files.storage import default_storage
# from django.core.files.base import ContentFile
# from django.contrib.auth import get_user_model
# import json

# from core.utils import is_client, is_master, is_admin
# from core.forms import OrderForm

# User = get_user_model()

# from django.forms import ModelForm
# from .models import Master, Part, Service, Status, Payment, Car

# class MasterForm(ModelForm):
#     class Meta:
#         model = Master
#         fields = ['name', 'surname', 'email']


# class PartForm(ModelForm):
#     class Meta:
#         model = Part
#         fields = ['name', 'description', 'price', 'image']


# class ServiceForm(ModelForm):
#     class Meta:
#         model = Service
#         fields = ['name', 'description', 'price']


# class StatusForm(ModelForm):
#     class Meta:
#         model = Status
#         fields = ['statusname']


# class PaymentForm(ModelForm):
#     class Meta:
#         model = Payment
#         fields = ['date', 'amount', 'paymentmethod']


# class CarForm(ModelForm):
#     class Meta:
#         model = Car
#         fields = ['name', 'description', 'image']


# def dictfetchall(cursor):
#     cols = [c[0] for c in cursor.description]
#     return [dict(zip(cols, row)) for row in cursor.fetchall()]

# def dictfetchone(cursor):
#     row = cursor.fetchone()
#     if row is None:
#         return None
#     cols = [c[0] for c in cursor.description]
#     return dict(zip(cols, row))

# def save_uploaded_file(f):
#     if not f:
#         return None
#     path = default_storage.save(f.name, ContentFile(f.read()))
#     return path

# def log_action_sql(user, table_name, operation, row_id=None, row_data=None):
#     try:
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 INSERT INTO actionlog
#                 (userid, action, action_timestamp, table_name, operation, row_id, row_data)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s)
#             """, [
#                 user.id if getattr(user, "is_authenticated", False) else None,
#                 f"{operation} on {table_name}",
#                 timezone.now(),
#                 table_name,
#                 operation,
#                 row_id,
#                 json.dumps(row_data or {}, default=str)
#             ])
#     except Exception:
#         pass


# @login_required
# @user_passes_test(is_client)
# def client_dashboard(request):
#     return render(request, "client_dashboard.html")

# @login_required
# @user_passes_test(is_master)
# def master_dashboard(request):
#     return render(request, "master_dashboard.html")

# @login_required
# @user_passes_test(is_admin)
# def admin_dashboard(request):
#     return render(request, "admin_dashboard.html")


# @login_required
# def order_list(request):
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT o.id, o.creationdate, o.clientid, "User".name AS client_name, "User".surname AS client_surname,
#                    o.carid, o.masterid, m.name AS master_name, m.surname AS master_surname,
#                    o.partid, p.name AS part_name, o.serviceid, s.name AS service_name,
#                    o.status, st.statusname, o.notes, o.total_cost
#             FROM "Order" o
#             LEFT JOIN "User" ON o.clientid = "User".id
#             LEFT JOIN master m ON o.masterid = m.id
#             LEFT JOIN part p ON o.partid = p.id
#             LEFT JOIN service s ON o.serviceid = s.id
#             LEFT JOIN status st ON o.status = st.id
#             ORDER BY o.creationdate DESC
#         """)
#         orders = dictfetchall(cursor)
#     return render(request, "orders/order_list.html", {"orders": orders})


# @login_required
# def order_detail(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT o.id, o.creationdate, o.clientid, "User".name AS client_name, "User".surname AS client_surname,
#                    o.carid, o.masterid, m.name AS master_name, m.surname AS master_surname,
#                    o.partid, p.name AS part_name, p.price AS part_price,
#                    o.serviceid, s.name AS service_name, s.price AS service_price,
#                    o.status, st.statusname, o.notes, o.total_cost
#             FROM "Order" o
#             LEFT JOIN "User" ON o.clientid = "User".id
#             LEFT JOIN master m ON o.masterid = m.id
#             LEFT JOIN part p ON o.partid = p.id
#             LEFT JOIN service s ON o.serviceid = s.id
#             LEFT JOIN status st ON o.status = st.id
#             WHERE o.id = %s
#         """, [pk])
#         order = dictfetchone(cursor)
#     if not order:
#         raise Http404("Заказ не найден")
#     return render(request, "orders/order_detail.html", {"order": order})


# @login_required
# def order_create(request):
#     if request.method == "POST":
#         form = OrderForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             carid = data.get("car")
#             masterid = data.get("master")
#             partid = data.get("part")
#             serviceid = data.get("service")
#             notes = data.get("notes") or ""
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             SELECT p.price AS part_price, s.price AS service_price
#                             FROM (SELECT %s::int AS partid) AS inp
#                             LEFT JOIN part p ON p.id = inp.partid
#                             LEFT JOIN service s ON s.id = %s::int
#                         """, [partid or None, serviceid])
#                         prices = dictfetchone(cursor) or {}
#                         part_price = prices.get("part_price") or 0
#                         service_price = prices.get("service_price") or 0
#                         total_cost = float(part_price) + float(service_price)

#                         cursor.execute("""
#                             INSERT INTO "Order"
#                             (creationdate, clientid, carid, masterid, partid, serviceid, status, notes, total_cost)
#                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#                             RETURNING id
#                         """, [
#                             timezone.now(), request.user.id, carid or None, masterid or None,
#                             partid or None, serviceid, 2, notes, total_cost
#                         ])
#                         new_id = cursor.fetchone()[0]

#                         row_data = {
#                             "id": new_id, "clientid": request.user.id, "carid": carid,
#                             "masterid": masterid, "partid": partid, "serviceid": serviceid,
#                             "status": 2, "notes": notes, "total_cost": total_cost
#                         }
#                         cursor.execute("""
#                             INSERT INTO actionlog
#                             (userid, action, action_timestamp, table_name, operation, row_id, row_data)
#                             VALUES (%s, %s, %s, %s, %s, %s, %s)
#                         """, [
#                             request.user.id,
#                             f"Создан заказ #{new_id}",
#                             timezone.now(),
#                             "Order",
#                             "insert",
#                             new_id,
#                             json.dumps(row_data, default=str)
#                         ])
#                 messages.success(request, "Заказ успешно создан.")
#                 return redirect("order_list")
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при создании заказа: {e}")
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f"Ошибка в поле {field}: {error}")
#     else:
#         form = OrderForm()
#     return render(request, "orders/order_form.html", {"form": form})


# @login_required
# def order_update(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute('SELECT id, status, notes FROM "Order" WHERE id = %s', [pk])
#         order = dictfetchone(cursor)
#     if not order:
#         raise Http404("Заказ не найден")

#     if request.method == "POST":
#         new_status = request.POST.get("status") or order["status"]
#         new_notes = request.POST.get("notes", order.get("notes", ""))
#         try:
#             with transaction.atomic():
#                 with connection.cursor() as cursor:
#                     cursor.execute("""
#                         UPDATE "Order"
#                         SET status = %s, notes = %s
#                         WHERE id = %s
#                     """, [new_status, new_notes, pk])
#                     cursor.execute("""
#                         INSERT INTO actionlog
#                         (userid, action, action_timestamp, table_name, operation, row_id, row_data)
#                         VALUES (%s, %s, %s, %s, %s, %s, %s)
#                     """, [
#                         request.user.id,
#                         f"Обновлён заказ #{pk}",
#                         timezone.now(),
#                         "Order",
#                         "update",
#                         pk,
#                         json.dumps({"status": new_status, "notes": new_notes}, default=str)
#                     ])
#             return redirect("order_detail", pk=pk)
#         except IntegrityError as e:
#             messages.error(request, f"Ошибка при обновлении: {e}")

#     return render(request, "orders/order_form.html", {"order": order})


# @login_required
# def order_delete(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute('SELECT id FROM "Order" WHERE id = %s', [pk])
#         if cursor.fetchone() is None:
#             raise Http404("Заказ не найден")

#     if request.method == "POST":
#         try:
#             with transaction.atomic():
#                 with connection.cursor() as cursor:
#                     cursor.execute('SELECT id, clientid, total_cost FROM "Order" WHERE id = %s', [pk])
#                     row = dictfetchone(cursor)
#                     cursor.execute('DELETE FROM "Order" WHERE id = %s', [pk])
#                     cursor.execute("""
#                         INSERT INTO actionlog
#                         (userid, action, action_timestamp, table_name, operation, row_id, row_data)
#                         VALUES (%s, %s, %s, %s, %s, %s, %s)
#                     """, [
#                         request.user.id,
#                         f"Удалён заказ #{pk}",
#                         timezone.now(),
#                         "Order",
#                         "delete",
#                         pk,
#                         json.dumps(row or {}, default=str)
#                     ])
#             return redirect("order_list")
#         except IntegrityError as e:
#             messages.error(request, f"Ошибка при удалении: {e}")
#     return render(request, "orders/confirm_delete.html", {"object": {"id": pk}})


# @login_required
# def home(request):
#     return render(request, 'home.html', {
#         'username': getattr(request.user, 'name', request.user.username)
#     })


# @login_required
# def admin_panel(request):
#     with connection.cursor() as cursor:
#         cursor.execute('SELECT COUNT(*) FROM "Order"')
#         orders_count = cursor.fetchone()[0]
#         cursor.execute('SELECT COUNT(*) FROM "User" WHERE role_id = 2')
#         masters_count = cursor.fetchone()[0]
#         cursor.execute('SELECT COUNT(*) FROM part')
#         parts_count = cursor.fetchone()[0]
#         cursor.execute('SELECT COUNT(*) FROM service')
#         services_count = cursor.fetchone()[0]
#         cursor.execute('SELECT COUNT(*) FROM car')
#         cars_count = cursor.fetchone()[0]
#     stats = {
#         'orders_count': orders_count,
#         'masters_count': masters_count,
#         'parts_count': parts_count,
#         'services_count': services_count,
#         'cars_count': cars_count,
#     }
#     return render(request, 'admin_panel/admin_panel.html', {'stats': stats})


# @login_required
# def masters_list(request):
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT id, name, surname, email
#             FROM master
#             ORDER BY surname, name
#         """)
#         rows = dictfetchall(cursor)
#     page = paginate_queryset(rows, per_page=5, request=request)
#     return render(request, 'admin_panel/masters_list.html', {'page': page})


# @login_required
# def master_create(request):
#     if request.method == 'POST':
#         form = MasterForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             INSERT INTO master (name, surname, email)
#                             VALUES (%s, %s, %s)
#                             RETURNING id
#                         """, [data['name'], data['surname'], data['email']])
#                         new_id = cursor.fetchone()[0]
#                         log_action_sql(request.user, 'master', 'create', row_id=new_id, row_data={'name': data['name'], 'surname': data['surname']})
#                 messages.success(request, 'Мастер создан')
#                 return redirect('masters_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при создании мастера: {e}")
#     else:
#         form = MasterForm()
#     return render(request, 'admin_panel/master_form.html', {'form': form, 'action': 'Создать'})


# @login_required
# def master_edit(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, name, surname, email FROM master WHERE id = %s", [pk])
#         master = dictfetchone(cursor)
#     if not master:
#         raise Http404("Мастер не найден")
#     if request.method == 'POST':
#         form = MasterForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             UPDATE master
#                             SET name = %s, surname = %s, email = %s
#                             WHERE id = %s
#                         """, [data['name'], data['surname'], data['email'], pk])
#                         log_action_sql(request.user, 'master', 'update', row_id=pk, row_data={'name': data['name'], 'surname': data['surname']})
#                 messages.success(request, 'Мастер обновлён')
#                 return redirect('masters_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при обновлении мастера: {e}")
#     else:
#         form = MasterForm(initial=master)
#     return render(request, 'admin_panel/master_form.html', {'form': form, 'action': 'Редактировать'})


# @login_required
# def master_delete(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, name, surname FROM master WHERE id = %s", [pk])
#         master = dictfetchone(cursor)
#     if not master:
#         raise Http404("Мастер не найден")
#     if request.method == 'POST':
#         try:
#             with transaction.atomic():
#                 with connection.cursor() as cursor:
#                     cursor.execute("DELETE FROM master WHERE id = %s", [pk])
#                     log_action_sql(request.user, 'master', 'delete', row_data={'name': master['name'], 'surname': master['surname']})
#             messages.success(request, 'Мастер удалён')
#             return redirect('masters_list')
#         except IntegrityError as e:
#             messages.error(request, f"Ошибка при удалении мастера: {e}")
#     return render(request, 'admin_panel/confirm_delete.html', {'object': master, 'type': 'Мастер'})


# @login_required
# def parts_list(request):
#     query = request.GET.get("q")
#     sort = request.GET.get("sort")
#     sql = "SELECT id, name, description, price, image FROM part"
#     params = []
#     if query:
#         sql += " WHERE name ILIKE %s"
#         params.append(f"%{query}%")
#     if sort == "desc":
#         sql += " ORDER BY name DESC"
#     else:
#         sql += " ORDER BY name"
#     with connection.cursor() as cursor:
#         cursor.execute(sql, params)
#         rows = dictfetchall(cursor)
#     page = paginate_queryset(rows, per_page=5, request=request)
#     readonly = getattr(request.user, 'role', None) and request.user.role.rolename in ['client', 'master']
#     return render(request, "admin_panel/parts_list.html", {"page": page, "query": query, "sort": sort})


# @login_required
# def part_create(request):
#     if request.method == 'POST':
#         form = PartForm(request.POST, request.FILES)
#         if form.is_valid():
#             data = form.cleaned_data
#             image_path = None
#             if request.FILES.get('image'):
#                 image_path = save_uploaded_file(request.FILES['image'])
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             INSERT INTO part (name, description, price, image)
#                             VALUES (%s, %s, %s, %s)
#                             RETURNING id
#                         """, [data['name'], data.get('description'), data.get('price'), image_path])
#                         new_id = cursor.fetchone()[0]
#                         log_action_sql(request.user, 'part', 'create', row_id=new_id, row_data={'name': data['name']})
#                 messages.success(request, 'Запчасть создана')
#                 return redirect('parts_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при создании запчасти: {e}")
#     else:
#         form = PartForm()
#     return render(request, 'admin_panel/part_form.html', {'form': form, 'action': 'Создать'})


# @login_required
# def part_edit(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, name, description, price, image FROM part WHERE id = %s", [pk])
#         part = dictfetchone(cursor)
#     if not part:
#         raise Http404("Запчасть не найдена")
#     if request.method == 'POST':
#         form = PartForm(request.POST, request.FILES)
#         if form.is_valid():
#             data = form.cleaned_data
#             image_path = part.get('image')
#             if request.FILES.get('image'):
#                 image_path = save_uploaded_file(request.FILES['image'])
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             UPDATE part
#                             SET name = %s, description = %s, price = %s, image = %s
#                             WHERE id = %s
#                         """, [data['name'], data.get('description'), data.get('price'), image_path, pk])
#                         log_action_sql(request.user, 'part', 'update', row_id=pk, row_data={'name': data['name']})
#                 messages.success(request, 'Запчасть обновлена')
#                 return redirect('parts_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при обновлении запчасти: {e}")
#     else:
#         form = PartForm(initial=part)
#     return render(request, 'admin_panel/part_form.html', {'form': form, 'action': 'Редактировать'})


# @login_required
# def part_delete(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, name FROM part WHERE id = %s", [pk])
#         part = dictfetchone(cursor)
#     if not part:
#         raise Http404("Запчасть не найдена")
#     if request.method == 'POST':
#         try:
#             with transaction.atomic():
#                 with connection.cursor() as cursor:
#                     cursor.execute("DELETE FROM part WHERE id = %s", [pk])
#                     log_action_sql(request.user, 'part', 'delete', row_data={'name': part['name']})
#             messages.success(request, 'Запчасть удалена')
#             return redirect('parts_list')
#         except IntegrityError as e:
#             messages.error(request, f"Ошибка при удалении запчасти: {e}")
#     return render(request, 'admin_panel/confirm_delete.html', {'object': part, 'type': 'Запчасть'})


# @login_required
# def services_list(request):
#     query = request.GET.get("q")
#     sort = request.GET.get("sort")
#     sql = "SELECT id, name, description, price FROM service"
#     params = []
#     if query:
#         sql += " WHERE name ILIKE %s"
#         params.append(f"%{query}%")
#     if sort == "desc":
#         sql += " ORDER BY name DESC"
#     else:
#         sql += " ORDER BY name"
#     with connection.cursor() as cursor:
#         cursor.execute(sql, params)
#         rows = dictfetchall(cursor)
#     page = paginate_queryset(rows, per_page=5, request=request)
#     readonly = getattr(request.user, 'role', None) and request.user.role.rolename in ['client', 'master']
#     return render(request, "admin_panel/services_list.html", {"page": page, "query": query, "sort": sort})


# @login_required
# def service_create(request):
#     if request.method == 'POST':
#         form = ServiceForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             INSERT INTO service (name, description, price)
#                             VALUES (%s, %s, %s)
#                             RETURNING id
#                         """, [data['name'], data.get('description'), data.get('price')])
#                         new_id = cursor.fetchone()[0]
#                         log_action_sql(request.user, 'service', 'create', row_id=new_id, row_data={'name': data['name']})
#                 messages.success(request, 'Услуга создана')
#                 return redirect('services_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при создании услуги: {e}")
#     else:
#         form = ServiceForm()
#     return render(request, 'admin_panel/service_form.html', {'form': form, 'action': 'Создать'})


# @login_required
# def service_edit(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, name, description, price FROM service WHERE id = %s", [pk])
#         service = dictfetchone(cursor)
#     if not service:
#         raise Http404("Услуга не найдена")
#     if request.method == 'POST':
#         form = ServiceForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             UPDATE service
#                             SET name = %s, description = %s, price = %s
#                             WHERE id = %s
#                         """, [data['name'], data.get('description'), data.get('price'), pk])
#                         log_action_sql(request.user, 'service', 'update', row_id=pk, row_data={'name': data['name']})
#                 messages.success(request, 'Услуга обновлена')
#                 return redirect('services_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при обновлении услуги: {e}")
#     else:
#         form = ServiceForm(initial=service)
#     return render(request, 'admin_panel/service_form.html', {'form': form, 'action': 'Редактировать'})


# @login_required
# def service_delete(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, name FROM service WHERE id = %s", [pk])
#         service = dictfetchone(cursor)
#     if not service:
#         raise Http404("Услуга не найдена")
#     if request.method == 'POST':
#         try:
#             with transaction.atomic():
#                 with connection.cursor() as cursor:
#                     cursor.execute("DELETE FROM service WHERE id = %s", [pk])
#                     log_action_sql(request.user, 'service', 'delete', row_data={'name': service['name']})
#             messages.success(request, 'Услуга удалена')
#             return redirect('services_list')
#         except IntegrityError as e:
#             messages.error(request, f"Ошибка при удалении услуги: {e}")
#     return render(request, 'admin_panel/confirm_delete.html', {'object': service, 'type': 'Услуга'})


# @login_required
# def statuses_list(request):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, statusname FROM status ORDER BY statusname")
#         rows = dictfetchall(cursor)
#     page = paginate_queryset(rows, per_page=5, request=request)
#     return render(request, 'admin_panel/statuses_list.html', {'page': page})


# @login_required
# def status_create(request):
#     if request.method == 'POST':
#         form = StatusForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             INSERT INTO status (statusname)
#                             VALUES (%s)
#                             RETURNING id
#                         """, [data['statusname']])
#                         new_id = cursor.fetchone()[0]
#                         log_action_sql(request.user, 'status', 'create', row_id=new_id, row_data={'statusname': data['statusname']})
#                 messages.success(request, 'Статус создан')
#                 return redirect('statuses_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при создании статуса: {e}")
#     else:
#         form = StatusForm()
#     return render(request, 'admin_panel/status_form.html', {'form': form, 'action': 'Создать'})


# @login_required
# def status_edit(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, statusname FROM status WHERE id = %s", [pk])
#         status = dictfetchone(cursor)
#     if not status:
#         raise Http404("Статус не найден")
#     if request.method == 'POST':
#         form = StatusForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("UPDATE status SET statusname = %s WHERE id = %s", [data['statusname'], pk])
#                         log_action_sql(request.user, 'status', 'update', row_id=pk, row_data={'statusname': data['statusname']})
#                 messages.success(request, 'Статус обновлён')
#                 return redirect('statuses_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при обновлении статуса: {e}")
#     else:
#         form = StatusForm(initial=status)
#     return render(request, 'admin_panel/status_form.html', {'form': form, 'action': 'Редактировать'})


# @login_required
# def status_delete(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, statusname FROM status WHERE id = %s", [pk])
#         status = dictfetchone(cursor)
#     if not status:
#         raise Http404("Статус не найден")
#     if request.method == 'POST':
#         try:
#             with transaction.atomic():
#                 with connection.cursor() as cursor:
#                     cursor.execute("DELETE FROM status WHERE id = %s", [pk])
#                     log_action_sql(request.user, 'status', 'delete', row_data={'statusname': status['statusname']})
#             messages.success(request, 'Статус удалён')
#             return redirect('statuses_list')
#         except IntegrityError as e:
#             messages.error(request, f"Ошибка при удалении статуса: {e}")
#     return render(request, 'admin_panel/confirm_delete.html', {'object': status, 'type': 'Статус'})


# @login_required
# def payments_list(request):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, date, amount, paymentmethod FROM payment ORDER BY date DESC")
#         rows = dictfetchall(cursor)
#     page = paginate_queryset(rows, per_page=5, request=request)
#     return render(request, 'admin_panel/payments_list.html', {'page': page})


# @login_required
# def payment_create(request):
#     if request.method == 'POST':
#         form = PaymentForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             INSERT INTO payment (date, amount, paymentmethod)
#                             VALUES (%s, %s, %s)
#                             RETURNING id
#                         """, [data['date'], data['amount'], data['paymentmethod']])
#                         new_id = cursor.fetchone()[0]
#                         log_action_sql(request.user, 'payment', 'create', row_id=new_id, row_data={'amount': str(data['amount'])})
#                 messages.success(request, 'Платёж создан')
#                 return redirect('payments_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при создании платежа: {e}")
#     else:
#         form = PaymentForm()
#     return render(request, 'admin_panel/payment_form.html', {'form': form, 'action': 'Создать'})


# @login_required
# def payment_edit(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, date, amount, paymentmethod FROM payment WHERE id = %s", [pk])
#         payment = dictfetchone(cursor)
#     if not payment:
#         raise Http404("Платёж не найден")
#     if request.method == 'POST':
#         form = PaymentForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             UPDATE payment
#                             SET date = %s, amount = %s, paymentmethod = %s
#                             WHERE id = %s
#                         """, [data['date'], data['amount'], data['paymentmethod'], pk])
#                         log_action_sql(request.user, 'payment', 'update', row_id=pk, row_data={'amount': str(data['amount'])})
#                 messages.success(request, 'Платёж обновлён')
#                 return redirect('payments_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при обновлении платежа: {e}")
#     else:
#         form = PaymentForm(initial=payment)
#     return render(request, 'admin_panel/payment_form.html', {'form': form, 'action': 'Редактировать'})


# @login_required
# def payment_delete(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, amount FROM payment WHERE id = %s", [pk])
#         payment = dictfetchone(cursor)
#     if not payment:
#         raise Http404("Платёж не найден")
#     if request.method == 'POST':
#         try:
#             with transaction.atomic():
#                 with connection.cursor() as cursor:
#                     cursor.execute("DELETE FROM payment WHERE id = %s", [pk])
#                     log_action_sql(request.user, 'payment', 'delete', row_data={'amount': str(payment['amount'])})
#             messages.success(request, 'Платёж удалён')
#             return redirect('payments_list')
#         except IntegrityError as e:
#             messages.error(request, f"Ошибка при удалении платежа: {e}")
#     return render(request, 'admin_panel/confirm_delete.html', {'object': payment, 'type': 'Платёж'})


# @login_required
# def cars_list(request):
#     query = request.GET.get("q")
#     sort = request.GET.get("sort")
#     sql = "SELECT id, name, description, image FROM car"
#     params = []
#     if query:
#         sql += " WHERE name ILIKE %s"
#         params.append(f"%{query}%")
#     if sort == "desc":
#         sql += " ORDER BY name DESC"
#     else:
#         sql += " ORDER BY name"
#     with connection.cursor() as cursor:
#         cursor.execute(sql, params)
#         rows = dictfetchall(cursor)
#     page = paginate_queryset(rows, per_page=5, request=request)
#     readonly = getattr(request.user, 'role', None) and request.user.role.rolename in ['client', 'master']
#     return render(request, "admin_panel/cars_list.html", {"page": page, "query": query, "sort": sort})


# @login_required
# def car_create(request):
#     if request.method == 'POST':
#         form = CarForm(request.POST, request.FILES)
#         if form.is_valid():
#             data = form.cleaned_data
#             image_path = None
#             if request.FILES.get('image'):
#                 image_path = save_uploaded_file(request.FILES['image'])
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             INSERT INTO car (name, description, image)
#                             VALUES (%s, %s, %s)
#                             RETURNING id
#                         """, [data['name'], data.get('description'), image_path])
#                         new_id = cursor.fetchone()[0]
#                         log_action_sql(request.user, 'car', 'create', row_id=new_id, row_data={'name': data['name']})
#                 messages.success(request, 'Машина создана')
#                 return redirect('cars_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при создании машины: {e}")
#     else:
#         form = CarForm()
#     return render(request, 'admin_panel/car_form.html', {'form': form, 'action': 'Создать'})


# @login_required
# def car_edit(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, name, description, image FROM car WHERE id = %s", [pk])
#         car = dictfetchone(cursor)
#     if not car:
#         raise Http404("Машина не найдена")
#     if request.method == 'POST':
#         form = CarForm(request.POST, request.FILES)
#         if form.is_valid():
#             data = form.cleaned_data
#             image_path = car.get('image')
#             if request.FILES.get('image'):
#                 image_path = save_uploaded_file(request.FILES['image'])
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute("""
#                             UPDATE car
#                             SET name = %s, description = %s, image = %s
#                             WHERE id = %s
#                         """, [data['name'], data.get('description'), image_path, pk])
#                         log_action_sql(request.user, 'car', 'update', row_id=pk, row_data={'name': data['name']})
#                 messages.success(request, 'Машина обновлена')
#                 return redirect('cars_list')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при обновлении машины: {e}")
#     else:
#         form = CarForm(initial=car)
#     return render(request, 'admin_panel/car_form.html', {'form': form, 'action': 'Редактировать'})


# @login_required
# def car_delete(request, pk):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, name FROM car WHERE id = %s", [pk])
#         car = dictfetchone(cursor)
#     if not car:
#         raise Http404("Машина не найдена")
#     if request.method == 'POST':
#         try:
#             with transaction.atomic():
#                 with connection.cursor() as cursor:
#                     cursor.execute("DELETE FROM car WHERE id = %s", [pk])
#                     log_action_sql(request.user, 'car', 'delete', row_data={'name': car['name']})
#             messages.success(request, 'Машина удалена')
#             return redirect('cars_list')
#         except IntegrityError as e:
#             messages.error(request, f"Ошибка при удалении машины: {e}")
#     return render(request, 'admin_panel/confirm_delete.html', {'object': car, 'type': 'Машина'})


# @login_required
# def statistics(request):
#     with connection.cursor() as cursor:
#         cursor.execute('SELECT COUNT(*) FROM "Order"')
#         orders_count = cursor.fetchone()[0]
#         cursor.execute("""
#             SELECT st.statusname, COUNT(o.id) AS count
#             FROM "Order" o
#             LEFT JOIN status st ON o.status = st.id
#             GROUP BY st.statusname
#             ORDER BY count DESC
#         """)
#         orders_by_status = dictfetchall(cursor)
#         cursor.execute("""
#             SELECT o.masterid AS master__id, u.name AS master__name, u.surname AS master__surname, COUNT(o.id) AS count
#             FROM "Order" o
#             LEFT JOIN "User" u ON o.masterid = "User".id
#             WHERE "User".role_id = 2
#             GROUP BY o.masterid, u.name, u.surname
#             ORDER BY count DESC
#             LIMIT 10
#         """)
#         top_masters = dictfetchall(cursor)
#     context = {
#         'orders_count': orders_count,
#         'orders_by_status': orders_by_status,
#         'top_masters': top_masters,
#     }
#     return render(request, 'admin_panel/statistics.html', context)


# @login_required
# def logs(request):
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT a.id, a.action, a.action_timestamp, a.table_name, a.operation, a.row_id, "User".name AS user_name
#             FROM actionlog a
#             LEFT JOIN "User" ON a.userid = "User".id
#             ORDER BY a.action_timestamp DESC
#         """)
#         rows = dictfetchall(cursor)
#     page = paginate_queryset(rows, per_page=50, request=request)
#     return render(request, 'admin_panel/logs.html', {'page': page})


# @login_required
# @user_passes_test(is_client)
# def client_dashboard(request):
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT o.id, o.creationdate, o.carid, o.status, st.statusname, o.total_cost
#             FROM "Order" o
#             LEFT JOIN status st ON o.status = st.id
#             WHERE o.clientid = %s
#             ORDER BY o.creationdate DESC
#         """, [request.user.id])
#         orders = dictfetchall(cursor)
#     return render(request, "client_dashboard.html", {"orders": orders})


# @login_required
# def master_orders(request):
#     user = request.user
#     if getattr(user, 'role_id', None) != 2:
#         return HttpResponseForbidden("Доступ разрешён только мастерам.")
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT o.id, o.creationdate, o.carid, o.clientid, st.statusname, s.name AS service_name, p.name AS part_name
#             FROM "Order" o
#             LEFT JOIN status st ON o.status = st.id
#             LEFT JOIN service s ON o.serviceid = s.id
#             LEFT JOIN part p ON o.partid = p.id
#             WHERE o.masterid = %s
#             ORDER BY o.creationdate DESC
#         """, [user.id])
#         orders_qs = dictfetchall(cursor)
#     paginator = Paginator(orders_qs, 10)
#     page_number = request.GET.get('page')
#     page = paginator.get_page(page_number)
#     return render(request, 'master/orders_list.html', {'orders': page})


# @login_required
# def admin_orders(request):
#     user = request.user
#     if getattr(user, 'role_id', None) != 1:
#         return HttpResponseForbidden("Доступ разрешён только администратору.")
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT o.id, o.creationdate, o.clientid, "User".name AS client_name, o.carid, o.status, st.statusname,
#                    o.serviceid, s.name AS service_name, o.partid, p.name AS part_name, o.masterid
#             FROM "Order" o
#             LEFT JOIN "User" ON o.clientid = "User".id
#             LEFT JOIN status st ON o.status = st.id
#             LEFT JOIN service s ON o.serviceid = s.id
#             LEFT JOIN part p ON o.partid = p.id
#             LEFT JOIN "User" m ON o.masterid = m.id
#             ORDER BY o.creationdate DESC
#         """)
#         orders = dictfetchall(cursor)
#     return render(request, 'admin_panel/admin_orders.html', {'orders': orders})


# @login_required
# def change_order_status(request, order_id):
#     user = request.user
#     if getattr(user, 'role_id', None) != 1:
#         return HttpResponseForbidden("Доступ разрешён только администратору.")
#     with connection.cursor() as cursor:
#         cursor.execute('SELECT id, status FROM "Order" WHERE id = %s', [order_id])
#         order = dictfetchone(cursor)
#     if not order:
#         raise Http404("Заказ не найден")
#     if request.method == "POST":
#         new_status_id = request.POST.get("status_id")
#         if new_status_id:
#             try:
#                 with transaction.atomic():
#                     with connection.cursor() as cursor:
#                         cursor.execute('UPDATE "Order" SET status = %s WHERE id = %s', [new_status_id, order_id])
#                         log_action_sql(request.user, 'Order', 'update', row_id=order_id, row_data={'status': new_status_id})
#                 return redirect('admin_orders')
#             except IntegrityError as e:
#                 messages.error(request, f"Ошибка при смене статуса: {e}")
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT id, statusname FROM status")
#         statuses = dictfetchall(cursor)
#     return render(request, 'admin_panel/change_status.html', {'order': order, 'statuses': statuses})


# @login_required
# def masters_list(request):
#     with connection.cursor() as cursor:
#         cursor.execute('SELECT id, name, surname FROM "User" WHERE role_id = 2 ORDER BY surname, name')
#         masters_qs = dictfetchall(cursor)
#     paginator = Paginator(masters_qs, 10)
#     page_number = request.GET.get('page')
#     page = paginator.get_page(page_number)
#     return render(request, "admin_panel/masters_list.html", {"page": page})


# @login_required
# def client_orders(request):
#     user = request.user
#     if getattr(user, 'role_id', None) != 3:
#         return HttpResponseForbidden("Доступ разрешён только клиентам.")
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT o.id, o.creationdate, o.carid, st.statusname, s.name AS service_name, p.name AS part_name, o.total_cost
#             FROM "Order" o
#             LEFT JOIN status st ON o.status = st.id
#             LEFT JOIN service s ON o.serviceid = s.id
#             LEFT JOIN part p ON o.partid = p.id
#             WHERE o.clientid = %s
#             ORDER BY o.creationdate DESC
#         """, [user.id])
#         orders_qs = dictfetchall(cursor)
#     return render(request, 'client/orders_list.html', {'orders': orders_qs})


# def paginate_queryset(queryset, per_page=5, request=None):
#     if isinstance(queryset, list):
#         paginator = Paginator(queryset, per_page)
#         page_number = request.GET.get('page') if request is not None else 1
#         return paginator.get_page(page_number)
#     paginator = Paginator(queryset, per_page)
#     page_number = request.GET.get('page') if request is not None else 1
#     return paginator.get_page(page_number)
