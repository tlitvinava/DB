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
            
            return redirect("order_list")
        else:
            # добавим ошибки формы в сообщения
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
    # Передаём имя текущего пользователя в шаблон
    return render(request, 'home.html', {
        'username': request.user.name  # поле name из твоей модели User
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


# -------------------------
# Forms
# -------------------------
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
        fields = ['date', 'amount', 'paymentmethod']


class CarForm(ModelForm):
    class Meta:
        model = Car
        fields = ['name', 'description', 'image']

# -------------------------
# Helper: log action
# -------------------------
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
        # Логирование не должно ломать основной поток
        pass


# -------------------------
# Admin panel home
# -------------------------
@admin_required
def admin_panel(request):
    # краткая сводка
    stats = {
        'orders_count': Order.objects.count(),
        'masters_count': User.objects.filter(role_id=2).count(),
        'parts_count': Part.objects.count(),
        'services_count': Service.objects.count(),
        'cars_count': Car.objects.count(),
    }
    return render(request, 'admin_panel/admin_panel.html', {'stats': stats})


# -------------------------
# Generic list/create/edit/delete helpers
# -------------------------
def paginate_queryset(request, queryset, per_page=5):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


# -------------------------
# Masters CRUD
# -------------------------
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
        form = PartForm(request.POST, request.FILES)  # добавил request.FILES
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
        form = PartForm(request.POST, request.FILES, instance=part)  # добавил request.FILES
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

    # поиск по названию
    if query:
        qs = qs.filter(name__icontains=query)

    # сортировка
    if sort == "desc":
        qs = qs.order_by("-name")
    else:  # по умолчанию или sort == "asc"
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


# -------------------------
# Status CRUD
# -------------------------
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


# -------------------------
# Payments CRUD
# -------------------------
@admin_required
def payments_list(request):
    qs = Payment.objects.all().order_by('-date')
    page = paginate_queryset(request, qs, per_page=5)
    return render(request, 'admin_panel/payments_list.html', {'page': page})


@admin_required
def payment_create(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            log_action(request.user, 'payment', 'create', row_id=payment.pk, row_data={'amount': str(payment.amount)})
            messages.success(request, 'Платёж создан')
            return redirect('payments_list')
    else:
        form = PaymentForm()
    return render(request, 'admin_panel/payment_form.html', {'form': form, 'action': 'Создать'})


@admin_required
def payment_edit(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save()
            log_action(request.user, 'payment', 'update', row_id=payment.pk, row_data={'amount': str(payment.amount)})
            messages.success(request, 'Платёж обновлён')
            return redirect('payments_list')
    else:
        form = PaymentForm(instance=payment)
    return render(request, 'admin_panel/payment_form.html', {'form': form, 'action': 'Редактировать'})


@admin_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        row_data = {'amount': str(payment.amount)}
        payment.delete()
        log_action(request.user, 'payment', 'delete', row_data=row_data)
        messages.success(request, 'Платёж удалён')
        return redirect('payments_list')
    return render(request, 'admin_panel/confirm_delete.html', {'object': payment, 'type': 'Платёж'})


# -------------------------
# Cars CRUD
# -------------------------
# Cars
# @login_required
# def cars_list(request):
#     qs = Car.objects.all().order_by('name')
#     page = paginate_queryset(request, qs, per_page=5)
#     readonly = _readonly_for_user(request.user)
#     return render(request, 'admin_panel/cars_list.html', {'page': page})


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
        form = CarForm(request.POST, request.FILES)  # добавил request.FILES
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
        form = CarForm(request.POST, request.FILES, instance=car)  # добавил request.FILES
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


# -------------------------
# Statistics
# -------------------------
# @admin_required
# def statistics(request):
#     orders_count = Order.objects.count()
#     orders_by_status = Order.objects.values('status__statusname').annotate(count=Count('id')).order_by('-count')
#     top_masters = Order.objects.values('master__id', 'master__name', 'master__surname').annotate(count=Count('id')).order_by('-count')[:10]
#     total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0

#     context = {
#         'orders_count': orders_count,
#         'orders_by_status': orders_by_status,
#         'top_masters': top_masters,
#         'total_revenue': total_revenue,
#     }
#     return render(request, 'admin_panel/statistics.html', context)

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

    # топ мастеров: только пользователи с role_id = 2
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


# -------------------------
# Logs
# -------------------------
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
    # Получаем все заказы текущего клиента
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
        .filter(master_id=user.id)  # фильтрация по masterid
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
    # доступ только администратору
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
    # только пользователи с role_id = 2
    masters_qs = User.objects.filter(role_id=2).order_by('surname', 'name')
    paginator = Paginator(masters_qs, 10)  # по 10 мастеров на страницу
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
    # проверяем, что это клиент (например, role_id = 3)
    if getattr(user, 'role_id', None) != 3:
        return HttpResponseForbidden("Доступ разрешён только клиентам.")

    # выбираем только заказы, где client_id совпадает с id текущего пользователя
    orders_qs = (
        Order.objects
        .select_related('car', 'status', 'service', 'part', 'master')
        .filter(client_id=user.id)   # ключевой момент!
        .order_by('-creationdate')
    )

    return render(request, 'client/orders_list.html', {'orders': orders_qs})
