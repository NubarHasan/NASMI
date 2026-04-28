import streamlit as st

st.set_page_config(page_title="NASMI — Review Queue", page_icon="✋", layout="wide")

st.title("✋ Review Queue")
st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Pending Reviews")
    st.info("No items in review queue.")

    st.divider()
    st.subheader("Review Item")
    st.info("Select an item to review.")

    st.text_area("Reviewer Notes", height=100, disabled=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.button("✅ Approve", disabled=True)
    with col_b:
        st.button("❌ Reject", disabled=True)
    with col_c:
        st.button("🔁 Escalate", disabled=True)

with col_right:
    st.subheader("Queue Summary")
    st.metric("Total Pending", "—")
    st.metric("Approved Today", "—")
    st.metric("Rejected Today", "—")

    st.divider()
    st.subheader("Filters")
    st.selectbox("Priority", ["All", "High", "Medium", "Low"])
    st.multiselect(
        "Document Type",
        ["Passport", "ID Card", "Visa", "Certificate", "Contract", "Other"],
    )
    st.selectbox("Assigned To", ["All", "Me", "Unassigned"])
    st.button("🔍 Apply Filters", disabled=True)

    st.divider()
    st.subheader("Bulk Actions")
    st.button("✅ Approve All", disabled=True)
    st.button("❌ Reject All", disabled=True)
