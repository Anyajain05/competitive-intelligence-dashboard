from __future__ import annotations

import argparse
import csv
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import quote_plus


"""
Reproducible Amazon India collection workflow.

This scraper is intentionally conservative:
- it uses Playwright browser automation instead of brittle HTTP-only scraping;
- it records only public listing/review fields needed by the assignment;
- it includes waits and a small sample cap to avoid aggressive traffic;
- selectors are isolated so they can be adjusted when Amazon changes markup.

Run after installing Playwright:
    python -m pip install playwright pandas
    python -m playwright install chromium
    python scrapers/amazon_india_scraper.py --brands Safari Skybags "American Tourister" VIP --products-per-brand 10
"""


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ProductRow:
    brand: str
    title: str
    price_text: str
    list_price_text: str
    discount_text: str
    rating_text: str
    review_count_text: str
    product_url: str


@dataclass
class ReviewRow:
    brand: str
    product_url: str
    review_title: str
    review_text: str
    rating_text: str
    is_verified_purchase: str


def clean_number(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def normalise_url(url: str) -> str:
    if not url:
        return ""
    return url.split("?")[0]


def scrape(args: argparse.Namespace) -> None:
    from playwright.sync_api import sync_playwright

    products: list[ProductRow] = []
    reviews: list[ReviewRow] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        page = browser.new_page(locale="en-IN", viewport={"width": 1366, "height": 900})

        for brand in args.brands:
            search_url = f"https://www.amazon.in/s?k={quote_plus(brand + ' luggage suitcase')}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(2500)

            cards = page.locator('[data-component-type="s-search-result"]').all()[: args.products_per_brand]
            for card in cards:
                title = safe_text(card.locator("h2 span").first())
                href = card.locator("h2 a").first().get_attribute("href") or ""
                product_url = normalise_url("https://www.amazon.in" + href if href.startswith("/") else href)
                row = ProductRow(
                    brand=brand,
                    title=title,
                    price_text=safe_text(card.locator(".a-price .a-offscreen").first()),
                    list_price_text=safe_text(card.locator(".a-price.a-text-price .a-offscreen").first()),
                    discount_text=safe_text(card.locator("span:has-text('% off')").first()),
                    rating_text=safe_text(card.locator(".a-icon-alt").first()),
                    review_count_text=safe_text(card.locator("a[href*='customerReviews'] span").first()),
                    product_url=product_url,
                )
                if row.title and row.product_url:
                    products.append(row)

                if product_url and args.reviews_per_product > 0:
                    reviews.extend(scrape_reviews(page, brand, product_url, args.reviews_per_product))
                time.sleep(args.delay)

        browser.close()

    write_rows(RAW_DIR / "amazon_products_raw.csv", products)
    write_rows(RAW_DIR / "amazon_reviews_raw.csv", reviews)
    print(f"Wrote {len(products)} raw products and {len(reviews)} raw reviews to {RAW_DIR}")


def scrape_reviews(page, brand: str, product_url: str, limit: int) -> list[ReviewRow]:
    rows: list[ReviewRow] = []
    review_url = product_url.rstrip("/") + "/#customerReviews"
    page.goto(review_url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(1800)

    review_cards = page.locator('[data-hook="review"]').all()[:limit]
    for review in review_cards:
        rows.append(
            ReviewRow(
                brand=brand,
                product_url=product_url,
                review_title=safe_text(review.locator('[data-hook="review-title"]').first()),
                review_text=safe_text(review.locator('[data-hook="review-body"]').first()),
                rating_text=safe_text(review.locator(".a-icon-alt").first()),
                is_verified_purchase=safe_text(review.locator('[data-hook="avp-badge"]').first()),
            )
        )
    return rows


def safe_text(locator) -> str:
    try:
        return " ".join(locator.inner_text(timeout=1500).split())
    except Exception:
        return ""


def write_rows(path: Path, rows: list) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brands", nargs="+", default=["Safari", "Skybags", "American Tourister", "VIP", "Aristocrat", "Nasher Miles"])
    parser.add_argument("--products-per-brand", type=int, default=10)
    parser.add_argument("--reviews-per-product", type=int, default=6)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--headed", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    scrape(parse_args())
