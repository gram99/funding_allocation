import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# 1. Page Configuration
st.set_page_config(page_title="PHA Allocation Dashboard", layout="wide")
st.title("🏗️ PHA Recovery Readiness & Allocation Tool")

# REQUIRED COLUMNS LIST
REQUIRED_COLS = [
    "PHA Name", "Physical Score", "Physical Trend", 
    "Quick Ratio", "TAR Ratio (%)", "Occupancy (%)", "CFP Obligation (%)"
]

# 2. Sidebar: Upload & Scenarios
with st.sidebar:
    st.header("📂 Data Source")
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
        if total != 100: st.error(f"⚠️ {label} total must be 100% (Current: {total}%)")
        return p, f, c, total

    p1, f1, c1, t1 = get_weights("Scenario A")
    p2, f2, c2, t2 = (0,0,0,100)
    if compare_mode:
        st.divider()
        p2, f2, c2, t2 = get_weights("Scenario B")

# 3. Validation Logic
def validate_data(df):
    errors = []
    # Check Columns
    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        errors.append(f"Missing columns: {', '.join(missing)}")
    
    if not errors:
        # Check for Non-Numeric values in data columns
        for col in REQUIRED_COLS[1:]:
            if not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Column '{col}' contains non-numeric data or text.")
        
        # Check for missing (NaN) values
        if df[REQUIRED_COLS].isnull().values.any():
            errors.append("File contains empty cells. Please fill all data points.")

    return errors

# 4. Calculation Helper
def calculate_alloc(df_in, p, f, c):
    df = df_in.copy()
    # Normalization
    df['phys_n'] = (df['Physical Score']/100 + (df['Physical Trend']-df['Physical Trend'].min())/(df['Physical Trend'].max()-df['Physical Trend'].min()))/2
    df['fin_n'] = (np.clip(df['Quick Ratio']/2,0,1) + (1-np.clip(df['TAR Ratio (%)']/20,0,1)))/2
    df['cap_n'] = (df['Occupancy (%)']/100 + df['CFP Obligation (%)']/100)/2
    # Allocation
    df['Index'] = (df['phys_n']*(p/100)) + (df['fin_n']*(f/100)) + (df['cap_n']*(c/100))
    df['Allocation ($)'] = (df['Index'] / df['Index'].sum()) * 15000000
    return df[['PHA Name', 'Index', 'Allocation ($)']]

# 5. Main App Logic
data_ready = False
if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    val_errors = validate_data(df_raw)
    
    if val_errors:
        for err in val_errors:
            st.error(f"❌ {err}")
        st.info("💡 Ensure your file has these exact headers: " + ", ".join(REQUIRED_COLS))
    else:
        st.success(f"✅ Data Validated: {len(df_raw)} PHAs Loaded")
        data_ready = True
else:
    # Use sample data as fallback
    df_raw = pd.DataFrame({
        "PHA Name": ["HA A", "HA B", "HA C", "HA D", "HA E"],
        "Physical Score": [45, 52, 38, 61, 49],
        "Physical Trend": [5, -2, 8, 1, -4],
        "Quick Ratio": [0.8, 1.2, 0.5, 1.5, 0.9],
        "TAR Ratio (%)": [12, 4, 18, 3, 9],
        "Occupancy (%)": [88, 97, 82, 98, 91],
        "CFP Obligation (%)": [75, 95, 60, 92, 85]
    })
    st.info("ℹ️ Using sample data. Upload a CSV to perform a real analysis.")
    data_ready = True

# Execute only if data is valid and weights are balanced
if data_ready and t1 == 100 and t2 == 100:
    res1 = calculate_alloc(df_raw, p1, f1, c1)
    
    if compare_mode:
        res2 = calculate_alloc(df_raw, p2, f2, c2)
        final_df = res1.merge(res2, on="PHA Name", suffixes=('_A', '_B'))
        final_df['Difference ($)'] = final_df['Allocation ($)_B'] - final_df['Allocation ($)_A']
        
        # UI Display for Comparison
        st.subheader("Scenario Comparison: Analysis")
        st.dataframe(final_df.style.format({
            'Index_A': '{:.2f}', 'Allocation ($)_A': '${:,.2f}', 
            'Index_B': '{:.2f}', 'Allocation ($)_B': '${:,.2f}', 
            'Difference ($)': '${:,.2f}'
        }), use_container_width=True)
        
        st.plotly_chart(px.bar(final_df, x='PHA Name', y='Difference ($)', 
                               color='Difference ($)', color_continuous_scale='RdBu_r',
                               title="Shift in Funds (Scenario B - Scenario A)"), use_container_width=True)
    else:
        final_df = res1
        st.subheader("Allocation Results")
        st.dataframe(final_df.style.format({'Index': '{:.2f}', 'Allocation ($)': '${:,.2f}'}), use_container_width=True)

    # 6. Notes & Export
    st.divider()
    user_notes = st.text_area("📝 Strategy Justification:", placeholder="Enter your reasoning for these assumptions...")

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, index=False, sheet_name='Allocations')
        meta = pd.DataFrame({
            "Parameter": ["Scenario A", "Scenario B", "Total Funding", "Justification"],
            "Value": [f"P:{p1} F:{f1} C:{c1}", f"P:{p2} F:{f2} C:{c2}" if compare_mode else "None", "$15M", user_notes]
        })
        meta.to_excel(writer, index=False, sheet_name='Metadata')

    st.download_button("📥 Export Audit Report", output.getvalue(), "pha_audit_report.xlsx", 
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
