import os
from django.db.models import Q
from django.conf import settings
from django.shortcuts import render, redirect
from django.utils import timezone
import uuid
from .models import Product, CartItem, Order, OrderItem ,UserProfile,ProductComment
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from .models import Product, CarModel

##kullanıci bilgileri
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required


def home(request):
    products_list = Product.objects.all()
    paginator = Paginator(products_list, 21)

    page_number = request.GET.get("sayfa")
    products = paginator.get_page(page_number)

    return render(request, "shop/home.html", {
        "products": products
    })

def iletisim_view(request):
    return render(request, "shop/iletisim.html")

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        author_name = request.POST.get("author_name", "").strip()
        text = request.POST.get("text", "").strip()

        if author_name and text:
            ProductComment.objects.create(
                product=product,
                source_product_id=product.source_product_id or str(product.id),
                source_comment_id=f"new-{uuid.uuid4().hex[:12]}",
                parent=None,
                author_name=author_name,
                text=text,
                date_text=timezone.now().strftime("%d.%m.%Y %H:%M:%S"),
                is_approved=False,
                is_imported=False,
            )

        return redirect("product_detail", product_id=product.id)

    option_values = []

    if product.option_values:
        option_values = [
            option.strip()
            for option in product.option_values.split("|")
            if option.strip()
        ]

    return render(request, "shop/product_detail.html", {
        "product": product,
        "option_values": option_values,
    })

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    quantity = int(request.POST.get("quantity", 1))
    direction = request.POST.get("direction", "")

    CartItem.objects.create(
        product=product,
        quantity=quantity,
        direction=direction
    )

    return redirect("cart")


def cart(request):
    cart_items = CartItem.objects.all()

    total_price = 0

    for item in cart_items:
        total_price += item.product.price * item.quantity

    quantity_options = range(1, 51)

    return render(request, "shop/cart.html", {
        "cart_items": cart_items,
        "total_price": total_price,
        "quantity_options": quantity_options
    })
def remove_from_cart(request, item_id):
    item = CartItem.objects.get(id=item_id)
    item.delete()

    return redirect("cart")

def update_cart_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))

        if quantity < 1:
            quantity = 1

        if quantity > 50:
            quantity = 50

        item.quantity = quantity
        item.save()

    return redirect("cart")

@login_required
def complete_order(request):
    cart_items = CartItem.objects.all()

    if not cart_items.exists():
        return redirect("cart")

    total_price = 0

    for item in cart_items:
        total_price += item.product.price * item.quantity

    customer_name = request.user.get_full_name()

    if not customer_name:
        customer_name = request.user.username


    profile = UserProfile.objects.filter(user=request.user).first()
    order = Order.objects.create(
        user=request.user,
        customer_name=customer_name,
        phone=profile.phone if profile else "Belirtilmedi",
        address=profile.address if profile else "Belirtilmedi",
        total_price=total_price
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            direction=item.direction,
            price=item.product.price
        )

    cart_items.delete()

    return redirect("order_success", order_id=order.id)




@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    return render(request, "shop/order_success.html", {
        "order": order
    })



def filter_products(request):
    brand = request.GET.get("brand", "")
    model = request.GET.get("model", "")
    group = request.GET.get("group", "")
    q = request.GET.get("q", "")

    products = Product.objects.all()

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(stock_code__icontains=q) |
            Q(product_code__icontains=q) |
            Q(brand__icontains=q)
        )

    if brand:
        products = products.filter(
            compatibilities__car_model__brand__name__iexact=brand
        )

    if model:
        products = products.filter(
            compatibilities__car_model__name__iexact=model
        )

    if group:
        products = products.filter(
            product_group__icontains=group
        )

    products = products.distinct()

    return render(request, "shop/home.html", {
        "products": products
    })

##kullanici islemleri
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            return render(request, "shop/register.html", {
                "error": "Şifreler aynı değil."
            })
        
        if User.objects.filter(username=username).exists():
            return render(request, "shop/register.html", {
                "error": "Bu kullanıcı adı zaten alınmış."
            })

        if User.objects.filter(email=email).exists():
            return render(request, "shop/register.html", {
                "error": "Bu e-mail adresi zaten kayıtlı."
            })

        user = User.objects.create_user(
            username=username,
            
            password=password1,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        UserProfile.objects.create(
            user=user,
            phone=phone,
            address=address
        )

        return redirect("login")

    return render(request, "shop/register.html")

def login_view(request):
    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username_or_email, password=password)

        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)

            request.session["login_count"] = request.session.get("login_count", 0) + 1

            return redirect("login")

        return render(request, "shop/login.html", {
            "error": "Kullanıcı adı, e-mail veya şifre hatalı."
        })

    return render(request, "shop/login.html")


@login_required
def account_view(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    profile = UserProfile.objects.filter(user=request.user).first()

    if request.method == "POST":
        phone = request.POST.get("phone", "")
        address = request.POST.get("address", "")
        email = request.POST.get("email", "")

        request.user.email = email
        request.user.save()

        if profile is None:
            profile = UserProfile.objects.create(
                user=request.user,
                phone=phone,
                address=address
            )
        else:
            profile.phone = phone
            profile.address = address
            profile.save()

        return redirect("account")

    return render(request, "shop/account.html", {
        "orders": orders,
        "profile": profile
    })



@login_required
def change_password_view(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password1 = request.POST.get("new_password1")
        new_password2 = request.POST.get("new_password2")

        if not request.user.check_password(old_password):
            return render(request, "shop/change_password.html", {
                "error": "Mevcut şifre hatalı."
            })

        if new_password1 != new_password2:
            return render(request, "shop/change_password.html", {
                "error": "Yeni şifreler aynı değil."
            })

        request.user.set_password(new_password1)
        request.user.save()

        update_session_auth_hash(request, request.user)

        return render(request, "shop/change_password.html", {
            "success": "Şifreniz başarıyla değiştirildi."
        })

    return render(request, "shop/change_password.html")


def logout_view(request):
    logout(request)
    return redirect("home")






#statik sayfalar fonksiyonları
def iade_hakki_view(request):
    return render(request, "shop/iade_hakki.html")

def iptal_view(request):
    return render(request, "shop/iptal.html")

def garanti_kosullari_view(request):
    return render(request, "shop/garanti_kosullari.html")

def uyelik_sozlesmesi_view(request):
    return render(request, "shop/uyelik_sozlesmesi.html")

def teslimat_bilgileri_view(request):
    return render(request, "shop/teslimat_bilgileri.html")

def gizlilik_guvenlik_view(request):
    return render(request, "shop/gizlilik_guvenlik.html")

def mesafeli_satis_sozlesmesi_view(request):
    return render(request, "shop/mesafeli_satis_sozlesmesi.html")
