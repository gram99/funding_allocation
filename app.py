import streamlit as st
import pandas as pd
import numpy as np

# 1. Page Configuration
st.set_page_config(page_title="PHA Recovery Allocation", layout="wide")
st.title("🏗️ PHA Recovery Readiness & Allocation Tool")
st.markdown("Use this tool to simulate $15M in funding based on management proxies.")

# 2. Sidebar for Adjustable Weights
with st.sidebar:
    st.header("Weight Configuration")
    st.info("Adjust the influence of each management proxy below.")
    phys_w = st.slider("Physical Management Weight", 0, 100, 35)
    fin_w = st.slider("Financial Management Weight", 0, 100, 35)
    cap_w = st.slider("Capacity/Exit Weight", 0, 100, 30)

    total_weight = phys_w + fin_w + cap_w
    if total_weight != 100:
        st.error(f"Total Weight must equal 100%. Current: {total_weight}%")

# 3. Helper: Generate or Load Data
@st.cache_data
def load_pha_data():
    # Replace this with your actual data source: df = pd.read_csv('your_data.csv')
    np.random.seed(42)
    phas = ["Housing Authority A", "Housing Authority B", "Housing Authority C", "Housing Authority D", "Housing Authority E"]
    data = {
        "PHA Name": phas,
        "Physical Score": [45, 52, 38, 61, 49], # Lower is worse
        "Physical Trend": [5, -2, 8, 1, -4],    # Improvement over last 2 years
        "Quick Ratio": [0.8, 1.2, 0.5, 1.5, 0.9], # <1.0 is struggling
        "TAR Ratio (%)": [12, 4, 18, 3, 9],      # Tenant Accounts Receivable (Lower is better)
        "Occupancy (%)": [88, 97, 82, 98, 91],   # Capacity proxy
        "CFP Obligation (%)": [75, 95, 60, 92, 85] # Capacity to spend
    }
    return pd.DataFrame(data)

df = load_pha_data()

# 4. Calculation Logic
if total_weight == 100:
    # Normalize components (0.0 to 1.0 scale)
    # Physical Management: High score + Positive trend
    df['phys_score_norm'] = df['Physical Score'] / 100
    df['phys_trend_norm'] = (df['Physical Trend'] - df['Physical Trend'].min()) / (df['Physical Trend'].max() - df['Physical Trend'].min())
    phys_subtotal = (df['phys_score_norm'] + df['phys_trend_norm']) / 2

    # Financial Management: High Quick Ratio + Low TAR
    df['quick_norm'] = np.clip(df['Quick Ratio'] / 2.0, 0, 1) # Cap at 2.0
    df['tar_norm'] = 1 - (df['TAR Ratio (%)'] / 20) # Assume 20% is worst case
    fin_subtotal = (df['quick_norm'] + df['tar_norm']) / 2

    # Capacity: High Occupancy + High Obligation
    df['occ_norm'] = df['Occupancy (%)'] / 100
    df['cfp_norm'] = df['CFP Obligation (%)'] / 100
    cap_subtotal = (df['occ_norm'] + df['cfp_norm']) / 2

    # Final Recovery Readiness Index
    df['Recovery_Index'] = (
        (phys_subtotal * (phys_w/100)) + 
        (fin_subtotal * (fin_w/100)) + 
        (cap_subtotal * (cap_w/100))
    )

    # Allocation of $15,000,000
    total_index_score = df['Recovery_Index'].sum()
    df['Allocation ($)'] = (df['Recovery_Index'] / total_index_score) * 15000000

    # 5. Visual Display
    st.subheader("Summary Table")
    formatted_df = df[['PHA Name', 'Recovery_Index', 'Allocation ($)']].sort_values('Recovery_Index', ascending=False)
    st.dataframe(formatted_df.style.format({'Recovery_Index': '{:.2f}', 'Allocation ($)': '${:,.2f}'}))

    st.bar_chart(df.set_index('PHA Name')['Allocation ($)'])
