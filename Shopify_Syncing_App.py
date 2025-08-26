import streamlit as st
import pandas as pd

st.set_page_config(page_title="Domanza Shopify Syncing", layout="wide")
st.title("Domanza Shopify Syncing")

# Hide Streamlit toolbar, header and footer
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

def read_file(f):
    name = str(f.name).lower()
    if name.endswith(".csv"):
        return pd.read_csv(f)
    return pd.read_excel(f)

def find_col(df, keywords):
    cols = list(df.columns)
    for kw in keywords:
        for c in cols:
            if kw in c.lower():
                return c
    return None

pqe_file = st.file_uploader("Upload Products_Quantities_export (CSV/XLSX)", type=["csv", "xlsx"])
ie_file = st.file_uploader("Upload inventory_export (CSV/XLSX)", type=["csv", "xlsx"])

if pqe_file and ie_file:
    pqe = read_file(pqe_file)
    ie = read_file(ie_file)

    pqe.columns = pqe.columns.map(lambda x: str(x).strip())
    ie.columns = ie.columns.map(lambda x: str(x).strip())

    pqe_barcode_col = find_col(pqe, ["barcode", "barcodes", "sku"])
    pqe_name_col = find_col(pqe, ["name_ar", "name", "title"])
    pqe_available_col = find_col(pqe, ["available_quantity", "available qty", "available", "quantity", "qty"])
    pqe_branch_col = find_col(pqe, ["branch_name", "branch"])

    ie_sku_col = find_col(ie, ["sku", "variant sku", "variant barcode", "barcode"])
    ie_location_col = find_col(ie, ["location"])
    # prefer exact 'Available (not editable)' else any column containing 'available' or 'quantity' or 'qty'
    shopify_qty_col = None
    for c in ie.columns:
        if c.strip().lower() == "available (not editable)":
            shopify_qty_col = c
            break
    if shopify_qty_col is None:
        shopify_qty_col = find_col(ie, ["available (not editable)", "available", "quantity", "qty"])

    missing = []
    if pqe_barcode_col is None:
        missing.append("barcode/SKU column in Products_Quantities_export")
    if pqe_available_col is None:
        missing.append("available_quantity column in Products_Quantities_export")
    if ie_sku_col is None:
        missing.append("SKU/Barcode column in inventory_export")
    if shopify_qty_col is None:
        missing.append("Available (or quantity) column in inventory_export")

    if missing:
        st.error("Missing columns: " + ", ".join(missing))
        st.stop()

    # filter PQE to branch Domanza if branch column exists
    pqe_filtered = pqe.copy()
    if pqe_branch_col is not None:
        try:
            pqe_filtered = pqe_filtered[pqe_filtered[pqe_branch_col].astype(str).str.lower() == "domanza"].copy()
        except Exception:
            pass

    # filter inventory to Location = Domanza if location col exists
    ie_filtered = ie.copy()
    if ie_location_col is not None:
        ie_filtered = ie_filtered[ie_filtered[ie_location_col].astype(str).str.lower() == "domanza"].copy()

    # aggregate shopify qty by SKU (sum) to avoid duplicates
    ie_filtered[shopify_qty_col] = pd.to_numeric(ie_filtered[shopify_qty_col], errors="coerce")
    ie_grouped = (
        ie_filtered
        .groupby(ie_sku_col, dropna=False, as_index=False)[shopify_qty_col]
        .sum()
        .rename(columns={ie_sku_col: "SKU", shopify_qty_col: "shopify_qty"})
    )

    # prepare PQE dataframe: ensure nard qty numeric
    pqe_filtered["nard_qty"] = pd.to_numeric(pqe_filtered[pqe_available_col], errors="coerce")

    # merge (left join)
    merged = pd.merge(
        pqe_filtered,
        ie_grouped,
        how="left",
        left_on=pqe_barcode_col,
        right_on="SKU"
    )

    # ensure shopify_qty numeric (NaN where missing)
    merged["shopify_qty"] = pd.to_numeric(merged.get("shopify_qty"), errors="coerce")

    # qty_diff for arithmetic (treat missing as 0 for calculation)
    merged["qty_diff"] = merged["nard_qty"].fillna(0) - merged["shopify_qty"].fillna(0)

    # sku_flag logic (preserve distinction between missing shopify value vs zero)
    def sku_flag(row):
        n = row["nard_qty"]
        s = row["shopify_qty"]
        if pd.notna(n) and pd.isna(s) and n > 0:
            return "not available_in_shopify"
        if pd.notna(n) and pd.isna(s) and (n == 0):
            return "dead_item"
        if pd.notna(s) and (n != s):
            return "mismatched_qty"
        if pd.notna(s) and (n == s):
            return "synced_sku"
        return None

    merged["sku_flag"] = merged.apply(sku_flag, axis=1)

    out_cols = []
    if pqe_name_col:
        out_cols.append(pqe_name_col)
    out_cols += [
        pqe_barcode_col,
        "nard_qty",
        "shopify_qty",
        "qty_diff"
    ]
    if "sale_price" in merged.columns:
        out_cols.append("sale_price")
    elif find_col(pqe, ["sale_price", "price", "sub_total", "total"]):
        out_cols.append(find_col(pqe, ["sale_price", "price", "sub_total", "total"]))
    out_cols.append("sku_flag")

    final = merged.loc[:, [c for c in out_cols if c in merged.columns]]

    st.dataframe(final, use_container_width=True)

    csv = final.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "domanza_shopify_sync.csv", "text/csv")


