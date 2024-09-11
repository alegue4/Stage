import streamlit as st
from utils import setup_sidebar

# ============ DEFINIZIONE SIDEBAR E STRUTTURA PAGINA ===============

st.set_page_config(layout="wide")
setup_sidebar()

st.markdown("<h1 style='text-align: center; margin-top: -60px;'>Home Page</h1>", unsafe_allow_html=True)
st.header("Introduzione")

st.write("""Questa Web App realizzata con [Streamlit](https://streamlit.io) fornisce strumenti per interagire con mappe interattive, per l'analisi di dati geospaziali
        e per la visualizzazione e l'elaborazione di immagini satellitari. Vengono sfruttate diverse tecnologie come librerie Python o API. Le principali librerie sono [Leafmap](https://leafmap.org) e [Streamlit-Folium](https://folium.streamlit.app/) mentre l'API 
        che viene utilizzata viene fornita da [MapBox](https://www.mapbox.com/).
        """)

st.write("""
Sono presenti due sezioni principali chiamate **Interactive Map** e **GeoJSON Analysis** che vengono spiegate in seguito assieme alle loro funzionalità.
Nella sidebar a sinistra sarà possibile navigare tra le diverse pagine e visualizzare le informazioni relative al progetto e ai contatti.
""")

st.subheader("Interactive Map")
info_col, img_col = st.columns([1, 3])
info_col.write("""In questa sezione è possibile interagire con una mappa interattiva offrendo diverse funzionalità per l'analisi di dati geospaziali.
               Le funzionalità principali presenti in questa pagina comprendono:
               """)
info_col.write("""
               - Un'interfaccia di disegno per inserire aree geografiche sulla mappa con la possibilità di assegnare ad esse nomi specifici.
               - Sezione per esportare le aree disegnate attraverso un file in formato *GeoJSON* ([info qui](https://www.ibm.com/docs/en/db2/11.5?topic=formats-geojson-format))
               - Sezione per importare un file nel medesimo formato per la visualizzazione sulla mappa delle aree presenti.
                """)

img_col.image("img/interactive_map_img.png", use_column_width=True, caption="Screenshot sezione Interactive Map")
st.subheader("GeoJSON Analysis")
info_col, img_col = st.columns([1, 3])
info_col.write("""In questa sezione è possibile importare un file GeoJSON contenente aree geografiche e visualizzare i dati geospaziali relativi ad esso. 
               Avvenuto l'inserimento del file saranno presenti due principali sezioni chiamate **Info Aggiuntive** e **Immagine Satellitare**, nelle quali 
               verranno mostrati i dati come coordinate, risoluzione spaziale, CRS (Coordinate Reference System) e immagine satellitare. Queste informazioni
               sono relative all'area che contiene tutte le aree che vengono analizzate grazie al file GeoJSON. Per l'analisi e la visualizzazione a schermo
               vengono usate librerie di Python e l'API fornita da MapBox per ottenere un immagine statica ([Documentazione Static Images API](https://docs.mapbox.com/api/maps/static-images/)
               """)
img_col.image("img/geojson_analysis.png", use_column_width=True, caption="Screenshot sezione GeoJSON Analysis")


        
        
    