from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api import OrderViewSet, StatusViewSet
from core.views import master_orders
from core.views import home
from core.views import admin_orders
from core.views import change_order_status
from core.views import client_orders

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'statuses', StatusViewSet, basename='status')

urlpatterns = [
    # Home
    path('', home, name='home'),

    # Orders (HTML)
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/update/', views.order_update, name='order_update'),
    path('orders/<int:pk>/delete/', views.order_delete, name='order_delete'),

    # Public: Parts / Services / Cars (просмотр для всех авторизованных ролей)
    path('parts/', views.parts_list, name='parts_list'),    
    #path('parts/<int:pk>/', views.part_detail, name='part_detail'),

    path('services/', views.services_list, name='services_list'),
    #path('services/<int:pk>/', views.service_detail, name='service_detail'),

    path('cars/', views.cars_list, name='cars_list'),
    #path('cars/<int:pk>/', views.car_detail, name='car_detail'),

    # Admin panel (CRUD и админские страницы)
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/statistics/', views.statistics, name='statistics'),
    path('admin-panel/logs/', views.logs, name='logs'),

    # Admin: Masters
    path('admin-panel/masters/', views.masters_list, name='masters_list'),
    path('admin-panel/masters/create/', views.master_create, name='master_create'),
    path('admin-panel/masters/<int:pk>/edit/', views.master_edit, name='master_edit'),
    path('admin-panel/masters/<int:pk>/delete/', views.master_delete, name='master_delete'),

    # Admin: Parts CRUD (отдельно от публичного просмотра)
    path('admin-panel/parts/', views.parts_list, name='admin_parts_list'),
    path('admin-panel/parts/create/', views.part_create, name='part_create'),
    path('admin-panel/parts/<int:pk>/edit/', views.part_edit, name='part_edit'),
    path('admin-panel/parts/<int:pk>/delete/', views.part_delete, name='part_delete'),

    # Admin: Services CRUD
    path('admin-panel/services/', views.services_list, name='admin_services_list'),
    path('admin-panel/services/create/', views.service_create, name='service_create'),
    path('admin-panel/services/<int:pk>/edit/', views.service_edit, name='service_edit'),
    path('admin-panel/services/<int:pk>/delete/', views.service_delete, name='service_delete'),

    # Admin: Statuses
    path('admin-panel/statuses/', views.statuses_list, name='statuses_list'),
    path('admin-panel/statuses/create/', views.status_create, name='status_create'),
    path('admin-panel/statuses/<int:pk>/edit/', views.status_edit, name='status_edit'),
    path('admin-panel/statuses/<int:pk>/delete/', views.status_delete, name='status_delete'),

    # Admin: Payments
    path('admin-panel/payments/', views.payments_list, name='payments_list'),
    path('admin-panel/payments/create/', views.payment_create, name='payment_create'),
    path('admin-panel/payments/<int:pk>/edit/', views.payment_edit, name='payment_edit'),
    path('admin-panel/payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),

    # Admin: Cars CRUD
    path('admin-panel/cars/', views.cars_list, name='admin_cars_list'),
    path('admin-panel/cars/create/', views.car_create, name='car_create'),
    path('admin-panel/cars/<int:pk>/edit/', views.car_edit, name='car_edit'),
    path('admin-panel/cars/<int:pk>/delete/', views.car_delete, name='car_delete'),

    # API (под префиксом api/)
    path('api/', include(router.urls)),
    
    path('master/orders/', master_orders, name='master_orders'),
    path('admin-panel/orders/', admin_orders, name='admin_orders'),
    path('admin-panel/orders/<int:order_id>/change-status/', change_order_status, name='change_order_status'),
        path('client/orders/', client_orders, name='client_orders'),
]
