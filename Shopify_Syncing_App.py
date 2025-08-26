import streamlit as st
import pandas as pd

# رفع ملفات CSV (Products_Quantities_export و inventory_export)
st.title("🔍 Shopify vs Nard Stock Sync Checker")

pqe_file = st.file_uploader("Upload Products_Quantities_export CSV", type=["csv"])
ie_file = st.file_uploader("Upload inventory_export CSV", type=["csv"])

if pqe_file and ie_file:
    # قراءة الملفات
    pqe = pd.read_csv(pqe_file)
    ie = pd.read_csv(ie_file)

    # فلترة Inventory export على Location = Domanza
    ie = ie[ie["Location"] == "Domanza"]

    # Merge
    df = pd.merge(
        pqe[pqe["branch_name"] == "Domanza"],
        ie,
        left_on="barcodes",
        right_on="SKU",
        how="left"
    )

    # حساب الأعمدة المطلوبة
    df["nard_qty"] = df["available_quantity"]
    df["shopify_qty"] = df["Available (not editable)"]
    df["qty_diff"] = df["nard_qty"].fillna(0) - df["shopify_qty"].fillna(0)

    def flag(row):
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

    df["sku_flag"] = df.apply(flag, axis=1)

    # اختيار أعمدة العرض
    result = df[[
        "name_ar",
        "barcodes",
        "nard_qty",
        "shopify_qty",
        "qty_diff",
        "sale_price",
        "sku_flag"
    ]]

    # فلتر حسب sku_flag
    filter_flag = st.multiselect(
        "Filter by SKU Flag",
        options=result["sku_flag"].dropna().unique(),
        default=result["sku_flag"].dropna().unique()
    )

    filtered = result[result["sku_flag"].isin(filter_flag)]

    st.dataframe(filtered, use_container_width=True)

    # تحميل كـ CSV
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="stock_check.csv",
        mime="text/csv"
    )
else:
    st.info("⬆️ Please upload both CSV files to continue.")
