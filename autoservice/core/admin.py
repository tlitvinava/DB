from django.contrib import admin
from .models import (
    Order,
    User,
    Actionlog,
    Car,
    Client,
    Clientarchive,
    Master,
    Part,
    Payment,
    Role,
    Service,
    Status
)

# Базовая регистрация моделей
admin.site.register(Order)
admin.site.register(User)
admin.site.register(Actionlog)
admin.site.register(Car)
admin.site.register(Client)
admin.site.register(Clientarchive)
admin.site.register(Master)
admin.site.register(Part)
admin.site.register(Payment)
admin.site.register(Role)
admin.site.register(Service)
admin.site.register(Status)
