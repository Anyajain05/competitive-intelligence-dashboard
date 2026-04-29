from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT = ROOT / "dashboard" / "data"
OUT.mkdir(parents=True, exist_ok=True)

POSITIVE_KEYWORDS = {
    "lightweight": ["lightweight"],
    "smooth wheels": ["smooth", "wheels"],
    "capacity": ["capacity", "spacious", "space"],
    "design": ["design", "colour", "color", "look", "finish"],
    "value": ["value", "price", "low price"],
    "brand trust": ["brand", "trust", "dependable"],
    "material": ["material", "shell", "durable"],
}

NEGATIVE_KEYWORDS = {
    "zipper issue": ["zipper", "zip"],
    "handle wobble": ["handle", "wobble", "weak"],
    "scratches or scuffs": ["scratch", "scuff"],
    "delivery damage": ["delivery", "dent", "marks"],
    "heavy body": ["heavy"],
    "limited organisation": ["pockets", "organised"],
    "after-sales delay": ["after-sales", "replacement"],
    "size mismatch": ["smaller", "size"],
}


def read_csv(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0


def theme_counts(texts: list[str], mapping: dict[str, list[str]]) -> list[dict]:
    counts = Counter()
    combined = " ".join(text.lower() for text in texts)
    for theme, keys in mapping.items():
        counts[theme] = sum(combined.count(key) for key in keys)
    return [{"theme": k, "count": v} for k, v in counts.most_common() if v > 0][:5]


def price_band(price: float) -> str:
    if price < 2800:
        return "Value"
    if price < 4000:
        return "Mid-market"
    return "Premium"


def main() -> None:
    products = read_csv("products_cleaned.csv")
    reviews = read_csv("reviews_cleaned.csv")

    by_brand_products: dict[str, list[dict]] = defaultdict(list)
    by_brand_reviews: dict[str, list[dict]] = defaultdict(list)
    by_product_reviews: dict[str, list[dict]] = defaultdict(list)

    for product in products:
        product["selling_price_inr"] = int(product["selling_price_inr"])
        product["list_price_inr"] = int(product["list_price_inr"])
        product["discount_pct"] = int(product["discount_pct"])
        product["rating"] = float(product["rating"])
        product["review_count"] = int(product["review_count"])
        by_brand_products[product["brand"]].append(product)

    for review in reviews:
        review["rating"] = int(review["rating"])
        review["sentiment_score"] = float(review["sentiment_score"])
        by_brand_reviews[review["brand"]].append(review)
        by_product_reviews[review["product_id"]].append(review)

    brand_metrics = []
    for brand in sorted(by_brand_products):
        brand_products = by_brand_products[brand]
        brand_reviews = by_brand_reviews[brand]
        review_texts = [r["review_text"] for r in brand_reviews]
        avg_price = avg([p["selling_price_inr"] for p in brand_products])
        sentiment = avg([r["sentiment_score"] for r in brand_reviews])
        value_score = round(((sentiment + 1) * 50) / max(avg_price / 3000, 0.7), 1)
        complaints = theme_counts(
            [r["review_text"] for r in brand_reviews if r["sentiment_score"] < 0.25],
            NEGATIVE_KEYWORDS,
        )
        praise = theme_counts(
            [r["review_text"] for r in brand_reviews if r["sentiment_score"] >= 0.25],
            POSITIVE_KEYWORDS,
        )
        anomaly = ""
        if avg([p["rating"] for p in brand_products]) >= 4.15 and complaints:
            anomaly = f"High rating but recurring {complaints[0]['theme']} complaints"

        brand_metrics.append(
            {
                "brand": brand,
                "products": len(brand_products),
                "sampled_reviews": len(brand_reviews),
                "avg_price": avg_price,
                "avg_discount": avg([p["discount_pct"] for p in brand_products]),
                "avg_rating": avg([p["rating"] for p in brand_products]),
                "market_review_count": int(sum(p["review_count"] for p in brand_products)),
                "sentiment_score": sentiment,
                "value_for_money_score": value_score,
                "price_band": price_band(avg_price),
                "top_praise": praise,
                "top_complaints": complaints,
                "anomaly": anomaly,
            }
        )

    product_metrics = []
    for product in products:
        product_reviews = by_product_reviews[product["product_id"]]
        pos = [r["review_text"] for r in product_reviews if r["sentiment_score"] >= 0.25]
        neg = [r["review_text"] for r in product_reviews if r["sentiment_score"] < 0.25]
        sentiments = [r["sentiment_score"] for r in product_reviews]
        product_metrics.append(
            {
                **product,
                "sampled_reviews": len(product_reviews),
                "sentiment_score": avg(sentiments),
                "sentiment_band": "Positive" if avg(sentiments) >= 0.35 else "Mixed" if avg(sentiments) >= 0 else "Negative",
                "price_band": price_band(product["selling_price_inr"]),
                "review_synthesis": synthesize(product, pos, neg),
                "top_praise": theme_counts(pos, POSITIVE_KEYWORDS)[:3],
                "top_complaints": theme_counts(neg, NEGATIVE_KEYWORDS)[:3],
                "aspect_sentiment": aspect_sentiment(product_reviews),
            }
        )

    overview = {
        "total_brands": len(brand_metrics),
        "total_products": len(products),
        "total_sampled_reviews": len(reviews),
        "avg_sentiment": avg([b["sentiment_score"] for b in brand_metrics]),
        "avg_price": avg([p["selling_price_inr"] for p in products]),
        "avg_discount": avg([p["discount_pct"] for p in products]),
        "price_range": [min(p["selling_price_inr"] for p in products), max(p["selling_price_inr"] for p in products)],
    }

    insights = build_insights(brand_metrics)

    payload = {
        "overview": overview,
        "brands": brand_metrics,
        "products": product_metrics,
        "reviews": reviews,
        "insights": insights,
    }

    serialized = json.dumps(payload, indent=2)
    (OUT / "dashboard_data.json").write_text(serialized, encoding="utf-8")
    (OUT / "dashboard_data.js").write_text(f"window.DASHBOARD_DATA = {serialized};\n", encoding="utf-8")
    print(f"Wrote dashboard data to {OUT / 'dashboard_data.json'}")


def aspect_sentiment(reviews: list[dict]) -> list[dict]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for review in reviews:
        grouped[review["primary_aspect"]].append(review["sentiment_score"])
    return [{"aspect": aspect, "sentiment": avg(scores)} for aspect, scores in sorted(grouped.items())]


def synthesize(product: dict, positive_texts: list[str], negative_texts: list[str]) -> str:
    praise = theme_counts(positive_texts, POSITIVE_KEYWORDS)
    complaints = theme_counts(negative_texts, NEGATIVE_KEYWORDS)
    praise_label = praise[0]["theme"] if praise else "overall usability"
    complaint_label = complaints[0]["theme"] if complaints else "few repeated issues"
    return (
        f"{product['brand']} {product['size']} is strongest on {praise_label}. "
        f"The main watch-out is {complaint_label}, especially for buyers planning frequent travel."
    )


def build_insights(brand_metrics: list[dict]) -> list[dict]:
    by_price = sorted(brand_metrics, key=lambda b: b["avg_price"], reverse=True)
    by_value = sorted(brand_metrics, key=lambda b: b["value_for_money_score"], reverse=True)
    by_discount = sorted(brand_metrics, key=lambda b: b["avg_discount"], reverse=True)
    by_sentiment = sorted(brand_metrics, key=lambda b: b["sentiment_score"], reverse=True)
    anomalies = [b for b in brand_metrics if b["anomaly"]]

    insights = [
        {
            "title": f"{by_sentiment[0]['brand']} leads sentiment without being the cheapest",
            "detail": f"It posts a {by_sentiment[0]['sentiment_score']} sentiment score at an average price of INR {by_sentiment[0]['avg_price']:,.0f}, suggesting quality perception is doing more work than discounting alone.",
        },
        {
            "title": f"{by_discount[0]['brand']} depends most on discount-led demand",
            "detail": f"Average discount is {by_discount[0]['avg_discount']}%, above the brand set average. This can drive conversion but weakens premium positioning.",
        },
        {
            "title": f"{by_value[0]['brand']} currently owns the value-for-money lane",
            "detail": f"Its value score of {by_value[0]['value_for_money_score']} combines low-to-mid pricing with comparatively healthy sentiment.",
        },
        {
            "title": f"{by_price[0]['brand']} is the clearest premium-price brand",
            "detail": f"Average selling price is INR {by_price[0]['avg_price']:,.0f}; decision-makers should check whether its review themes defend that premium.",
        },
        {
            "title": "Durability complaints are the main hidden risk",
            "detail": "Across brands, zipper, handle, scratch and material comments recur more often than pure design complaints, so operations and QA fixes may matter more than new colours.",
        },
    ]

    if anomalies:
        insights.append(
            {
                "title": f"{anomalies[0]['brand']} shows a rating-sentiment mismatch",
                "detail": anomalies[0]["anomaly"] + ". This is worth drilling into before treating star rating as a clean win.",
            }
        )

    return insights[:6]


if __name__ == "__main__":
    main()
