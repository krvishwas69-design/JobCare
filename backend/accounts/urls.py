from django.urls import path

from . import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view()),
    path('auth/login/', views.LoginView.as_view()),
    path('auth/logout/', views.LogoutView.as_view()),
    path('auth/me/', views.MeView.as_view()),
    path('billing/invoices/', views.InvoiceListView.as_view()),
    path('billing/purchase/', views.PurchaseView.as_view()),
    path('billing/verify/', views.VerifyPaymentView.as_view()),
    path('billing/razorpay/webhook/', views.RazorpayWebhookView.as_view()),
]
