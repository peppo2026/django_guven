from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.CharField(max_length=255)
    stock = models.IntegerField(default=0)
    source_product_id = models.CharField(max_length=50, blank=True, null=True)
    source_url = models.TextField(blank=True, null=True)

    description = models.TextField(blank=True, null=True)
    stock_code = models.CharField(max_length=100, blank=True, null=True)
    product_code = models.CharField(max_length=150, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    condition = models.CharField(max_length=100, blank=True, null=True)
    product_group = models.CharField(max_length=150, blank=True, null=True)
    compatible_cars = models.TextField(blank=True, null=True)
    comments_html = models.TextField(blank=True, null=True)
    has_direction = models.BooleanField(default=False)
    option_title = models.CharField(max_length=100, blank=True, null=True)
    option_values = models.TextField(blank=True, null=True)

    #buradaki model sadece db de olacak ama web de gozukmeyecek, sadece scraping sırasında kullanılacak
    is_scraped = models.BooleanField(default=False)
    is_in_stock = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.product.name} - {self.image}"


class CarBrand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class CarModel(models.Model):
    brand = models.ForeignKey(CarBrand, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class ProductCompatibility(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="compatibilities")
    car_model = models.ForeignKey(CarModel, on_delete=models.CASCADE)
    years = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.car_model}"


class ProductComment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="comments")

    source_product_id = models.CharField(max_length=50)
    source_comment_id = models.CharField(max_length=50)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies"
    )

    author_name = models.CharField(max_length=100)
    text = models.TextField()
    date_text = models.CharField(max_length=50, blank=True, null=True)

    is_approved = models.BooleanField(default=True)
    is_imported = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "source_comment_id")

    def __str__(self):
        return f"{self.author_name} - {self.product.name}"


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    direction = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.product.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.user.username


class Order(models.Model):
    customer_name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=50)
    address = models.TextField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sipariş #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    direction = models.CharField(max_length=20, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"