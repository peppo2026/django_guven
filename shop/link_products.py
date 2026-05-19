from shop.models import Product, CarModel, ProductCompatibility

products = Product.objects.all()
models = CarModel.objects.all()

count = 0

for product in products:
    text = f"""
    {product.name or ""}
    {product.description or ""}
    {product.compatible_cars or ""}
    """.lower()

    for model in models:
        model_text = model.name.lower()

        if model_text in text:
            _, created = ProductCompatibility.objects.get_or_create(
                product=product,
                car_model=model
            )

            if created:
                count += 1

print("Yeni eşleşen:", count)