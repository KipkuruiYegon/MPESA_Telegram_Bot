from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.webhook, name='webhook'),
    path('mpesa/payment_callback/', views.payment_callback, name='mpesa_payment_callback'),
]
