from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path("iletisim/", views.iletisim_view, name="iletisim"),

    path('urun/<int:product_id>/', views.product_detail, name='product_detail'),

    path('sepete-ekle/<int:product_id>/', views.add_to_cart, name='add_to_cart'),

    path('sepet/', views.cart, name='cart'),
    path('sepetten-sil/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path("sepet/adet-guncelle/<int:item_id>/", views.update_cart_quantity, name="update_cart_quantity"),
    path("siparisi-tamamla/", views.complete_order, name="complete_order"),
    path("siparis-basarili/<int:order_id>/", views.order_success, name="order_success"),
    path('filtre/', views.filter_products, name='filter_products'),
    path("uye-ol/", views.register_view, name="register"),
    path("giris/", views.login_view, name="login"),
    path("cikis/", views.logout_view, name="logout"),
    path("hesabim/", views.account_view, name="account"),
    path("sifre-degistir/", views.change_password_view, name="change_password"),
    path("iade-hakki/", views.iade_hakki_view, name="iade_hakki"),
    path("iptal/", views.iptal_view, name="iptal"),
    path("garanti-kosullari/", views.garanti_kosullari_view, name="garanti_kosullari"),
    path("uyelik-sozlesmesi/", views.uyelik_sozlesmesi_view, name="uyelik_sozlesmesi"),
    path("teslimat-bilgileri/", views.teslimat_bilgileri_view, name="teslimat_bilgileri"),
    path("gizlilik-guvenlik/", views.gizlilik_guvenlik_view, name="gizlilik_guvenlik"),
    path("mesafeli-satis-sozlesmesi/", views.mesafeli_satis_sozlesmesi_view, name="mesafeli_satis_sozlesmesi"),
]