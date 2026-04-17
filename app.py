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
    
    # Template Download Button
    template_df = pd.DataFrame(columns=REQUIRED_COLS)
    template_csv = template_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV Template", data=template_csv, file_name="pha_template.csv", mime="text/csv")
    
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
    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        errors.append(f"Missing columns: {', '.join(missing)}")
    if not errors:
        for col in REQUIRED_COLS[1:]:
            if not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Column '{col}' contains non-numeric data.")
        if df[REQUIRED_COLS].isnull().values.any():
            errors.append("File contains empty cells.")
    return errors

# 4. Calculation Helper
def calculate_alloc(df_in, p, f, c):
    df = df_in.copy()
    t_min, t_max = df['Physical Trend'].min(), df['Physical Trend'].max()
    t_range = t_max - t_min
    df['phys_n'] = (df['Physical Score']/100 + (0.5 if t_range == 0 else (df['Physical Trend']-t_min)/t_range))/2
    df['fin_n'] = (np.clip(df['Quick Ratio']/2, 0, 1) + (1-np.clip(df['TAR Ratio (%)']/20, 0, 1)))/2
    df['cap_n'] = (df['Occupancy (%)']/100 + df['CFP Obligation (%)']/100)/2
    df['Index'] = (df['phys_n']*(p/100)) + (df['fin_n']*(f/100)) + (df['cap_n']*(c/100))
    df['Allocation ($)'] = (df['Index'] / df['Index'].sum()) * 15000000
    return df[['PHA Name', 'Index', 'Allocation ($)']]

# 5. Main App Logic
data_ready = False
if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    val_errors = validate_data(df_raw)
    if val_errors:
        for err in val_errors: st.error(f"❌ {err}")
    else:
        st.success(f"✅ {len(df_raw)} PHAs Loaded")
        data_ready = True
else:
    df_raw = pd.DataFrame({
        "PHA Name": ["HA A", "HA B", "HA C", "HA D", "HA E"],
        "Physical Score": [45, 52, 38, 61, 49],
        "Physical Trend": [5, -2, 8, 1, -4],
        "Quick Ratio": [0.8, 1.2, 0.5, 1.5, 0.9],
        "TAR Ratio (%)": [12, 4, 18, 3, 9],
        "Occupancy (%)": [88, 97, 82, 98, 91],
        "CFP Obligation (%)": [75, 95, 60, 92, 85]
    })
    st.info("ℹ️ Using sample data.")
    data_ready = True

if data_ready and t1 == 100 and t2 == 100:
    res1 = calculate_alloc(df_raw, p1, f1, c1)
    
    if compare_mode:
        res2 = calculate_alloc(df_raw, p2, f2, c2)
        final_df = res1.merge(res2, on="PHA Name", suffixes=('_A', '_B'))
        final_df['Difference ($)'] = final_df['Allocation ($)_B'] - final_df['Allocation ($)_A']
        
        st.subheader("Allocation Results: Scenario Comparison")
        # hide_index=True removes the first column in both views
        st.dataframe(
            final_df.style.format({
                'Index_A': '{:.2f}', 'Allocation ($)_A': '${:,.2f}', 
                'Index_B': '{:.2f}', 'Allocation ($)_B': '${:,.2f}', 
                'Difference ($)': '${:,.2f}'
            }), 
            use_container_width=True, 
            hide_index=True
        )
        st.plotly_chart(px.bar(final_df, x='PHA Name', y='Difference ($)', color='Difference ($)', color_continuous_scale='RdBu_r'), use_container_width=True)
    else:
        final_df = res1
        st.subheader("Allocation Results")
        # hide_index=True applied here
        st.dataframe(
            final_df.style.format({'Index': '{:.2f}', 'Allocation ($)': '${:,.2f}'}), 
            use_container_width=True, 
            hide_index=True
        )

    st.divider()
    user_notes = st.text_area("📝 Justification & Notes", placeholder="Provide context for these weighting assumptions...")

    # Excel Export
    output = BytesIO()
    try:
        import xlsxwriter
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Allocations')
            meta = pd.DataFrame({"Parameter": ["A", "B", "Notes"], "Value": [f"{p1}/{f1}/{c1}", f"{p2}/{f2}/{c2}" if compare_mode else "N/A", user_notes]})
            meta.to_excel(writer, index=False, sheet_name='Metadata')
        excel_data = output.getvalue()
    except ImportError:
        with pd.ExcelWriter(output) as writer:
            final_df.to_excel(writer, index=False)
        excel_data = output.getvalue()

    st.download_button("📥 Download Audit-Ready Excel Report", excel_data, "pha_audit_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
