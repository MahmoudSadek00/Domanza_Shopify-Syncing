import streamlit as st
import pandas as pd

st.title("Shopify vs Nard Inventory Sync Check")

# File uploaders
pqe_file = st.file_uploader("Upload Products_Quantities_export CSV", type="csv")
ie_file = st.file_uploader("Upload inventory_export CSV", type="csv")

if pqe_file and ie_file:
    # Read CSVs
    pqe = pd.read_csv(pqe_file)
    ie = pd.read_csv(ie_file)

    # Filter only Domanza location
    ie = ie[ie["Location"] == "Domanza"]

    # Join on barcode/SKU
    merged = pd.merge(
        pqe,
        ie,
        how="left",
        left_on="barcodes",
        right_on="SKU"
    )

    # Calculate fields
    merged["nard_qty"] = merged["available_quantity"]
    merged["shopify_qty"] = merged["Available (not editable)"]
    merged["qty_diff"] = merged["nard_qty"].fillna(0) - merged["shopify_qty"].fillna(0)

    def get_flag(row):
        if pd.notna(row["nard_qty"]) and row["nard_qty"] > 0 and pd.isna(row["shopify_qty"]):
            return "not available_in_shopify"
        elif row["nard_qty"] == 0 and pd.isna(row["shopify_qty"]):
            return "dead_item"
        elif row["nard_qty"] != row["shopify_qty"]:
            return "miss match_qty"
        elif row["nard_qty"] == row["shopify_qty"]:
            return "synced_sku"
        return None

    merged["sku_flag"] = merged.apply(get_flag, axis=1)

    # Select final columns
    final_df = merged[[
        "name_ar",
        "barcodes",
        "nard_qty",
        "shopify_qty",
        "qty_diff",
        "sale_price",
        "sku_flag"
    ]]

    st.dataframe(final_df)

    # Download option
    csv = final_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Results CSV", csv, "sync_check_results.csv", "text/csv")
