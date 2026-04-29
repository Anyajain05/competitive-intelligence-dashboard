const state = {
  data: null,
  selectedProductId: null,
  sortKey: "sentiment_score",
  sortDir: -1,
};

const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const $ = (id) => document.getElementById(id);

async function init() {
  if (window.DASHBOARD_DATA) {
    state.data = window.DASHBOARD_DATA;
  } else {
    const response = await fetch("./data/dashboard_data.json");
    state.data = await response.json();
  }
  state.selectedProductId = state.data.products[0]?.product_id;
  hydrateFilters();
  bindEvents();
  render();
}

function hydrateFilters() {
  const brands = [...new Set(state.data.products.map((p) => p.brand))].sort();
  $("brandFilter").innerHTML = brands.map((b) => `<option value="${b}" selected>${b}</option>`).join("");

  const categories = [...new Set(state.data.products.map((p) => p.category))].sort();
  $("categoryFilter").innerHTML += categories.map((c) => `<option value="${c}">${c}</option>`).join("");
}

function bindEvents() {
  ["brandFilter", "categoryFilter", "sentimentFilter", "ratingFilter", "priceFilter", "searchBox"].forEach((id) => {
    $(id).addEventListener("input", render);
  });
  $("resetFilters").addEventListener("click", () => {
    [...$("brandFilter").options].forEach((option) => (option.selected = true));
    $("categoryFilter").value = "all";
    $("sentimentFilter").value = "all";
    $("ratingFilter").value = "3.5";
    $("priceFilter").value = "7000";
    $("searchBox").value = "";
    render();
  });
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      state.sortDir = state.sortKey === key ? state.sortDir * -1 : -1;
      state.sortKey = key;
      renderBrandTable(filteredBrands());
    });
  });
}

function currentFilters() {
  return {
    brands: [...$("brandFilter").selectedOptions].map((o) => o.value),
    category: $("categoryFilter").value,
    sentiment: $("sentimentFilter").value,
    minRating: Number($("ratingFilter").value),
    maxPrice: Number($("priceFilter").value),
    search: $("searchBox").value.trim().toLowerCase(),
  };
}

function filteredProducts() {
  const filters = currentFilters();
  return state.data.products.filter((p) => {
    const text = `${p.title} ${p.brand}`.toLowerCase();
    return (
      filters.brands.includes(p.brand) &&
      (filters.category === "all" || p.category === filters.category) &&
      (filters.sentiment === "all" || p.sentiment_band === filters.sentiment) &&
      p.rating >= filters.minRating &&
      p.selling_price_inr <= filters.maxPrice &&
      (!filters.search || text.includes(filters.search))
    );
  });
}

function filteredBrands() {
  const products = filteredProducts();
  const brands = [...new Set(products.map((p) => p.brand))];
  return state.data.brands.filter((b) => brands.includes(b.brand));
}

function render() {
  $("ratingValue").textContent = `${Number($("ratingFilter").value).toFixed(1)}+`;
  $("priceValue").textContent = INR.format(Number($("priceFilter").value));
  const products = filteredProducts();
  const brands = filteredBrands();
  if (!products.some((p) => p.product_id === state.selectedProductId)) {
    state.selectedProductId = products[0]?.product_id || null;
  }
  renderKpis(products, brands);
  renderScatter(brands);
  renderDiscountBars(brands);
  renderBrandTable(brands);
  renderProducts(products);
  renderProductDetail(products);
  renderInsights();
}

function avg(values) {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
}

function renderKpis(products, brands) {
  $("kpiBrands").textContent = brands.length;
  $("kpiProducts").textContent = products.length;
  $("kpiReviews").textContent = products.reduce((sum, p) => sum + p.sampled_reviews, 0);
  $("kpiSentiment").textContent = avg(products.map((p) => p.sentiment_score)).toFixed(2);
  $("kpiPrice").textContent = INR.format(avg(products.map((p) => p.selling_price_inr)));
  $("kpiDiscount").textContent = `${avg(products.map((p) => p.discount_pct)).toFixed(1)}%`;
}

function renderScatter(brands) {
  if (!brands.length) {
    $("scatterChart").innerHTML = `<p class="muted">No brands match the current filters.</p>`;
    return;
  }
  const prices = brands.map((b) => b.avg_price);
  const sentiments = brands.map((b) => b.sentiment_score);
  const minPrice = Math.min(...prices) * 0.92;
  const maxPrice = Math.max(...prices) * 1.08;
  const minSent = Math.min(...sentiments, -0.2);
  const maxSent = Math.max(...sentiments, 0.8);
  
  // Aggressive collision avoidance: push labels far apart
  const placed = [];
  const offsets = [
    { x: 35, y: -40 },   // top-right
    { x: -55, y: -40 },  // top-left
    { x: 35, y: 35 },    // bottom-right
    { x: -55, y: 35 },   // bottom-left
    { x: 55, y: 0 },     // far right
    { x: -75, y: 0 }     // far left
  ];
  
  $("scatterChart").innerHTML = brands
    .map((b, i) => {
      const x = ((b.avg_price - minPrice) / (maxPrice - minPrice || 1)) * 88 + 6;
      const y = ((b.sentiment_score - minSent) / (maxSent - minSent || 1)) * 82 + 8;
      
      // Count how many labels are already too close
      let collision = 0;
      for (const p of placed) {
        if (Math.abs(p.x - x) < 6 && Math.abs(p.y - y) < 6) {
          collision++;
        }
      }
      
      // Pick offset based on collision count; cycle through offsets
      const offset = collision > 0 ? offsets[Math.min(collision - 1, offsets.length - 1)] : { x: 14, y: -14 };
      
      placed.push({ x, y });
      const labelHTML = `${b.brand}<br><span class="muted">${INR.format(b.avg_price)} | ${b.sentiment_score.toFixed(2)}</span>`;
      return `<div class="point" style="left:${x}%;bottom:${y}%"></div><div class="point-label" style="left:${x}%;bottom:${y}%;transform:translate(${offset.x}px,${offset.y}px)">${labelHTML}</div>`;
    })
    .join("");
}

function renderDiscountBars(brands) {
  const maxDiscount = Math.max(...brands.map((b) => b.avg_discount), 1);
  $("discountBars").innerHTML = brands
    .sort((a, b) => b.avg_discount - a.avg_discount)
    .map(
      (b) => `<div class="bar-row"><strong>${b.brand}</strong><div class="bar-track"><div class="bar-fill" style="width:${(b.avg_discount / maxDiscount) * 100}%"></div></div><span>${Number(b.avg_discount).toFixed(1)}%</span></div>`
    )
    .join("");
}

function renderBrandTable(brands) {
  const sorted = [...brands].sort((a, b) => {
    const av = a[state.sortKey];
    const bv = b[state.sortKey];
    if (typeof av === "string") return av.localeCompare(bv) * state.sortDir;
    return (av - bv) * state.sortDir;
  });
  $("brandTable").innerHTML = sorted
    .map(
      (b) => `<tr>
        <td><strong>${b.brand}</strong><br><span class="muted">${b.price_band}</span></td>
        <td>${INR.format(b.avg_price)}</td>
        <td>${Number(b.avg_discount).toFixed(1)}%</td>
        <td>${Number(b.avg_rating).toFixed(2)}</td>
        <td>${b.sampled_reviews}<br><span class="muted">${b.market_review_count.toLocaleString("en-IN")} marketplace reviews</span></td>
        <td>${Number(b.sentiment_score).toFixed(2)}</td>
        <td>${Number(b.value_for_money_score).toFixed(2)}</td>
        <td>${tags(b.top_praise, false)}<br>${tags(b.top_complaints, true)}</td>
      </tr>`
    )
    .join("");
}

function tags(items, negative) {
  return items.map((i) => `<span class="tag ${negative ? "neg" : ""}">${i.theme}</span>`).join("");
}

function renderProducts(products) {
  $("productList").innerHTML = products
    .sort((a, b) => b.sentiment_score - a.sentiment_score)
    .map(
      (p) => `<button type="button" class="product-card ${p.product_id === state.selectedProductId ? "active" : ""}" data-id="${p.product_id}">
        <strong>${p.title}</strong>
        <span>${p.brand} | ${p.size} | ${INR.format(p.selling_price_inr)} | ${p.rating} stars | ${p.sentiment_band}</span>
      </button>`
    )
    .join("");
  document.querySelectorAll(".product-card").forEach((card) => {
    card.addEventListener("click", () => {
      state.selectedProductId = card.dataset.id;
      render();
    });
  });
}

function renderProductDetail(products) {
  const product = products.find((p) => p.product_id === state.selectedProductId);
  if (!product) {
    $("productDetail").innerHTML = `<p class="muted">No product matches the current filters.</p>`;
    return;
  }
  $("productDetail").innerHTML = `
    <p class="eyebrow">${product.brand} | ${product.category}</p>
    <h3>${product.title}</h3>
    <p class="muted">${product.review_synthesis}</p>
    <div class="detail-metrics">
      <div><span>Price</span><strong>${INR.format(product.selling_price_inr)}</strong></div>
      <div><span>List price</span><strong>${INR.format(product.list_price_inr)}</strong></div>
      <div><span>Discount</span><strong>${Number(product.discount_pct).toFixed(1)}%</strong></div>
      <div><span>Sentiment</span><strong>${Number(product.sentiment_score).toFixed(2)}</strong></div>
      <div><span>Rating</span><strong>${Number(product.rating).toFixed(1)}</strong></div>
      <div><span>Review count</span><strong>${product.review_count.toLocaleString("en-IN")}</strong></div>
      <div><span>Sample reviews</span><strong>${product.sampled_reviews}</strong></div>
      <div><span>Band</span><strong>${product.price_band}</strong></div>
    </div>
    <div class="theme-columns">
      <div><h2>Appreciation themes</h2>${tags(product.top_praise, false)}</div>
      <div><h2>Complaint themes</h2>${tags(product.top_complaints, true)}</div>
    </div>
    <div class="aspect-list">
      <h2>Aspect-level sentiment</h2>
      ${product.aspect_sentiment
        .map((a) => {
          const width = ((a.sentiment + 1) / 2) * 100;
          return `<div class="aspect-row"><span>${a.aspect}</span><div class="aspect-track"><div class="aspect-fill" style="width:${width}%"></div></div><strong>${Number(a.sentiment).toFixed(2)}</strong></div>`;
        })
        .join("")}
    </div>
  `;
}

function renderInsights() {
  $("insightList").innerHTML = state.data.insights
    .map((insight) => `<article class="insight"><strong>${insight.title}</strong><p>${insight.detail}</p></article>`)
    .join("");
}

init().catch((error) => {
  document.body.innerHTML = `<main><h1>Dashboard data failed to load</h1><p>${error.message}</p></main>`;
});
