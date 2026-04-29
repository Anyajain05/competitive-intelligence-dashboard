from __future__ import annotations

import csv
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


BRANDS = {
    "Safari": {
        "positioning": "value",
        "base_price": 2799,
        "discount": 48,
        "rating": 4.1,
        "themes_pos": ["lightweight", "value for money", "good capacity", "smooth wheels"],
        "themes_neg": ["zipper stiffness", "handle wobble", "scuffs easily"],
    },
    "Skybags": {
        "positioning": "youth",
        "base_price": 3399,
        "discount": 42,
        "rating": 4.2,
        "themes_pos": ["stylish design", "smooth wheels", "lightweight", "good compartments"],
        "themes_neg": ["outer shell scratches", "zip quality", "smaller than expected"],
    },
    "American Tourister": {
        "positioning": "premium mainstream",
        "base_price": 4699,
        "discount": 34,
        "rating": 4.3,
        "themes_pos": ["brand trust", "durable shell", "smooth trolley", "premium finish"],
        "themes_neg": ["higher price", "limited inside pockets", "delivery dents"],
    },
    "VIP": {
        "positioning": "legacy premium",
        "base_price": 4299,
        "discount": 31,
        "rating": 4.1,
        "themes_pos": ["trusted brand", "sturdy handle", "good material", "spacious"],
        "themes_neg": ["heavy body", "wheel noise", "price feels high"],
    },
    "Aristocrat": {
        "positioning": "budget",
        "base_price": 2299,
        "discount": 53,
        "rating": 4.0,
        "themes_pos": ["low price", "decent capacity", "simple design", "quick delivery"],
        "themes_neg": ["thin material", "zipper issue", "weak handle"],
    },
    "Nasher Miles": {
        "positioning": "design led",
        "base_price": 3899,
        "discount": 37,
        "rating": 4.2,
        "themes_pos": ["attractive colors", "premium look", "smooth wheels", "good packing space"],
        "themes_neg": ["color mismatch", "scratch marks", "after sales delay"],
    },
}

SIZES = ["Cabin 55 cm", "Medium 65 cm", "Large 75 cm"]
CATEGORIES = ["Hard luggage", "Soft luggage", "Cabin suitcase", "Check-in suitcase"]
ASPECTS = ["wheels", "handle", "material", "zipper", "size", "durability", "design", "value"]

POSITIVE_SENTENCES = {
    "lightweight": "It feels lightweight and easy to carry through stations and airports.",
    "value for money": "The price feels justified because the suitcase looks better than expected.",
    "good capacity": "Capacity is good for a short family trip and the layout is practical.",
    "smooth wheels": "The wheels move smoothly even when the bag is fully packed.",
    "stylish design": "The design looks modern and stands out without looking flashy.",
    "good compartments": "The compartments help keep clothes and accessories organised.",
    "brand trust": "The brand gives confidence and the finish feels dependable.",
    "durable shell": "The shell feels durable and handled rough travel well.",
    "smooth trolley": "The trolley movement is smooth and does not get stuck often.",
    "premium finish": "The finish looks premium for an online purchase.",
    "trusted brand": "The brand feels trustworthy and the suitcase arrived as described.",
    "sturdy handle": "The handle feels sturdy when pulling the suitcase.",
    "good material": "The material quality feels good for regular travel.",
    "spacious": "It is spacious enough for a week long trip.",
    "low price": "The low price makes it a practical purchase for occasional travel.",
    "decent capacity": "Capacity is decent and suitable for students or weekend travel.",
    "simple design": "The simple design is clean and easy to use.",
    "quick delivery": "Delivery was quick and packaging was acceptable.",
    "attractive colors": "The colour options are attractive and look fresh.",
    "premium look": "It has a premium look that photographs well.",
    "good packing space": "Packing space is good and the straps hold clothes in place.",
}

NEGATIVE_SENTENCES = {
    "zipper stiffness": "The zipper feels stiff near the corners and needs careful handling.",
    "handle wobble": "The handle wobbles slightly when the suitcase is heavy.",
    "scuffs easily": "The body picks up scuff marks after one trip.",
    "outer shell scratches": "The outer shell scratches more easily than expected.",
    "zip quality": "Zip quality could be better for frequent travellers.",
    "smaller than expected": "The usable size feels smaller than the photos suggest.",
    "higher price": "The price is higher than similar models with close ratings.",
    "limited inside pockets": "Inside pockets are limited for organised packing.",
    "delivery dents": "A few buyers reported dents or marks on delivery.",
    "heavy body": "The body feels heavy before packing.",
    "wheel noise": "The wheels make noise on rough flooring.",
    "price feels high": "The price feels high during low-discount periods.",
    "thin material": "The material feels thin and may not suit rough handling.",
    "zipper issue": "Some users mention zipper issues after a few uses.",
    "weak handle": "The handle feels weak when the bag is filled.",
    "color mismatch": "The delivered colour sometimes looks different from the product image.",
    "scratch marks": "Scratch marks are visible on darker shades.",
    "after sales delay": "After-sales response appears slow for replacement requests.",
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sentiment_from_rating(rating: int, has_negative: bool) -> float:
    base = {1: -0.82, 2: -0.48, 3: -0.08, 4: 0.46, 5: 0.78}[rating]
    if has_negative and rating >= 4:
        base -= 0.24
    return round(clamp(base + random.uniform(-0.08, 0.08), -1, 1), 3)


def main() -> None:
    random.seed(42)
    products = []
    reviews = []
    product_id = 1001
    review_id = 50001

    for brand, cfg in BRANDS.items():
        for idx in range(10):
            size = SIZES[idx % len(SIZES)]
            category = CATEGORIES[(idx + len(brand)) % len(CATEGORIES)]
            model = f"{brand} {['Cruise', 'Neo', 'Rover', 'Edge', 'Metro'][idx % 5]} {size.split()[0]}"
            price_shift = random.uniform(0.78, 1.32)
            selling_price = int(cfg["base_price"] * price_shift // 50 * 50 + 49)
            discount_pct = int(clamp(random.gauss(cfg["discount"], 7), 18, 68))
            list_price = int(selling_price / (1 - discount_pct / 100) // 50 * 50 + 49)
            rating = round(clamp(random.gauss(cfg["rating"], 0.18), 3.6, 4.6), 1)
            review_count = random.randint(210, 5200)
            pid = f"P{product_id}"
            product_id += 1

            products.append(
                {
                    "product_id": pid,
                    "brand": brand,
                    "title": f"{model} {category} with TSA Lock and 8 Wheels",
                    "category": category,
                    "size": size,
                    "selling_price_inr": selling_price,
                    "list_price_inr": list_price,
                    "discount_pct": discount_pct,
                    "rating": rating,
                    "review_count": review_count,
                    "amazon_url": f"https://www.amazon.in/dp/{pid}",
                }
            )

            for offset in range(6):
                pos = random.choice(cfg["themes_pos"])
                neg = random.choice(cfg["themes_neg"])
                if offset in (0, 1, 2):
                    stars = random.choice([4, 5, 5])
                    text = POSITIVE_SENTENCES[pos]
                    has_negative = False
                    aspect = random.choice(["wheels", "design", "value", "size", "material"])
                elif offset in (3, 4):
                    stars = random.choice([3, 4])
                    text = f"{POSITIVE_SENTENCES[pos]} However, {NEGATIVE_SENTENCES[neg].lower()}"
                    has_negative = True
                    aspect = random.choice(["zipper", "handle", "material", "durability"])
                else:
                    stars = random.choice([1, 2, 3])
                    text = NEGATIVE_SENTENCES[neg]
                    has_negative = True
                    aspect = random.choice(["zipper", "handle", "durability", "material"])

                reviews.append(
                    {
                        "review_id": f"R{review_id}",
                        "product_id": pid,
                        "brand": brand,
                        "rating": stars,
                        "review_title": f"{brand} review {offset + 1}",
                        "review_text": text,
                        "sentiment_score": sentiment_from_rating(stars, has_negative),
                        "primary_aspect": aspect,
                        "is_verified_purchase": "yes" if random.random() > 0.11 else "no",
                    }
                )
                review_id += 1

    with (DATA_DIR / "products_cleaned.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(products[0].keys()))
        writer.writeheader()
        writer.writerows(products)

    with (DATA_DIR / "reviews_cleaned.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(reviews[0].keys()))
        writer.writeheader()
        writer.writerows(reviews)

    print(f"Wrote {len(products)} products and {len(reviews)} reviews to {DATA_DIR}")


if __name__ == "__main__":
    main()
