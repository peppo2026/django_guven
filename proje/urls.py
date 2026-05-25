from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('reveber-guven/', admin.site.urls),

    path(
        "sifremi-unuttum/",
        auth_views.PasswordResetView.as_view(
            template_name="shop/password_reset_form.html"
        ),
        name="password_reset"
    ),

    path(
        "sifremi-unuttum/gonderildi/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="shop/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    path(
        "sifre-sifirla/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="shop/password_reset_confirm.html"
        ),
        name="password_reset_confirm"
    ),

    path(
        "sifre-sifirla/tamamlandi/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="shop/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),

    path('', include('shop.urls')),
]