from django.contrib import admin
from django import forms
from django.utils import timezone
import uuid

from .models import (
    Product,
    CartItem,
    Order,
    OrderItem,
    CarBrand,
    CarModel,
    ProductCompatibility,
    UserProfile,
    ProductComment
)


class ProductCommentAdminForm(forms.ModelForm):
    admin_reply = forms.CharField(
        label="Bu yoruma cevap yaz",
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "style": "width: 700px;",
            "placeholder": "Bu müşterinin yorumuna cevabınızı buraya yazın..."
        })
    )

    class Meta:
        model = ProductComment
        fields = "__all__"


@admin.register(ProductComment)
class ProductCommentAdmin(admin.ModelAdmin):
    form = ProductCommentAdminForm

    list_display = (
        "id",
        "author_name",
        "short_text",
        "product",
        "parent",
        "is_approved",
        "is_imported",
        "date_text",
        "source_product_id",
        "source_comment_id",
    )

    list_filter = (
        "is_approved",
        "is_imported",
        "created_at",
    )

    search_fields = (
        "author_name",
        "text",
        "product__name",
        "source_product_id",
        "source_comment_id",
    )

    list_editable = (
        "is_approved",
    )

    ordering = (
        "-id",
    )

    readonly_fields = (
        "source_product_id",
        "source_comment_id",
        "is_imported",
        "created_at",
    )

    fieldsets = (
        ("Yorum Bilgisi", {
            "fields": (
                "product",
                "parent",
                "author_name",
                "text",
                "date_text",
                "is_approved",
                "is_imported",
            )
        }),
        ("Kaynak Bilgisi", {
            "fields": (
                "source_product_id",
                "source_comment_id",
                "created_at",
            )
        }),
        ("Admin Cevabı", {
            "fields": (
                "admin_reply",
            )
        }),
    )

    def short_text(self, obj):
        return obj.text[:80]

    short_text.short_description = "Yorum"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        reply_text = form.cleaned_data.get("admin_reply", "").strip()

        if reply_text:
            ProductComment.objects.create(
                product=obj.product,
                source_product_id=obj.source_product_id,
                source_comment_id=f"admin-reply-{obj.id}-{uuid.uuid4().hex[:8]}",
                parent=obj,
                author_name="Guvenotoyedek",
                text=reply_text,
                date_text=timezone.now().strftime("%d.%m.%Y %H:%M:%S"),
                is_approved=True,
                is_imported=False,
            )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "quantity", "direction", "price")
    readonly_fields = ("product", "quantity", "direction", "price")
    can_delete = False
    show_change_link = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "phone",
        "total_price",
        "created_at",
    )

    list_display_links = ("id", "customer_name")

    list_filter = (
        "created_at",
    )

    search_fields = (
        "customer_name",
        "phone",
        "address",
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "user",
        "customer_name",
        "phone",
        "address",
        "total_price",
        "created_at",
    )

    inlines = [
        OrderItemInline,
    ]


admin.site.register(Product)
admin.site.register(CartItem)
admin.site.register(OrderItem)

admin.site.register(CarBrand)
admin.site.register(CarModel)
admin.site.register(ProductCompatibility)
admin.site.register(UserProfile)