# app.py
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px


# PAGE CONFIG

st.set_page_config(layout="wide")
st.title("Real-Time AI Follow-Up & Lead Dashboard")


# MACHINE TYPE DETECTION

def detect_machine_type(text):
    t = str(text).lower()

    if "press" in t:
        return "Hydraulic Press"
    if "pot" in t and "mill" in t:
        return "Pot Mill"
    if "jar" in t and "mill" in t:
        return "Jar Mill or PP Jar"
    if "peristaltic" in t:
        return "Peristaltic Pump"
    if "media" in t:
        return "Grinding Media"
    if "die" in t:
        return "Die Sets"
    if "ss" in t:
        return "Stainless Steel Products"
    if "aluminium" in t or "alumina" in t:
        return "Alumina Products"
    if "autoclave" in t:
        return "Auto Clave"
    if "quartz" in t:
        return "Quartz Products"
    if "furnace" in t:
        return "Furnace"
    if "silicon" in t or "silicone" in t:
        return "Silicon Products"
    if "vacuum" in t:
        return "Vacuum Related Products"
    if "spray" in t and "dryer" in t:
        return "Spray Dryer"

    return "Other"


# REFRESH DATA BUTTON

if st.sidebar.button("🔄 Refresh Data (after sheet update)"):
    st.rerun()


# LOAD GOOGLE SHEET

# LOAD GOOGLE SHEET
def load_sheet():
    credentials = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(credentials)
    sh = gc.open("imp")
    ws = sh.sheet1
    return pd.DataFrame(ws.get_all_records())
    
df = load_sheet()


# CLEAN DATA

df.replace("", pd.NA, inplace=True)

df = df.rename(columns={
    "COMPANY": "company",
    "DATES": "date",
    "DESCRIPTION": "description",
    "QUOTATION NO.":"quotation no.",
    "OUTCOME": "outcome",
    "PLACE": "place",
    "INDUSTRY_TYPE": "industry"
})


df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

today = pd.Timestamp.today()
df["date"] = df["date"].apply(lambda d: d if pd.notna(d) and d <= today else today)

df["days_since"] = (today - df["date"]).dt.days


df["machine_type"] = df["description"].apply(detect_machine_type)

df["outcome_clean"] = df["outcome"].astype(str).str.lower().str.strip()


# KEYWORDS FOR CALL / RESPONSE REMINDERS

CALL_KEYWORDS_REGEX = r"(call|respond|follow|inform|later|week|change|changes)"

# SIDEBAR MENU

page = st.sidebar.selectbox("Menu", [
    "Follow-Up Dashboard",
    "AI Lead Intelligence",
    "Customer Clustering",
    "Assistant",
    "Dataset"
])

# FOLLOW-UP DASHBOARD

if page == "Follow-Up Dashboard":

    st.header("📋 Pending Follow-Ups")

    # FOLLOW-UP WINDOW: 20–30 days only
    followups = df[
        (
            df["outcome"].isna() |
            (df["outcome_clean"] == "") |
            (df["outcome_clean"] == "no response")
        )
        &
        (df["days_since"] > 20)
        &
        (df["days_since"] <= 30)
    ]

    st.metric("Total Follow-Ups Required", followups.shape[0])

    st.dataframe(followups[[
         "quotation no.", "company", "description", "date", "days_since"
    ]])


    # CALL / RESPONSE REMINDERS

    call_reminders = df[
        df["outcome_clean"].str.contains(CALL_KEYWORDS_REGEX, regex=True, na=False)
    ]

    if not call_reminders.empty:
        st.markdown("---")
        st.subheader("📞 Call / Response Reminders")

        for _, row in call_reminders.iterrows():
            st.warning(
                f"🔔 **{row['company']}** - {row['outcome']}"
            )

    if followups.empty and call_reminders.empty:
        st.info("✔ No follow-ups or reminders pending.")

# AI LEAD INTELLIGENCE (RULE-BASED)

elif page == "AI Lead Intelligence":

    st.header("AI Lead Intelligence")

    idx = st.selectbox(
        "Select Lead",
        df.index,
        format_func=lambda i: f"Lead {df.at[i,'lead_id']} - {df.at[i,'company']}"
    )

    lead = df.loc[idx]
    days = lead["days_since"]
    outcome = lead["outcome_clean"]

    if outcome == "bought":
        prediction = "Customer has already bought the product!"
        score = 95
        color = "success"
    else:
        if days < 7:
            prediction = "High chance, no follow-up needed."
            score = 80
            color = "success"
        elif days < 20:
            prediction = "Medium chance, monitor closely."
            score = 55
            color = "info"
        elif days <= 35:
            prediction = "Low chance — follow-up recommended."
            score = 40
            color = "warning"
        else:
            prediction = "Very low chance — customer likely inactive."
            score = 25
            color = "error"

    st.subheader("AI Assessment Result")

    if color == "success":
        st.success(prediction)
    elif color == "info":
        st.info(f"{prediction} ({score}%)")
    elif color == "warning":
        st.warning(f"{prediction} ({score}%)")
    else:
        st.error(f"{prediction} ({score}%)")

    st.markdown("---")
    st.write(f"Quotation No:{lead['quotation no.']}")
    st.write(f"**Company:** {lead['company']}")
    st.write(f"**Description:** {lead['description']}")
    st.write(f"**Days Since Quotation:** {days}")
    st.write(f"**Outcome:** {lead['outcome'] if pd.notna(lead['outcome']) else 'No Response'}")
    


# CUSTOMER CLUSTERING

elif page == "Customer Clustering":

    st.header("Customer Clustering Based on Product Enquiry")

    product_counts = df["machine_type"].value_counts()

    st.plotly_chart(px.bar(
        product_counts,
        title="Enquiry Count per Product Type",
        labels={"value": "Number of Enquiries", "index": "Machine Type"}
    ))


# ASSISTANT

elif page == "Assistant":

    st.header("Message Generator")

    idx = st.selectbox(
        "Select Lead",
        df.index,
        format_func=lambda i: f"Lead {df.at[i,'lead_id']} — {df.at[i,'company']}"
    )

    lead = df.loc[idx]
    company = lead["company"]
    desc = lead["description"]
    date = lead["date"]

    tone = st.selectbox("Message Tone", [
        "Polite Reminder",
        "Urgent Follow-Up",
        "Friendly Check-In"
    ])

    if tone == "Polite Reminder":
        msg = f"Hello {company},\n\nThis is a gentle reminder regarding your quotation request for {desc} dated {date.date()}.\n\nRegards,\nMetwiz Sales"
    elif tone == "Urgent Follow-Up":
        msg = f"Hello {company},\n\nWe are following up on your quotation for {desc}. Kindly update us.\n\nRegards,\nMetwiz Sales"
    else:
        msg = f"Hi {company},\n\nJust checking in regarding your enquiry for {desc}.\n\nThanks,\nMetwiz"

    st.text_area("Generated Message", msg, height=180)

# DATASET VIEW

else:
    st.header("Live Dataset")
    st.dataframe(df)





