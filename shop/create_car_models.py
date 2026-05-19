from shop.models import CarBrand, CarModel

data = {
    "Opel": [
        "Agila A", "Agila B",
        "Astra Classic", "Astra F", "Astra G", "Astra H", "Astra J", "Astra K",
        "Calibra",
        "Combo B", "Combo C", "Combo D",
        "Corsa A", "Corsa B", "Corsa C", "Corsa D", "Corsa E",
        "Kadette-E",
        "Meriva-A", "Meriva B",
        "Omega A", "Omega B",
        "Opel GT",
        "Senator B",
        "Signum",
        "Sintra",
        "Speedster",
        "Tigra A", "Tigra B",
        "Vectra A", "Vectra B", "Vectra C",
        "Zafira A", "Zafira B", "Zafira C",
        "Insignia",
    ],
    "Chevrolet": [
        "Aveo Hatchback",
        "Aveo Sedan",
        "Captiva",
        "Cruze Hatchback",
        "Cruze Sedan",
        "Lacetti",
        "Spark",
        "Trax",
        "Volt",
    ],
}

created_count = 0

for brand_name, model_names in data.items():
    brand, _ = CarBrand.objects.get_or_create(name=brand_name)

    for model_name in model_names:
        _, created = CarModel.objects.get_or_create(
            brand=brand,
            name=model_name
        )

        if created:
            created_count += 1

print("Eklenen model sayısı:", created_count)