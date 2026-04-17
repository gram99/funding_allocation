import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="PHA Recovery Allocation", layout="wide")
st.title("PHA Recovery Readiness & Allocation Tool")
st.markdown("Simulate the allocation of **$15M** in funding based on management performance and capacity.")

# 2. Sidebar & Scenario Logic
with st.sidebar:
    st.header("Simulation Scenarios")
    
    # Define Scenarios
    scenarios = {
        "Custom": None,
        "Balanced (Default)": {"phys": 35, "fin": 35, "cap": 30},
        "Focus on Physical Assets": {"phys": 60, "fin": 20, "cap": 20},
        "Focus on Financial Stability": {"phys": 20, "fin": 60, "cap": 20},
        "Focus on Execution Capacity": {"phys": 20, "fin": 20, "cap": 60}
    }
    
    selected_scenario = st.selectbox("Choose a pre-set strategy:", list(scenarios.keys()))

    st.divider()
    st.header("Weight Configuration")
    
    # Get defaults based on scenario selection
    defaults = scenarios[selected_scenario] if scenarios[selected_scenario] else {"phys": 35, "fin": 35, "cap": 30}

    # Physical Management Inputs
    phys_w_input = st.slider("Physical Management Weight (%)", 0, 100, defaults["phys"], key="phys_s")
    phys_w = st.number_input("Exact Physical Weight", 0, 100, phys_w_input, key="phys_n")
    
    st.divider()

    # Financial Management Inputs
    fin_w_input = st.slider("Financial Management Weight (%)", 0, 100, defaults["fin"], key="fin_s")
    fin_w = st.number_input("Exact Financial Weight", 0, 100, fin_w_input, key="fin_n")
    
    st.divider()

    # Capacity/Exit Inputs
    cap_w_input = st.slider("Capacity/Exit Weight (%)", 0, 100, defaults["cap"], key="cap_s")
    cap_w = st.number_input("Exact Capacity Weight", 0, 100, cap_w_input, key="cap_n")

    st.divider()

    total_weight = phys_w + fin_w + cap_w
    
    if total_weight != 100:
        st.error(f"⚠️ Total Weight: {total_weight}% (Must be 100%)")
    else:
        st.success("✅ Weights Balanced")

# 3. Data Loading
@st.cache_data
def load_pha_data():
    phas = ["Housing Authority A", "Housing Authority B", "Housing Authority C", "Housing Authority D", "Housing Authority E"]
    data = {
        "PHA Name": phas,
        "Physical Score": [45, 52, 38, 61, 49], 
        "Physical Trend": [5, -2, 8, 1, -4],    
        "Quick Ratio": [0.8, 1.2, 0.5, 1.5, 0.9], 
        "TAR Ratio (%)": [12, 4, 18, 3, 9],      
        "Occupancy (%)": [88, 97, 82, 98, 91],   
        "CFP Obligation (%)": [75, 95, 60, 92, 85]
    }
    return pd.DataFrame(data)

df = load_pha_data().copy()

# 4. Calculation Logic
if total_weight == 100:
    # --- Physical Normalization ---
    df['phys_score_norm'] = df['Physical Score'] / 100
    trend_range = df['Physical Trend'].max() - df['Physical Trend'].min()
    df['phys_trend_norm'] = 0.5 if trend_range == 0 else (df['Physical Trend'] - df['Physical Trend'].min()) / trend_range
    phys_subtotal = (df['phys_score_norm'] + df['phys_trend_norm']) / 2

    # --- Financial Normalization ---
    df['quick_norm'] = np.clip(df['Quick Ratio'] / 2.0, 0, 1)
    df['tar_norm'] = 1 - np.clip(df['TAR Ratio (%)'] / 20, 0, 1)
    fin_subtotal = (df['quick_norm'] + df['tar_norm']) / 2

    # --- Capacity Normalization ---
    df['occ_norm'] = df['Occupancy (%)'] / 100
    df['cfp_norm'] = df['CFP Obligation (%)'] / 100
    cap_subtotal = (df['occ_norm'] + df['cfp_norm']) / 2

    # Final Index Calculation
    df['Recovery_Index'] = (
        (phys_subtotal * (phys_w/100)) + 
        (fin_subtotal * (fin_w/100)) + 
        (cap_subtotal * (cap_w/100))
    )

    # Allocation Logic ($15M)
    total_index_score = df['Recovery_Index'].sum()
    df['Allocation ($)'] = (df['Recovery_Index'] / total_index_score) * 15000000

    # 5. Visual Display
    st.header(f"Results: {selected_scenario}")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Funding Allocation Summary")
        formatted_df = df[['PHA Name', 'Recovery_Index', 'Allocation ($)']].sort_values('Recovery_Index', ascending=False)
        st.dataframe(
            formatted_df.style.format({'Recovery_Index': '{:.2f}', 'Allocation ($)': '${:,.2f}'}),
            use_container_width=True,
            hide_index=True
        )

    with col2:
        st.subheader("Funding Split")
        fig = px.pie(df, values='Allocation ($)', names='PHA Name', hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    
    # Comparison Chart
    st.subheader("Readiness Index Comparison")
    fig_bar = px.bar(df.sort_values('Recovery_Index'), x='Recovery_Index', y='PHA Name', orientation='h',
                     color='Recovery_Index', color_continuous_scale='Blues',
                     labels={'Recovery_Index': 'Index Score', 'PHA Name': 'Authority'})
    st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.warning("⚠️ The current weights do not equal 100%. Please adjust the sliders or select a pre-set scenario.")
