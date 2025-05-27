
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import requests

st.set_page_config(page_title="SaaS Cost Calculator", layout="wide")

# Constants
CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "INR": "₹", "GBP": "£", "JPY": "¥"}
SUPPORTED_CURRENCIES = list(CURRENCY_SYMBOLS.keys())

# Helper function to calculate base costs in USD
def calculate_costs(users, api_calls, storage, revenue, emails):
    return {
        "User Costs": users * 0.05,
        "API Costs": api_calls * 0.0001,
        "Storage Costs": storage * 1,
        "Email Costs": emails * 0.002,
        "Revenue Share": revenue * 0.01,
    }

# Fetch exchange rates
@st.cache_data(ttl=3600)
def get_exchange_rates():
    url = "https://api.exchangeratesapi.io/v1/latest"
    params = {
        "access_key": "ee6999efe7cc88e6b2abbb3381daac74",
        "symbols": ",".join(SUPPORTED_CURRENCIES)
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("rates", {})
    else:
        st.error(f"Failed to fetch exchange rates: {response.status_code}")
        return {}

# Cost table and conversion
def generate_cost_dataframe(costs_usd, conversion_rate, symbol):
    costs_converted = {k: v * conversion_rate for k, v in costs_usd.items()}
    df = pd.DataFrame(list(costs_converted.items()), columns=["Service", "Cost"])
    df["Cost"] = df["Cost"].map(lambda x: f"{symbol}{x:,.2f}")
    return df

# Generate pie chart
def plot_pie_chart(costs):
    fig, ax = plt.subplots()
    labels = list(costs.keys())
    sizes = list(costs.values())
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    return fig

# Generate monthly trend data
def plot_monthly_trend(total_cost, cycle):
    monthly_cost = total_cost / 12 if cycle == "Yearly" else total_cost
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    trend_df = pd.DataFrame({"Month": months, "Cost": [monthly_cost]*12})
    return trend_df

# Export PDF
def generate_pdf(df):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "SaaS Cost Calculator Report")
    c.setFont("Helvetica", 12)
    y = height - 100
    for i in range(len(df)):
        line = f"{df['Service'][i]}: {df['Cost'][i]}"
        c.drawString(50, y, line)
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return buffer

# --- Main App Logic ---
rates = get_exchange_rates()

st.title("💰 SaaS Cost Calculator")
col1, col2 = st.columns(2)

with col1:
    users = st.number_input("Users", 0, value=1000)
    api_calls = st.number_input("API Calls", 0, value=1000000)
    storage = st.number_input("Storage (GB)", 0, value=10)
    emails = st.number_input("Emails Sent", 0, value=5000)

with col2:
    revenue = st.number_input("Revenue ($)", 0, value=10000)
    cycle = st.selectbox("Billing Cycle", ["Monthly", "Yearly"])
    currency = st.selectbox("Currency", SUPPORTED_CURRENCIES)

# Conversion rate
eur_to_usd = rates.get("USD")
eur_to_target = rates.get(currency)
conversion_rate = (1 / eur_to_usd) * eur_to_target if eur_to_usd and eur_to_target else 1
symbol = CURRENCY_SYMBOLS.get(currency, "$")

# Base and custom cost calculation
base_costs = calculate_costs(users, api_calls, storage, revenue, emails)
custom_services = []
num_services = st.number_input("Number of Custom Services", 0, 10, 0)
for i in range(num_services):
    name = st.text_input(f"Service {i+1} Name", key=f"name_{i}")
    fixed = st.number_input(f"Fixed Cost", key=f"fixed_{i}")
    per_user = st.number_input(f"Per User Cost", key=f"user_{i}")
    custom_services.append((name, fixed + per_user * users))

costs_usd = base_costs.copy()
for name, total in custom_services:
    costs_usd[name] = total

if cycle == "Yearly":
    costs_usd = {k: v * 12 for k, v in costs_usd.items()}

df = generate_cost_dataframe(costs_usd, conversion_rate, symbol)
costs_converted = {k: v * conversion_rate for k, v in costs_usd.items()}

# Display
st.dataframe(df.set_index("Service"))
st.subheader("Cost Distribution")
st.pyplot(plot_pie_chart(costs_converted))
st.subheader("Monthly Cost Trend")
st.line_chart(plot_monthly_trend(sum(costs_converted.values()), cycle).set_index("Month"))

# Export
st.subheader("Export")
col1, col2 = st.columns(2)

with col1:
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name="cost_report.csv", mime="text/csv")

with col2:
    pdf_buffer = generate_pdf(df)
    st.download_button("Download PDF", data=pdf_buffer, file_name="cost_report.pdf", mime="application/pdf")
