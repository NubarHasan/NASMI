import streamlit as st

st.set_page_config(page_title="NASMI — Export", page_icon="📤", layout="wide")

st.title("📤 Export")
st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Export Data")

    export_type = st.selectbox(
        "Export Type",
        ["Full Profile", "Documents Only", "Entities Only", "Timeline", "Custom"],
    )

    st.multiselect(
        "Include Fields",
        [
            "Personal Info",
            "Documents",
            "Entities",
            "Addresses",
            "Custom Fields",
            "Timeline",
            "Contradictions",
        ],
        default=["Personal Info", "Documents"],
    )

    st.selectbox("Export Format", ["PDF", "JSON", "CSV", "Excel (.xlsx)"])
    st.toggle("Include Confidence Scores", value=True)
    st.toggle("Include Source References", value=True)
    st.toggle("Encrypt Output", value=False)

    st.divider()
    st.button("📤 Export Now", disabled=True)

with col_right:
    st.subheader("Export History")
    st.info("No exports yet.")

    st.divider()
    st.subheader("Scheduled Exports")
    st.toggle("Enable Scheduled Export", value=False)
    st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
    st.time_input("Export Time")
    st.button("💾 Save Schedule", disabled=True)
