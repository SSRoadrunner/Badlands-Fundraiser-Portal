import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Badlands Fundraiser Portal", layout="wide", page_icon="🍕")

# --- 2. DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/18OsT6-V43pdzXiwVUv9GFoLddyuU9HOMrio717o6gmo/edit?gid=413428396#gid=413428396"

# --- 3. HELPERS: EMAIL VALIDATION & SENDING ---
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def send_confirmation_email(to_email, org_name, order_id, items, grand_total):
    try:
        server = st.secrets["EMAIL_SERVER"]
        port = int(st.secrets["EMAIL_PORT"])
        sender_auth = st.secrets["EMAIL_SENDER"]
        pwd = st.secrets["EMAIL_PASSWORD"]
        
        msg = MIMEMultipart()
        msg['From'] = f"Badlands Pizza Fundraiser <NoReply@ssrr.co>" 
        msg['To'] = to_email
        msg['Subject'] = f"🍕 Order Receipt: {org_name} ({order_id})"
        
        rows = ""
        for i in items:
            rows += f"<tr><td style='padding:8px; border-bottom:1px solid #ddd;'>{i['Seller']}</td><td style='padding:8px; border-bottom:1px solid #ddd;'>{i['Product']}</td><td style='padding:8px; border-bottom:1px solid #ddd; text-align:center;'>{i['Qty']}</td><td style='padding:8px; border-bottom:1px solid #ddd; text-align:right;'>${i['Total']:.2f}</td></tr>"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
                <h2 style="color: #d32f2f; text-align: center;">🍕 Badlands Pizza Fundraiser</h2>
                <p>Hello <strong>{org_name}</strong>,</p>
                <p>Thank you for your submission. Below is a summary of the order we received:</p>
                <div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
                    <strong>Order ID:</strong> {order_id}<br>
                    <strong>Date:</strong> {datetime.now().strftime("%B %d, %Y")}
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #d32f2f; color: white;">
                            <th style="padding: 10px; text-align: left;">Seller</th>
                            <th style="padding: 10px; text-align: left;">Item</th>
                            <th style="padding: 10px; text-align: center;">Qty</th>
                            <th style="padding: 10px; text-align: right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <div style="text-align: right; margin-top: 20px; font-size: 18px;">
                    <strong>Grand Total: <span style="color: #d32f2f;">${grand_total:.2f}</span></strong>
                </div>
                <p style="text-align: right; font-size: 14px; color: #666;">
                    <em>Note: this is not an invoice. Other fees and charges may need to be applied.</em>
                </p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;">
                <p style="font-size: 12px; color: #888; text-align: center;">
                    This is an automated receipt. <strong>Please do not reply to this email.</strong>
                </p>
            </div>
        </body>
        </html>"""
        
        msg.attach(MIMEText(html_body, 'html'))
        smtp = smtplib.SMTP_SSL(server, port, timeout=10)
        smtp.login(sender_auth, pwd)
        smtp.sendmail(sender_auth, [to_email, sender_auth], msg.as_string())
        smtp.quit()
        return True
    except Exception:
        return False

# --- 4. DATA LOADING ---
def get_data():
    try:
        p = conn.read(spreadsheet=SHEET_URL, worksheet="Products", ttl=300)
        return p
    except:
        return pd.DataFrame(columns=["Item Name", "Price"])

product_df = get_data()

if 'current_items' not in st.session_state: st.session_state.current_items = []
if 'active_order_id' not in st.session_state: st.session_state.active_order_id = None

st.title("🍕 Badlands Fundraiser Portal")

# --- 5. STEP 1: CONTACT INFO ---
st.subheader("1. Organization & Contact Info")
c1, c2 = st.columns(2)
c3, c4 = st.columns(2)
with c1: org_name = st.text_input("Organization Name").strip()
with c2: owner_name = st.text_input("Order Contact Person")
with c3: owner_email = st.text_input("Contact Email")
with c4:
    if org_name and st.session_state.active_order_id is None:
        st.session_state.active_order_id = f"ORD-{random.randint(1000, 9999)}"
    order_id = st.text_input("Order ID", value=st.session_state.active_order_id or "Pending...", disabled=True)

st.divider()

# --- 6. STEP 2: ADD SELLERS & ITEMS ---
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
    seller_input = s_col1.text_input("Seller Name")
    item_list = product_df["Item Name"].tolist() if not product_df.empty else ["No Data Found"]
    selected_item = s_col2.selectbox("Select Item", item_list)
    qty = s_col3.number_input("Quantity", min_value=1, step=1)

    btn_col1, btn_col2, buffer = st.columns([1, 1, 2])
    
    if btn_col1.button("➕ Add Item", use_container_width=True, type="primary"):
        if seller_input and org_name:
            price_row = product_df[product_df["Item Name"] == selected_item]
            if not price_row.empty:
                val = float(price_row["Price"].values[0])
                st.session_state.current_items.append({
                    "Order_ID": st.session_state.active_order_id,
                    "Seller": seller_input,
                    "Product": selected_item,
                    "Qty": qty,
                    "Total": val * qty
                })
                st.rerun()
        else:
            st.warning("Please enter an Organization and Seller Name first.")

    if btn_col2.button("🧹 Clear Entire List", use_container_width=True):
        st.session_state.current_items = []
        st.rerun()

# --- 7. STEP 3: REVIEW & SUBMIT ---
if st.session_state.current_items:
    st.divider()
    st.subheader("3. Review Order")
    for idx, item in enumerate(st.session_state.current_items):
        r1, r2, r3, r4, r5 = st.columns([2, 2, 1, 1, 1])
        r1.write(f"**{item['Seller']}**")
        r2.write(item['Product'])
        r3.write(f"Qty: {item['Qty']}")
        r4.write(f"${item['Total']:.2f}")
        if r5.button("🗑️", key=f"del_{idx}"):
            st.session_state.current_items.pop(idx)
            st.rerun()

    gt = sum(i['Total'] for i in st.session_state.current_items)
    st.write(f"### 💰 Grand Total: ${gt:.2f}")
    st.caption("Note: this is not an invoice. Other fees and charges may need to be applied.")
    
    st.markdown("""
        <div style="background-color: #ffeded; padding: 15px; border-radius: 10px; border: 2px solid #ff4b4b; margin-top: 20px;">
            <p style="color: #ff4b4b; font-size: 18px; font-weight: bold; margin-bottom: 0;">
                🚨 ATTENTION: Once you click 'Finalize and Submit', this order is LOCKED and cannot be edited. 
                Please verify all data before proceeding.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    confirm = st.checkbox("I verify that all information is correct.")
    
    if st.button("🚀 Finalize and Submit", type="primary", use_container_width=True, disabled=not confirm):
        if not is_valid_email(owner_email):
            st.error("❌ Please provide a valid email address to receive your receipt.")
        else:
            with st.spinner('🍕 Processing your order, updating records, and sending email...'):
                try:
                    receipt_email = owner_email
                    d_df = pd.DataFrame(st.session_state.current_items)
                    e_d = conn.read(spreadsheet=SHEET_URL, worksheet="Order_Details", ttl=0)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Order_Details", data=pd.concat([e_d, d_df]))
                    
                    l_o = conn.read(spreadsheet=SHEET_URL, worksheet="Orders", ttl=0)
                    n_m = pd.DataFrame([{
                        "Order_ID": st.session_state.active_order_id, 
                        "Organization": org_name, 
                        "Owner_Name": owner_name, 
                        "Owner_Email": owner_email, 
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    conn.update(spreadsheet=SHEET_URL, worksheet="Orders", data=pd.concat([l_o, n_m]))

                    send_confirmation_email(owner_email, org_name, st.session_state.active_order_id, st.session_state.current_items, gt)
                    
                    st.balloons()
                    st.success(f"✅ Order Submitted! A receipt was sent to {receipt_email}.")
                    st.session_state.current_items = []
                    st.session_state.active_order_id = None
                    
                except Exception as e:
                    st.error(f"Error: {e}")
