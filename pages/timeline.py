import streamlit as st

st.set_page_config(page_title="NASMI — Timeline", page_icon="📅", layout="wide")

st.title("📅 Timeline")
st.divider()

col_left, col_right = st.columns([3, 1])

with col_left:
    st.subheader("Document & Event Timeline")
    st.info("No timeline events yet.")

    st.divider()
    st.subheader("Upcoming Expirations")
    st.info("No upcoming expirations.")

with col_right:
    st.subheader("Filters")
    st.multiselect(
        "Event Type",
        [
            "Document Issued",
            "Document Expired",
            "Document Uploaded",
            "Field Updated",
            "Review Completed",
        ],
    )
    st.date_input("From")
    st.date_input("To")
    st.button("🔍 Apply Filters", disabled=True)

    st.divider()
    st.subheader("Add Manual Event")
    st.text_input("Event Title")
    st.date_input("Event Date")
    st.text_area("Notes", height=80)
    st.button("➕ Add Event", disabled=True)
