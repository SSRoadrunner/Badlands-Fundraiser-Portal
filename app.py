import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="Badlands Fundraiser Portal", 
    layout="wide", 
    page_icon="🍕"
)

# --- 2. DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 🛑 PASTE YOUR FULL URL HERE 🛑
SHEET_URL = "https://docs.google.com/spreadsheets/d/18OsT6-V43pdzXiwVUv9GFoLddyuU9HOMrio717o6gmo/edit?gid=413428396#gid=413428396"

# --- 3. DATA LOADING & SESSION STATE ---
def get_data():
    """Fetches data with a safety net to prevent the app from cutting off."""
    try:
        products = conn.read(spreadsheet=SHEET_URL, worksheet="Products", ttl=0)
        orders = conn.read(spreadsheet=SHEET_URL, worksheet="Orders", ttl=0)
        return products, orders
    except Exception as e:
        # This keeps the app running even if the sheet fails
        return pd.DataFrame(columns=["Item Name", "Price"]), pd.DataFrame()

product_df, orders_db = get_data()

if 'current_items' not in st.session_state:
    st.session_state.current_items = []

if 'active_order_id' not in st.session_state:
    st.session_state.active_order_id = None

st.title("🍕 Badlands Fundraiser Portal")

# --- 4. STEP 1: ORGANIZATION & CONTACT INFO ---
st.subheader("1. Organization & Contact Info")
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

with col1:
    org_name = st.text_input("Organization Name (e.g., Badlands Elementary)").strip()

with col2:
    owner_name = st.text_input("Order Contact Person")

with col3:
    owner_email = st.text_input("Contact Email")

with col4:
    if org_name:
        if st.session_state.active_order_id is None:
            if not orders_db.empty and 'Organization' in orders_db.columns:
                org_column = orders_db['Organization'].fillna('').astype(str)
                mask = org_column.str.lower() == org_name.lower()
                
                if mask.any():
                    st.session_state.active_order_id = str(orders_db[mask]['Order_ID'].values[0])
                else:
                    st.session_state.active_order_id = f"ORD-{random.randint(1000, 9999)}"
            else:
                st.session_state.active_order_id = f"ORD-{random.randint(1000, 9999)}"
        
        order_id = st.text_input("Order ID", value=st.session_state.active_order_id, disabled=True)
    else:
        st.session_state.active_order_id = None
        order_id = st.text_input("Order ID", value="Pending Org Name...", disabled=True)

st.divider()

# --- 5. STEP 2: ADD SELLERS & ITEMS ---
st.subheader("2. Add Sellers & Items")

st.info("""
**Instructions:**
1. Add a **Seller Name**, select **Item** and **Quantity**, then click **Add Item**.
2. To add a **different item** for the same seller, select the new item from the dropdown, update the quantity, and click **Add Item**.
3. To add a **different seller**, change the name in the Seller field, select their item/quantity, and click **Add Item**.
4. Continue until all sellers and items have been entered.
""")

with st.container(border=True):
    s_col1, s_col2, s_col3 = st.columns([2, 2, 1])
    
    with s_col1:
        seller = st.text_input("Seller Name")
    
    with s_col2:
        # If the sheet is empty or failing, we show a default message
        if product_df.empty or "Item Name" not in product_df.columns:
            st.error("⚠️ Connection Issue: 'Item Name' column not found in Google Sheet!")
            item_list = ["Error: Check Sheet"]
        else:
            item_list = product_df["Item Name"].tolist()
        
        selected_item = st.selectbox("Select Item", item_list)
    
    with s_col3:
        qty = st.number_input("Quantity", min_value=1, step=1)

    btn_col1, btn_col2 = st.columns([1, 4])
    with btn_col1:
        if st.button("➕ Add Item", use_container_width=True):
            if seller and org_name and not product_df.empty:
                try:
                    unit_price = product_df.loc[product_df["Item Name"] == selected_item, "Price"].values[0]
                    st.session_state.current_items.append({
                        "Order_ID": st.session_state.active_order_id,
                        "Organization": org_name,
                        "Seller": seller,
                        "Product": selected_item,
                        "Qty": qty,
                        "Total": float(unit_price * qty)
                    })
                except:
                    st.error("Could not find price for this item.")
            else:
                st.warning("Please ensure Org Name and Seller Name are filled.")
    
    with btn_col2:
        if st.button("🗑️ Clear Entire List", type="secondary"):
            st.session_state.current_items = []
            st.session_state.active_order_id = None
            st.rerun()

# --- 6. STEP 3: REVIEW & FINAL SUBMISSION ---
if st.session_state.current_items:
    st.divider()
    st.write("### Current Order Summary")
    
    grand_total = sum(entry['Total'] for entry in st.session_state.current_items)
    
    for index, entry in enumerate(st.session_state.current_items):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
        c1.write(f"**Seller:** {entry['Seller']}")
        c2.write(f"**Item:** {entry['Product']}")
        c3.write(f"**Qty:** {entry['Qty']}")
        c4.write(f"**Total:** ${entry['Total']:.2f}")
        if c5.button("🗑️", key=f"delete_{index}"):
            st.session_state.current_items.pop(index)
            st.rerun()

    st.write(f"### 💰 Grand Total: ${grand_total:.2f}")

    st.markdown(
        """
        <div style="background-color: #ffeded; padding: 15px; border-radius: 10px; border: 2px solid #ff4b4b; margin-top: 20px;">
            <p style="color: #ff4b4b; font-size: 18px; font-weight: bold; margin-bottom: 0;">
                🚨 ATTENTION: Once you click 'Finalize and Submit', this order is LOCKED. 
                You will not be able to edit or delete these items from this portal after submission. 
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.write("") 
    confirm_submit = st.checkbox("I verify that the information is correct and cannot be changed.")

    if st.button("🚀 Finalize and Submit", type="primary", use_container_width=True, disabled=not confirm_submit):
        # Final Upload
        try:
            details_df = pd.DataFrame(st.session_state.current_items)
            # Fetch existing to append
            existing_details = conn.read(spreadsheet=SHEET_URL, worksheet="Order_Details", ttl=0)
            conn.update(spreadsheet=SHEET_URL, worksheet="Order_Details", data=pd.concat([existing_details, details_df]))
            
            # Update Orders Master
            latest_orders = conn.read(spreadsheet=SHEET_URL, worksheet="Orders", ttl=0)
            if org_name.lower() not in latest_orders['Organization'].fillna('').astype(str).str.lower().values:
                new_master = pd.DataFrame([{
                    "Order_ID": st.session_state.active_order_id,
                    "Organization": org_name,
                    "Owner_Name": owner_name,
                    "Owner_Email": owner_email,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                conn.update(spreadsheet=SHEET_URL, worksheet="Orders", data=pd.concat([latest_orders, new_master]))

            st.success("Order Submitted Successfully!")
            st.session_state.current_items = [] 
            st.session_state.active_order_id = None
            st.balloons()
        except Exception as e:
            st.error(f"Upload failed: {e}")