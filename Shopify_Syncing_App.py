import streamlit as st
import pandas as pd

st.set_page_config(page_title="Domanza Shopify Syncing", layout="wide")

st.title("Domanza Shopify Syncing")

uploaded_pqe = st.file_uploader("Upload Products_Quantities_export CSV", type="csv")
uploaded_ie = st.file_uploader("Upload inventory_export CSV", type="csv")

if uploaded_pqe and uploaded_ie:
    pqe = pd.read_csv(uploaded_pqe)
    ie = pd.read_csv(uploaded_ie)

    ie.rename(columns=lambda x: x.strip(), inplace=True)
    pqe.rename(columns=lambda x: x.strip(), inplace=True)

    merged = pd.merge(
        pqe,
        ie,
        left_on="barcodes",
        right_on="SKU",
        how="left"
    )

    merged["nard_qty"] = merged["available_quantity"]
    merged["shopify_qty"] = merged["Available (not editable)"]
    merged["qty_diff"] = merged["nard_qty"].fillna(0) - merged["shopify_qty"].fillna(0)

    def flag(row):
        if row["nard_qty"] > 0 and pd.isna(row["shopify_qty"]):
            return "not available_in_shopify"
        elif row["nard_qty"] == 0 and pd.isna(row["shopify_qty"]):
            return "dead_item"
        elif row["nard_qty"] != row["shopify_qty"]:
            return "miss match_qty"
        elif row["nard_qty"] == row["shopify_qty"]:
            return "synced_sku"
        return None

    merged["sku_flag"] = merged.apply(flag, axis=1)

    result = merged[[
        "name_ar", "barcodes", "nard_qty",
        "shopify_qty", "qty_diff", "sale_price", "sku_flag"
    ]]

    st.subheader("Comparison Result")
    st.dataframe(result, use_container_width=True)

    csv = result.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Result CSV",
        csv,
        "shopify_sync_result.csv",
        "text/csv"
    )
