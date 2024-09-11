import streamlit as st

def setup_sidebar():
    st.logo("img/streamlit_logo.png")
    # Sidebar
    st.sidebar.title("About")
    st.sidebar.info("""
        INFO 1
        """
    )

    st.sidebar.title("Contact")
    st.sidebar.info("""
        INFO 2
        """
    )

    st.sidebar.title("Support")
    st.sidebar.info("""
        INFO 3
        """
    )