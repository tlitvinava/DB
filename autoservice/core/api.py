# core/api.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404

from .models import Order, Status
from .serializers import OrderSerializer, StatusSerializer
from .permissions import ClientCanCreateOwnOrder, AdminOrMasterCanModify, IsAdmin, IsMaster, IsClient

def role_name(user):
    return getattr(getattr(user, 'role', None), 'rolename', None)

class StatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticated]

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-creationdate')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description']
    ordering_fields = ['creationdate', 'completeddate', 'status']

    def get_permissions(self):
        # Детальная матрица прав
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action in ('create',):
            return [IsAuthenticated(), ClientCanCreateOwnOrder()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), AdminOrMasterCanModify()]
        # Действия ниже — только для админа/мастера
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        rn = role_name(user)

        # Клиент видит только свои заказы (если в Order есть связь на клиента)
        if rn == 'CLIENT':
            return Order.objects.filter(clientid=user.id).order_by('-creationdate')

        # Мастер видит заказы по статусам «в работе», например
        if rn == 'MASTER':
            return Order.objects.exclude(status='COMPLETED').order_by('-creationdate')

        # Админ видит всё
        return Order.objects.all().order_by('-creationdate')

    def perform_create(self, serializer):
        # Привязываем заказ к текущему пользователю‑клиенту
        serializer.save(clientid=self.request.user.id)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, AdminOrMasterCanModify])
    def set_status(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)
        status_id = request.data.get('status')
        if not status_id:
            return Response({'detail': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)
        order.status_id = status_id
        order.save()
        return Response(OrderSerializer(order).data)
