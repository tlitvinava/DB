from django import forms
from core.models import User, Role

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ModelChoiceField(queryset=Role.objects.all(), empty_label="Выберите роль")

    class Meta:
        model = User
        fields = ['email', 'name', 'surname', 'password', 'confirm_password', 'role']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        if password != confirm:
            raise forms.ValidationError("Пароли не совпадают")
        return cleaned_data


from django import forms
from django.contrib.auth import get_user_model
from core.models import Order, Car, Part, Payment, Service, Status

User = get_user_model()

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['car', 'master', 'part', 'payment', 'service', 'notes']
        widgets = {
            'car': forms.Select(attrs={'class': 'form-control'}),
            'master': forms.Select(attrs={'class': 'form-control'}),
            'part': forms.Select(attrs={'class': 'form-control'}),
            'payment': forms.Select(attrs={'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # фильтруем только пользователей с ролью мастера (role_id = 2)
        self.fields['master'].queryset = User.objects.filter(role_id=2)
