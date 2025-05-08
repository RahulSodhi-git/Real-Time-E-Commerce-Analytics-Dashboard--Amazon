import time
import os
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import threading

# =========================== Scraper Function ===========================
def scrape_amazon_products(category_name, search_query, max_pages=5):
    base_url = f"https://www.amazon.de/s?k={search_query}&page={{}}"
    products = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="my_amazon_profile",
            headless=True
        )
        page = context.pages[0] if context.pages else context.new_page()

        for page_num in range(1, max_pages + 1):
            url = base_url.format(page_num)
            print(f"[{category_name}] Page {page_num} → {url}")
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)

            product_cards = page.query_selector_all("div.s-main-slot div[data-component-type='s-search-result']")
            print(f" Found {len(product_cards)} product blocks.")

            if not product_cards:
                print(f"No more products on page {page_num}. Ending early.")
                break

            for card in product_cards:
                try:
                    name_tag = card.query_selector("h2")
                    if not name_tag:
                        continue
                    name = name_tag.inner_text().strip()

                    price_tag = card.query_selector(".a-price .a-offscreen")
                    price = price_tag.inner_text().strip() if price_tag else None

                    rating_raw = card.query_selector("span.a-icon-alt")
                    if rating_raw:
                        rating_text = rating_raw.inner_text().strip()
                        rating = rating_text.split()[0].replace(",", ".")
                    else:
                        rating = None

                    products.append([
                        datetime.now(), category_name, name, price, rating
                    ])
                except Exception as e:
                    print(f" Error parsing one product: {e}")
            time.sleep(1)
        context.close()

    print(f"Finished category: {category_name} — {len(products)} products scraped.\n")
    return products

# =========================== Refresh and Save ===========================
def run_scraper_and_update_excel():
    categories = {
        "Laptops": "laptops",
        "Smartphones": "smartphones",
        "Monitors": "monitore",
        "Books": "b%C3%BCcher",
        "Fashion": "herren mode",
        "Shoes": "sportschuhe",
        "Kitchen": "k%C3%BCchenger%C3%A4te",
        "Beauty": "beauty",
        "Office": "b%C3%BCrobedarf",
        "Headphones": "kopfh%C3%B6rer"
    }

    while True:
        all_data = []
        print("\nStarting full scrape round...")
        for category_name, search_term in categories.items():
            print(f"\nScraping category: {category_name}")
            data = scrape_amazon_products(category_name, search_term, max_pages=5)
            all_data.extend(data)

        df = pd.DataFrame(all_data, columns=["Timestamp", "Category", "Product Name", "Price", "Rating"])

        file_path = "amazon_master.xlsx"
        if os.path.exists(file_path):
            existing_df = pd.read_excel(file_path, engine='openpyxl')
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            combined_df = df

        combined_df.to_excel(file_path, index=False, engine="openpyxl")
        print(f"\nTotal scraped this round: {len(df)} products")
        print(f"Excel updated: {file_path}")
        print("Auto-refreshing after 5 minutes...\n")
        time.sleep(5 * 60)

# =========================== Dashboard ===========================
def load_data():
    df = pd.read_excel("amazon_master.xlsx", engine='openpyxl')
    df["Clean Price"] = pd.to_numeric(df["Price"].str.replace("€", "").str.replace(",", ".").str.extract(r'(\d+\.\d+)')[0], errors='coerce')
    df["Rating"] = pd.to_numeric(df["Rating"], errors='coerce')
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
    df.dropna(subset=["Clean Price", "Rating", "Category"], inplace=True)
    return df

app = dash.Dash(__name__)
app.title = "Amazon Dashboard"

app.layout = html.Div([
    html.H1("Amazon Product Dashboard", style={"textAlign": "center"}),
    dcc.Interval(id='interval-refresh', interval=5 * 60 * 1000, n_intervals=0),

    html.Div([
        html.Label("Select Categories:"),
        dcc.Dropdown(id='category-dropdown', multi=True),
        html.Br(),
        html.Label("Select Rating Range:"),
        dcc.RangeSlider(id='rating-slider', min=0, max=5, step=0.1, marks={i: str(i) for i in range(6)}),
        html.Br(),
        html.Label("Select Price Range (€):"),
        dcc.RangeSlider(id='price-slider', min=0, max=2500, step=10, marks={i: f"€{i}" for i in range(0, 2600, 500)}),
    ], style={"margin": "20px"}),

    dcc.Graph(id='bar-category-count'),
    dcc.Graph(id='scatter-price-rating'),
    dcc.Graph(id='price-distribution-by-category'),
    dcc.Graph(id='line-avg-price-category'),
    dcc.Graph(id='pie-category-share')
])

@app.callback(
    Output('category-dropdown', 'options'),
    Input('interval-refresh', 'n_intervals')
)
def update_category_options(_):
    df = load_data()
    return [{'label': cat, 'value': cat} for cat in sorted(df['Category'].unique())]

@app.callback(
    Output('rating-slider', 'value'),
    Output('price-slider', 'value'),
    Input('interval-refresh', 'n_intervals')
)
def set_slider_ranges(_):
    df = load_data()
    return [df['Rating'].min(), df['Rating'].max()], [df['Clean Price'].min(), df['Clean Price'].max()]

@app.callback(
    Output('bar-category-count', 'figure'),
    Output('scatter-price-rating', 'figure'),
    Output('price-distribution-by-category', 'figure'),
    Output('line-avg-price-category', 'figure'),
    Output('pie-category-share', 'figure'),
    Input('category-dropdown', 'value'),
    Input('rating-slider', 'value'),
    Input('price-slider', 'value'),
    Input('interval-refresh', 'n_intervals')
)
def update_graphs(selected_categories, rating_range, price_range, _):
    df = load_data()
    if selected_categories:
        df = df[df['Category'].isin(selected_categories)]
    df = df[(df['Rating'] >= rating_range[0]) & (df['Rating'] <= rating_range[1])]
    df = df[(df['Clean Price'] >= price_range[0]) & (df['Clean Price'] <= price_range[1])]

    bar_fig = px.bar(df.groupby("Category").size().reset_index(name='Count'),
                     x="Category", y="Count", title="Product Count per Category")

    scatter_fig = px.scatter(df, x="Clean Price", y="Rating", color="Category",
                             hover_data=["Product Name"], title="Price vs Rating")

    safe_max = max(df['Clean Price'].max(), 2500)
    price_bins = pd.cut(df['Clean Price'], bins=[0, 50, 100, 200, 500, 1000, 2000, safe_max])
    price_dist = df.groupby([price_bins.astype(str), 'Category']).size().reset_index(name='Count')
    price_dist.columns = ['Price Range', 'Category', 'Count']
    price_hist = px.bar(price_dist, x='Price Range', y='Count', color='Category', barmode='group',
                        title="Product Count in Price Ranges by Category")

    line_fig = px.line(df.groupby(["Timestamp", "Category"])["Clean Price"].mean().reset_index(),
                       x="Timestamp", y="Clean Price", color="Category",
                       title="Avg Price per Category Over Time")

    pie_fig = px.pie(df, names="Category", title="Share of Products by Category")

    return bar_fig, scatter_fig, price_hist, line_fig, pie_fig

if __name__ == "__main__":
    threading.Thread(target=run_scraper_and_update_excel, daemon=True).start()
    app.run(debug=True, port=8050)

### link for the dashboard: - http://127.0.0.1:8050/
