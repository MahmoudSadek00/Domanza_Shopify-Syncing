import streamlit as st
import pandas as pd

st.title("Domanza_Shopify Syncing")

# File upload option
uploaded_pqe = st.file_uploader("Upload Products_Quantities_export (CSV/Excel)", type=["csv", "xlsx"])
uploaded_ie = st.file_uploader("Upload inventory_export (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_pqe and uploaded_ie:
    # Read files
    if uploaded_pqe.name.endswith(".csv"):
        pqe = pd.read_csv(uploaded_pqe)
    else:
        pqe = pd.read_excel(uploaded_pqe)

    if uploaded_ie.name.endswith(".csv"):
        ie = pd.read_csv(uploaded_ie)
    else:
        ie = pd.read_excel(uploaded_ie)

    # Filter branch
    pqe = pqe[pqe["branch_name"] == "Domanza"]

    # Merge
    merged = pd.merge(
        pqe,
        ie,
        how="left",
        left_on="barcodes",
        right_on="SKU",
        suffixes=("_nard", "_shopify")
    )

    # Calculate fields
    merged["nard_qty"] = merged["available_quantity"]
    merged["shopify_qty"] = merged["Domanza"]
    merged["qty_diff"] = (merged["available_quantity"] - merged["Domanza"]).fillna(0)

    # Define flag
    def get_flag(row):
        if row["nard_qty"] > 0 and pd.isna(row["shopify_qty"]):
            return "not available_in_shopify"
        elif row["nard_qty"] == 0 and pd.isna(row["shopify_qty"]):
            return "dead_item"
        elif row["nard_qty"] != row["shopify_qty"]:
            return "miss match_qty"
        elif row["nard_qty"] == row["shopify_qty"]:
            return "synced_sku"
        else:
            return None

    merged["sku_flag"] = merged.apply(get_flag, axis=1)

    # Final dataframe
    final_df = merged[[
        "name_ar", "barcodes", "nard_qty", "shopify_qty", "qty_diff", "sale_price", "sku_flag"
    ]]

    # Show table
    st.dataframe(final_df, use_container_width=True)

    # Download CSV
    st.download_button(
        label="Download CSV",
        data=final_df.to_csv(index=False).encode("utf-8"),
        file_name="domanza_shopify_compare.csv",
        mime="text/csv"
    )
