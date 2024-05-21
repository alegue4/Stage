import streamlit as st
from streamlit_folium import st_folium
import leafmap.foliumap as leafmap
import folium
import json
from geojson import Feature, FeatureCollection

# Dialog che viene aperto ogni volta in cui viene selezionata un'area geografica
# Serve per inserire informazioni come il nome di un'area geografica.
# Ottine il testo inserito dall'utente e lo assegna alla properties 'name' 
# dell'area selezionata.
# Estrae la latitudine e la longitudine del centro attuale e lo zoom della mappa 
# e li salva nel session state in modo tale che alla chiusura del dialog la mappa 
# rimanga ferma nell'ultima posizione in cui l'utente si è spostato sulla mappa.
@st.experimental_dialog("Inserisci le informazioni per l'area selezionata")
def set_info_area(last_drawing, m):
    
    name = st.text_input("Inserisci il nome dell'area selezionata")      
    if st.button("Salva Informazioni"):
        last_drawing['properties']['name'] = name
        if 'drawings' not in st.session_state:
            st.session_state.drawings = []
        st.session_state.drawings.append(last_drawing)

        center_lat = m['center']['lat']
        center_lng = m['center']['lng']
        zoom = m['zoom']
        st.session_state.lat = center_lat
        st.session_state.lon = center_lng
        st.session_state.zoom = zoom
        st.rerun()
        
st.set_page_config(layout="wide")
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


# Title
st.markdown("<h1 style='text-align: center;'>Home Page</p>", unsafe_allow_html=True)
st.subheader("Introduzione")

st.write("""Questa Web App multipagina creata con [Streamlit](https://streamlit.io), mostra l'utilizzo di diverse librarie, 
        come [Leafmap](https://leafmap.org), [Geemap](https://geemap.org), [MapBox](https://www.mapbox.com/).
        Come riferimento viene utilizzata la [GitHub repository](https://github.com/giswqs/streamlit-geospatial).
        """)
st.write("""Sono presenti diverse sezioni per l'analisi e la visualizzazione di immagini satellitari con la possibilità
         di usufruire di mappe interattive e statiche. 
        """)

st.info("Clicca nella sidebar a sinistra per navigare tra le diverse pagine.")

st.subheader("Informazioni")
st.write("""In questa sezione della Web App è presente una mappa interattiva nella quale
è possibile utilizzare i diversi elementi di disegno e di ricerca forniti dall'interfaccia 
grafica di **Leafmap**. Gli elementi principali sono:
""")
st.write(""" 
- Elementi ***Draw*** che permettono di disegnare forme geometriche (Rettangoli, Cerchi o Poligoni) 
e marker sulla mappa. 
- Elementi per eliminare o cancellare disegni sulla mappa.
- Elemento ***Show where I am*** per attivare la Geolocalizzazione e ottenere 
l'area approssimativa
- Pulsante di ***Ricerca*** per ottenere un luogo o una via precisa.
- Pulsante ***Export*** per scaricare il file GeoJSON relativo alla collezione di elementi
disegnati sulla mappa.
""")

# Quelle sotto sono le coordinate del dipartimento di informatica U14
lat =  45.523840041350965
lon = 9.21977690041348
zoom = 17
# Imposta le coordinate iniziali e lo zoom se non sono già salvati
# salvandoli successivamente nel session state
if 'lat' not in st.session_state or 'lon' not in st.session_state:
    st.session_state.lat = lat  # coordinate iniziali
    st.session_state.lon = lon  # coordinate iniziali
if 'zoom' not in st.session_state:
    st.session_state.zoom = zoom  # zoom iniziale 
    
col1, col2 = st.columns([5, 3])

with col1:  
    st.subheader("Mappa")

    # Crea Mappa iniziale con leafmap e il modulo foliumap e aggiunge il
    # basemap SATELLITE
    m = leafmap.Map(locate_control=True, 
                    plugin_LatLngPopup=False,
                    edit_options={"edit": False, "remove": False},
                    center=(st.session_state.lat, st.session_state.lon), 
                    zoom = st.session_state.zoom)
    
    m.add_basemap("SATELLITE") 

    with col2:
        # Componente di caricamento di un GeoJSON dal quale vengono estratte
        # le feature ovvero le aree selezionate e salvate poi nella lista di aree/disegni
        # da esportare. Utile se l'utente ha salvato in precedenza un file GeoJSON e vuole
        # rivisualizzare le aree disegnate oppure aggiungerne di nuove.
        st.subheader("Import")
        uploaded_file = st.file_uploader("Carica un file GeoJSON", type=["geojson"], key="file_uploader")

        if uploaded_file is not None:
            # Legge il contenuto del file GeoJSON
            geojson_data = json.load(uploaded_file)
            # Copia il GeoJSON inserito per salvarlo in caso di inserimento di un nuovo GeoJSOn
            current_file_content = json.dumps(geojson_data)

            # Se c'è un nuovo file caricato diverso da quello precedente allora la lista di aree dovrà essere
            # cancellata e aggiornata con le aree presenti nel nuovo file caricato.
            if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != current_file_content:
                # Salva il contenuto del nuovo file caricato
                st.session_state.last_uploaded_file = current_file_content
                # Pulisce le aree precedenti
                st.session_state.drawings = []
                # Salva le nuove aree caricate nella lista delle aree disegnate
                for feature in geojson_data['features']:
                    st.session_state.drawings.append({
                        'type': 'Feature',
                        'geometry': feature['geometry'],
                        'properties': feature['properties']
                    })
        else:
            st.session_state.last_uploaded_file = None

    # Questo if consente di avere un pop up quando si passa sopra
    # ad un'area disegnata mostrando il suo nome relativo inserito
    # in alla sua creazione. Per farlo cerca se è presente la lista
    # di aree disegnate nel session state e se lo trova estrae il nome
    # dalle properties e lo assegna alla relativa figura in modo tale
    # che questo sia visibile al momento dell'hover dell'area selezionata 
    if 'drawings' in st.session_state:
        for drawing in st.session_state.drawings:
            area_name = drawing['properties']['name']
            tooltip_text = f"Nome: {area_name}"
            folium.GeoJson(
                drawing,
                tooltip=tooltip_text  # Usa il testo formattato qui
            ).add_to(m)

    # Viene ottenuto il componente streamlit_folium chiamato st_component
    # che servirà per ottenere le diverse informazioni sui disegni/aree
    # selezionate nella mappa
    st_component = st_folium(m, height=600, use_container_width=True)
    #st.json(st_component)

    # Questo if ottiene l'ultimo disegno/area selezionata nella mappa
    # interrativa. Se non esiste ancora un'area selezionata o se è già
    # stata inserita nella lista finale allora non deve fare operazioni,
    # altrimenti viene aperto un experimental dialog nel quale vengono
    # inserite diverse informazioni come nome, ecc...
    if st_component.get('last_active_drawing') is not None:
        last_drawing = st_component['last_active_drawing']
        # Controlla se il disegno corrente è già stato salvato
        if 'drawings' in st.session_state:
            existing_drawings = [d['geometry'] for d in st.session_state.drawings]
        else:
            existing_drawings = []

        if last_drawing['geometry'] not in existing_drawings:
            set_info_area(last_drawing, st_component)
    
            

with col2:
    st.divider()
    st.subheader("Export")
    st.write("""Dopo aver selezionato una o piu' aree grazie agli strumenti di disegno
            forniti dalla libreria di **Leafmap** comprarirà un pulsante per esportare il file
            GeoJSON contente le informazioni relative alle aree selezionate. Se l'area selezionata è una 
            allora verrà scaricato un file chiamato *data.geojson*, mentre se le aree selezionate sono più
            di una allora il file sarà chiamato *multi_data.geojson*.
    """)
    st.write("""Dopo aver selezionato un'area verrà aperto un **Dialog** per inserire un nome o ulteriori
             informazioni relativa all'area che verranno salvate tramite il pulsante *"Salva Informazioni"*.
             Nel caso in cui si dovessero salvare delle informazioni, anche se vuote, queste non potranno essere più
             modificate, mentre se si dovesse uscire dal Dialog tramite il suo pulsante di chiusura facendo un click
             sull'area selezionata sarà possibile ricompilare il Dialog.
    """)
    

    # Questo if controlla se è presente una lista di disegni/aree selezionate e
    # dopo averli convertiti in un formato GeoJSON adeguato è possibile scaricare
    # il file contenente tutte le informazioni.
    if 'drawings' in st.session_state:
        # Converti i disegni in formato GeoJSON
        features = [Feature(geometry=drawing['geometry'], properties=drawing['properties']) for drawing in st.session_state.drawings]
        feature_collection = FeatureCollection(features)
        geojson_str = json.dumps(feature_collection)

        # Determina il nome del file in base alla lunghezza della lista dei disegni
        file_name = "data.geojson" if len(st.session_state.drawings) == 1 else "multi_data.geojson"

        # Aggiungi il pulsante per scaricare il file GeoJSON
        st.download_button(
            label="Export GeoJSON file",
            data=geojson_str,
            file_name=file_name,
            mime="application/geo+json"
        )
        st.write("**LISTA AREE DISEGNATE**:")
        st.json(st.session_state.drawings, expanded=False)
        
    