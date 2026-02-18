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
        fields = ['id', 'name', 'description']

class OrderSerializer(serializers.ModelSerializer):
    client_info = ClientSerializer(source='client', read_only=True)
    car_info = CarSerializer(source='car', read_only=True)
    status_info = StatusSerializer(source='status', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'client',
            'car',
            'master',
            'part',
            'service',
            'payment',
            'status',
            'creationdate',
            'notes',
            'client_info',
            'car_info',
            'status_info'
        ]
