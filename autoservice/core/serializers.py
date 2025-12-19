# core/serializers.py
from rest_framework import serializers
from .models import Order, Status, Client, Car

class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ['id', 'statusname']

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'surname', 'email']

class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['id', 'model', 'number']

class OrderSerializer(serializers.ModelSerializer):
    # если нужно отдавать вложенные сущности — раскомментируй
    # client = ClientSerializer(source='clientid', read_only=True)
    # car = CarSerializer(source='carid', read_only=True)
    # status_obj = StatusSerializer(source='status', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'clientid',
            'carid',
            'status',
            'creationdate',
            'completeddate',
            'description',
            # 'client', 'car', 'status_obj'
        ]
