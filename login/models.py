from django.db import models
from django import forms

# Create your models here.
class LoginForm(forms.Form):
    username = forms.CharField(label='',max_length = 100, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(label='', widget=forms.PasswordInput(attrs={'placeholder':'Password'}))


class PasswordResetForm(forms.Form):
    password = forms.CharField(label='',max_length = 100, widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    repeat_password = forms.CharField(label='', widget=forms.PasswordInput(attrs={'placeholder':'Repeat Password'}))