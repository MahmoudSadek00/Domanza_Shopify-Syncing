import streamlit as st
import pandas as pd

st.title("Domanza – Shopify Stock Sync Checker")

# رفع ملف Products Quantities
pqe_file = st.file_uploader("Upload Products_Quantities_export CSV", type=["csv"], key="pqe")

# رفع ملف Inventory Export
ie_file = st.file_uploader("Upload inventory_export CSV", type=["csv"], key="ie")

if pqe_file and ie_file:
    # قراءة البيانات
    pqe = pd.read_csv(pqe_file)
    ie = pd.read_csv(ie_file)

    # توحيد الأعمدة المطلوبة
    pqe.rename(columns={
        "available_quantity": "nard_qty",
        "barcodes": "SKU"
    }, inplace=True)

    # التأكد من أن العمود بتاع Shopify موجود
    if "Available (not editable)" not in ie.columns:
        st.error("⚠️ The Shopify file must contain a column called: `Available (not editable)`")
    else:
        ie.rename(columns={"Available (not editable)": "shopify_qty"}, inplace=True)

        # فلترة Shopify على لوكيشن دومانزا
        if "Location" in ie.columns:
            ie = ie[ie["Location"] == "Domanza"]

        # merge بناءً على SKU
        merged = pd.merge(pqe, ie, on="SKU", how="left")

        # معالجة الفروقات
        merged["qty_diff"] = merged["nard_qty"] - merged["shopify_qty"].fillna(0)

        def flag_row(row):
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

        merged["sku_flag"] = merged.apply(flag_row, axis=1)

        # عرض النتايج
        st.subheader("Sync Report")
        st.dataframe(merged)

        # تحميل النتايج
        csv_out = merged.to_csv(index=False).encode("utf-8")
        st.download_button("Download Result CSV", csv_out, "sync_report.csv", "text/csv")
