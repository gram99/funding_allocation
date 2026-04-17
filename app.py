import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# 1. Page Configuration
st.set_page_config(page_title="PHA Allocation Dashboard", layout="wide")
st.title("🏗️ PHA Recovery Readiness & Allocation Tool")

# 2. Sidebar: Upload & Scenarios
with st.sidebar:
    st.header("📂 Data Source")
    # File Uploader for CSV/TXT
    uploaded_file = st.file_uploader("Upload PHA Data (.csv or .txt)", type=["csv", "txt"])
    
    st.divider()
    st.header("Settings")
    compare_mode = st.toggle("Enable Comparison Mode", value=False)
    
    scenarios = {
        "Balanced (Default)": {"phys": 35, "fin": 35, "cap": 30},
        "Focus on Physical Assets": {"phys": 60, "fin": 20, "cap": 20},
        "Focus on Financial Stability": {"phys": 20, "fin": 60, "cap": 20},
        "Focus on Execution Capacity": {"phys": 20, "fin": 20, "cap": 60}
    }

    def get_weights(label):
        st.subheader(f"Weights: {label}")
        preset = st.selectbox(f"Strategy for {label}", list(scenarios.keys()), key=f"sel_{label}")
        defaults = scenarios[preset]
        p = st.number_input(f"Physical (%) - {label}", 0, 100, defaults["phys"], key=f"p_{label}")
        f = st.number_input(f"Financial (%) - {label}", 0, 100, defaults["fin"], key=f"f_{label}")
        c = st.number_input(f"Capacity (%) - {label}", 0, 100, defaults["cap"], key=f"c_{label}")
        total = p + f + c
        if total != 100: st.error(f"⚠️ {label} must total 100% (Current: {total}%)")
        return p, f, c, total

    p1, f1, c1, t1 = get_weights("Scenario A")
    p2, f2, c2, t2 = (0,0,0,100)
    if compare_mode:
        st.divider()
        p2, f2, c2, t2 = get_weights("Scenario B")

# 3. Calculation Helper
def calculate_alloc(df_in, p, f, c):
    df = df_in.copy()
    # Normalization Logic
    df['phys_n'] = (df['Physical Score']/100 + (df['Physical Trend']-df['Physical Trend'].min())/(df['Physical Trend'].max()-df['Physical Trend'].min()))/2
    df['fin_n'] = (np.clip(df['Quick Ratio']/2,0,1) + (1-np.clip(df['TAR Ratio (%)']/20,0,1)))/2
    df['cap_n'] = (df['Occupancy (%)']/100 + df['CFP Obligation (%)']/100)/2
    # Allocation
    df['Index'] = (df['phys_n']*(p/100)) + (df['fin_n']*(f/100)) + (df['cap_n']*(c/100))
    df['Allocation ($)'] = (df['Index'] / df['Index'].sum()) * 15000000
    return df[['PHA Name', 'Index', 'Allocation ($)']]

# 4. Main App Logic
if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    st.success(f"Loaded {len(df_raw)} records from {uploaded_file.name}")
else:
    # Fallback to sample data if no file uploaded
    df_raw = pd.DataFrame({
        "PHA Name": ["HA A", "HA B", "HA C", "HA D", "HA E"],
        "Physical Score": [45, 52, 38, 61, 49],
        "Physical Trend": [5, -2, 8, 1, -4],
        "Quick Ratio": [0.8, 1.2, 0.5, 1.5, 0.9],
        "TAR Ratio (%)": [12, 4, 18, 3, 9],
        "Occupancy (%)": [88, 97, 82, 98, 91],
        "CFP Obligation (%)": [75, 95, 60, 92, 85]
    })
    st.info("Using sample data. Upload a CSV in the sidebar to use your own.")

# Perform Calculations
if t1 == 100 and t2 == 100:
    res1 = calculate_alloc(df_raw, p1, f1, c1)
    
    if compare_mode:
        res2 = calculate_alloc(df_raw, p2, f2, c2)
        final_df = res1.merge(res2, on="PHA Name", suffixes=('_A', '_B'))
        final_df['Difference ($)'] = final_df['Allocation ($)_B'] - final_df['Allocation ($)_A']
        
        st.subheader("Scenario Comparison")
        st.dataframe(final_df.style.format({'Index_A': '{:.2f}', 'Allocation ($)_A': '${:,.2f}', 'Index_B': '{:.2f}', 'Allocation ($)_B': '${:,.2f}', 'Difference ($)': '${:,.2f}'}), use_container_width=True)
        st.plotly_chart(px.bar(final_df, x='PHA Name', y='Difference ($)', color='Difference ($)', color_continuous_scale='RdBu_r'), use_container_width=True)
    else:
        final_df = res1
        st.subheader("Allocation Results")
        st.dataframe(final_df.style.format({'Index': '{:.2f}', 'Allocation ($)': '${:,.2f}'}), use_container_width=True)

    # 5. Notes & Justification Section
    st.divider()
    st.subheader("📝 Justification & Notes")
    user_notes = st.text_area("Provide context for these weighting assumptions (will be included in the export):", 
                              placeholder="e.g., Prioritizing Physical Score due to recent site inspection findings...")

    # 6. Export to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, index=False, sheet_name='Allocations')
        # Add a separate sheet for weights and notes
        summary_data = {
            "Parameter": ["Scenario A Weights", "Scenario B Weights (if enabled)", "Total Funding", "Notes"],
            "Value": [f"Phys:{p1} Fin:{f1} Cap:{c1}", f"Phys:{p2} Fin:{f2} Cap:{c2}" if compare_mode else "N/A", "$15,000,000", user_notes]
        }
        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Simulation_Meta')

    st.download_button(
        label="📥 Download Audit-Ready Excel Report",
        data=output.getvalue(),
        file_name="pha_funding_simulation.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
