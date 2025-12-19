from django.shortcuts import render, redirect
from django.contrib.auth import login
from django import forms
from core.models import User, Role

class RegisterForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Повторите пароль")
    name = forms.CharField(max_length=100, label="Имя")
    surname = forms.CharField(max_length=100, label="Фамилия")
    role = forms.ModelChoiceField(queryset=Role.objects.all(), label="Роль")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('confirm_password'):
            raise forms.ValidationError("Пароли не совпадают")
        return cleaned

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            name = form.cleaned_data['name']
            surname = form.cleaned_data['surname']
            role = form.cleaned_data['role']

            # создаём пользователя через менеджер, чтобы пароль хэшировался
            user = User.objects.create_user(
                email=email,
                password=password,
                name=name,
                surname=surname,
                role=role
            )

            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})
