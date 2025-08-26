import streamlit as st
import pandas as pd

st.set_page_config(page_title="Domanza Shopify Syncing", layout="wide")

st.title("📦 Domanza vs Shopify Stock Sync Checker")

# --- File uploaders ---
st.sidebar.header("Upload Files")
pqe_file = st.sidebar.file_uploader("Upload Products_Quantities_export.xlsx", type=["xlsx"])
ie_file = st.sidebar.file_uploader("Upload inventory_export.xlsx", type=["xlsx"])

if pqe_file and ie_file:
    # Read both Excel files
    pqe = pd.read_excel(pqe_file)
    ie = pd.read_excel(ie_file)

    # Make sure columns exist
    st.write("✅ Loaded PQE columns:", list(pqe.columns))
    st.write("✅ Loaded Inventory columns:", list(ie.columns))

    # Handle tricky column names
    shopify_col = None
    for col in ie.columns:
        if "Available" in col:  # fuzzy match
            shopify_col = col
            break

    if shopify_col is None:
        st.error("❌ Couldn't find column containing 'Available' in inventory_export file.")
    else:
        # Rename for consistency
        ie = ie.rename(columns={shopify_col: "shopify_qty"})

        # Merge like your SQL
        merged = pd.merge(
            pqe,
            ie,
            how="left",
            left_on="barcodes",
            right_on="SKU"
        )

        # Only filter Domanza location
        merged = merged[merged["Location"] == "Domanza"]
        merged = merged[merged["branch_name"] == "Domanza"]

        # Rename PQE column
        merged["nard_qty"] = merged["available_quantity"]

        # Qty diff
        merged["qty_diff"] = merged["nard_qty"].fillna(0) - merged["shopify_qty"].fillna(0)

        # sku_flag logic
        def flag_row(row):
            if row["nard_qty"] > 0 and pd.isna(row["shopify_qty"]):
                return "not available_in_shopify"
            elif row["nard_qty"] == 0 and pd.isna(row["shopify_qty"]):
                return "dead_item"
            elif row["nard_qty"] != row["shopify_qty"]:
                return "miss match_qty"
            elif row["nard_qty"] == row["shopify_qty"]:
                return "synced_sku"
            return None

        merged["sku_flag"] = merged.apply(flag_row, axis=1)

        # Select relevant columns
        final = merged[
            ["name_ar", "barcodes", "nard_qty", "shopify_qty", "qty_diff", "sale_price", "sku_flag"]
        ]

        # Show results
        st.subheader("Results")
        st.dataframe(final, use_container_width=True)

        # CSV download
        csv = final.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Results as CSV", data=csv, file_name="sync_results.csv", mime="text/csv")

else:
    st.info("👆 Please upload both files to start.")
