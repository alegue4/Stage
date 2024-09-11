import streamlit as st
import base64

# Metodo per convertire immagine in una stringa base64 utilizzabile
# in un codice html
def load_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()
    
def setup_sidebar():
    st.sidebar.expander("Sidebar", expanded=True)
    st.logo("img/streamlit_logo.png")
    # Sidebar
    with st.sidebar:
        st.title("About")
        github_img = load_image("img/github_logo.png")
        # GitHub
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <img src="data:image/png;base64,{github_img}" style="width:30px; margin-right: 10px;">
                <a href="https://github.com/alegue4/Stage" target="_blank">Github Repository</a>
            </div>
            """,
            unsafe_allow_html=True
        )   