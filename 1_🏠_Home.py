import streamlit as st

# ============ DEFINIZIONE SIDEBAR E STRUTTURA PAGINA ===============

st.set_page_config(layout="wide")
st.logo("img/streamlit_logo.png")
st.sidebar.expander("Sidebar", expanded=True)

st.sidebar.title("About")
st.sidebar.info(
    """
    INFO 1
    """
)
st.sidebar.title("Contact")
st.sidebar.info(
    """
    INFO 2
    """
)

st.sidebar.title("Support")
st.sidebar.info(
    """
    INFO 3
    """
)

st.markdown("<h1 style='text-align: center; margin-top: -60px;'>Home Map</h1>", unsafe_allow_html=True)
st.header("Introduzione")

st.write("""Questa Web App multipagina creata con [Streamlit](https://streamlit.io), mostra l'utilizzo di diverse librerie, 
        come [Leafmap](https://leafmap.org), [MapBox](https://www.mapbox.com/) e librerie di Python per l'analisi di dati JSON,
        elaborazioni di immagini e molte altre per garantire il corretto funzionamento della Web App. Nella [GitHub repository](https://github.com/alegue4/Stage) 
        è presente il codice relativo al progetto.
        """)
st.write("""Sono presenti diverse sezioni per l'analisi e la visualizzazione di immagini satellitari con la possibilità
         di usufruire di mappe interattive e statiche. In seguito viene descritta la struttura della Web App con le sezioni più importanti.
        """)

st.header("Sezioni")
st.info("Clicca nella sidebar a sinistra per navigare tra le diverse pagine.")
st.subheader("Interactive Map")
info_col, img_col = st.columns([1, 3])
info_col.write("""In questa sezione è possibile interagire con una mappa disegnando aree geografiche tramite appositi
               strumenti di disegno e salvare i file relativi in formato GeoJSON i quali conterranno le informazioni relative all'area selezionata.
               """)
info_col.write("""Sulla destra è presente uno screenshot della sezione nel quale si può notare che sono state selezionate 5 aree ed è possibile tramite
               un pulsante di Export scaricare il file GeoJSON relativo oppure importare un file contente delle aree selezionate e salvate in precedenza.
               """)
img_col.image("img/interactive_map_img.png", use_column_width=True, caption="Screenshot sezione Interactive Map")
st.subheader("GeoJSON Analysis")
info_col, img_col = st.columns([1, 3])
info_col.write("""In questa sezione è possibile importare un file GeoJSON dal quale verranno estratte le coordinate di Bounding Box.
               Queste verranno usate per ottenere una immagine statica utilizzando l'API di Mapbox. Di questa immagine verranno visualizzate 
               le coordinate dei suoi vertici, le coordinate del centro e la risoluzione spaziale. Grazie all'utilizzo
               di uno Slider è possibile fare il confronto tra l'immagine ottenuta e un layer applicato sopra di essa. 
               """)
info_col.write("""Sulla destra è presente uno screenshot della sezione nel quale si può notare una immagine satellitare con le sue informazioni.
               """)
img_col.image("img/load_file_img.png", use_column_width=True, caption="Screenshot sezione GeoJSON Analysis")


        
        
    