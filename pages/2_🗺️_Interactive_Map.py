import streamlit as st
from streamlit_folium import st_folium
import leafmap.foliumap as leafmap
import folium
from folium.plugins import Draw
import json
from geojson import Feature, FeatureCollection
from map_utils import create_map_image

# ============ DICHIARAZIONE E DEFINIZIONE DI FUNZIONI ===============
def initialize_session_state():
    if 'lat' not in st.session_state:
        st.session_state.lat = 45.523840041350965
    if 'lon' not in st.session_state:
        st.session_state.lon = 9.21977690041348
    if 'zoom' not in st.session_state:
        st.session_state.zoom = 17
    if 'drawings' not in st.session_state:
        st.session_state.drawings = []
    if 'bounds_toggle' not in st.session_state:
        st.session_state.bounds_toggle = False
# Funzione per calcolare i bounds di tutte le aree inserite.
# Questa funziona viene chiamata ogni volta che viene aggiunta una nuova area alla
# mappa o quando viene inserito un file tramite il pulsante di import. Questo perchè
# la mappa deve contenere tutte le aree disegnate in modo da farle inizialmente
# vedere tutte all'utente.
def calculate_bounds(drawings):
    all_coords = []
    for drawing in drawings:
        for polygon in drawing['geometry']['coordinates']:
            all_coords.extend(polygon)
    min_lon = min(coord[0] for coord in all_coords)
    max_lon = max(coord[0] for coord in all_coords)
    min_lat = min(coord[1] for coord in all_coords)
    max_lat = max(coord[1] for coord in all_coords)
    return [[min_lat, min_lon], [max_lat, max_lon]]

# Dialog che viene aperto ogni volta in cui viene selezionata un'area geografica
# Serve per inserire informazioni come il nome di un'area geografica.
# Ottine il testo inserito dall'utente e lo assegna alla properties 'name' 
# dell'area selezionata.
# Estrae la latitudine e la longitudine del centro attuale e lo zoom della mappa 
# e li salva nel session state in modo tale che alla chiusura del dialog la mappa 
# rimanga ferma nell'ultima posizione in cui l'utente si è spostato sulla mappa.
@st.experimental_dialog("Inserisci le informazioni per l'area selezionata", )
def set_info_area(last_drawing, st_component):
    name = st.text_input("Inserisci il nome dell'area selezionata")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salva Informazioni"):
            last_drawing['properties']['name'] = name
            update_session_state(last_drawing, st_component)
            st.rerun()
    with col2:
        if st.button("Salva senza Informazioni"):
            update_session_state(last_drawing, st_component)
            st.rerun()

# Funzione per aggiornare lo stato della sessione
def update_session_state(last_drawing, st_component):
    if 'drawings' not in st.session_state:
        st.session_state.drawings = []
    st.session_state.drawings.append(last_drawing)
    
    if st.session_state.bounds_toggle:
        st.session_state.bounds = calculate_bounds(st.session_state.drawings)
    else:
        if 'bounds' in st.session_state:
            del st.session_state['bounds']

    st.session_state.lat = st_component['center']['lat']
    st.session_state.lon = st_component['center']['lng']
    st.session_state.zoom = st_component['zoom']

# ============ DEFINIZIONE SIDEBAR E STRUTTURA PAGINA ===============

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
st.markdown("<h1 style='text-align: center;'>Interactive Map</h1>", unsafe_allow_html=True)

st.header("Introduzione")

st.write("""Questa pagina della Web App permette la visualizzazione di di una mappa interattiva grazie alla libreria
         di **Leafmap** con la possibilità di modificare, disegnare aree e salvare relative informazioni. In seguito sono presentate
         i 3 componenti fondamentali di questa sezione.
        """)
map_col, import_export_col = st.columns(2)
with map_col:
    st.subheader("Mappa")
    st.write("""Sulla mappa interattiva è possibile utilizzare i diversi elementi di disegno e di ricerca forniti dall'interfaccia 
    grafica di **Leafmap**. Gli elementi principali sono:
    """)
    st.write(""" 
    - Elementi ***Draw*** che permettono di disegnare forme geometriche (Rettangoli, Cerchi o Poligoni) 
    e marker sulla mappa. 
    - Elementi per eliminare o cancellare disegni sulla mappa.
    - Elemento ***Show where I am*** per attivare la Geolocalizzazione e ottenere 
    l'area approssimativa
    - Pulsante di ***Ricerca*** per ottenere un luogo o una via precisa.
    """)
with import_export_col:
    st.subheader("Import")
    st.write("""Nella sezione di **Import** è possibile caricare un file GeoJSON precedentemente salvato, in modo tale da visualizzare le
             aree e le relative informazioni all'interno della mappa e eventualmente aggiungere nuove aree. Se vengono aggiunte nuove aree questa
             nuova lista dovrà essere scaricata con il pulsante *Export*
    """)
    st.subheader("Export")
    st.write("""Nella sezione di  **Export** è possibile scaricare il file GeoJSON che rappresenta la lista delle aree disegnate sulla
             mappa interattiva salvando anche le informazioni relative a ciascuna di esse (come nome, ecc.). E' inoltre possibile rinominare
             il nome del file che si andrà a scaricare con il pulsante *Export*.
    """)

# ============ INIZIALIZZAZIONE VALORI UTILI ===============

initialize_session_state()

# ============ CODICE PRINCIPALE DELLA PAGINA ===============

col1, col2 = st.columns([5, 3])

with col1:  
    st.subheader("Mappa")
    # Crea Mappa iniziale con leafmap e il modulo foliumap e aggiunge il
    # basemap SATELLITE
    # Creazione della mappa utilizzando leafmap.foliumap.Map
    m = leafmap.Map(
        locate_control=True, 
        scale_control=True,
        plugin_LatLngPopup=False,
        center=(st.session_state.lat, st.session_state.lon), 
        zoom=st.session_state.zoom,
        draw_control=False,  # Disattiviamo il draw_control
    )
    m.add_basemap("SATELLITE")

    # Creazione di un Draw plugin personalizzato
    draw = Draw(
        draw_options={
            'polyline': False,
            'polygon': True,
            'circle': False,
            'rectangle': True,
            'marker': False,
            'circlemarker': False,
        },
        edit_options={
        'edit': False,
        'remove': False
    }
    )
    draw.add_to(m)

    with col2:
        # Componente di caricamento di un GeoJSON dal quale vengono estratte
        # le feature ovvero le aree selezionate e salvate poi nella lista di aree/disegni
        # da esportare. Utile se l'utente ha salvato in precedenza un file GeoJSON e vuole
        # rivisualizzare le aree disegnate oppure aggiungerne di nuove.
        st.subheader("Import")
        st.write("""Se il file inserito è uguale a quello precedente allora la mappa non viene modificata,
                 in quanto le aree disegnate in precedenza sono già state elaborate.
        """)
        uploaded_file = st.file_uploader("Carica un file GeoJSON", type=["geojson"], 
                                         key="file_uploader", 
                                         help="Cliccare sul pulsante X per togliere il file inserito non cambia la mappa.")

        if uploaded_file is not None:
            # Legge il contenuto del file GeoJSON
            geojson_data = json.load(uploaded_file)
            st.json(geojson_data, expanded=False)
            # Copia il GeoJSON inserito per salvarlo in caso di inserimento di un nuovo GeoJSON
            current_file_content = json.dumps(geojson_data)

            # Se c'è un nuovo file caricato diverso da quello precedente allora la lista di aree dovrà essere
            # cancellata e aggiornata con le aree presenti nel nuovo file caricato.
            if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != current_file_content:
                # Salva il contenuto del nuovo file caricato
                st.session_state.last_uploaded_file = current_file_content
                
                if 'features' not in geojson_data or not geojson_data['features']:
                    st.session_state.drawings = []
                else:
                    # Pulisce le aree precedenti
                    st.session_state.drawings = []
                    # Salva le nuove aree caricate nella lista delle aree disegnate
                    for feature in geojson_data['features']:
                        st.session_state.drawings.append({
                            'type': 'Feature',
                            'geometry': feature['geometry'],
                            'properties': feature['properties']
                        })

                    if st.session_state.bounds_toggle:
                        # Calcola i bounds e aggiorna il session state
                        st.session_state.bounds = calculate_bounds(st.session_state.drawings)
                    else:
                        # Rimuovi i bounds dal session state se il toggle è disattivato
                        if 'bounds' in st.session_state:
                            del st.session_state['bounds']
        else:
            st.session_state.last_uploaded_file = None

    # Questo if consente di avere un pop up quando si passa sopra
    # ad un'area disegnata mostrando il suo nome relativo inserito
    # in alla sua creazione. Per farlo cerca se è presente la lista
    # di aree disegnate nel session state e se la trova estrae il nome
    # dalle properties di ciascuna e lo assegna alla relativa figura in modo tale
    # che sia visibile al momento dell'hover dell'area selezionata 
    if 'drawings' in st.session_state:
        for drawing in st.session_state.drawings:
            if 'properties' in drawing:
                properties = drawing['properties']
                if properties:
                    popup_text = "<br>".join([f"{key}: {value}" for key, value in properties.items()])
                    folium.GeoJson(
                        drawing,
                        tooltip=popup_text  # Usa il testo formattato qui
                    ).add_to(m)
                else:
                    folium.GeoJson(drawing).add_to(m)
            else:
                folium.GeoJson(drawing).add_to(m)

    # Centra la mappa ai limiti delle coordinate
    if 'bounds' in st.session_state:
        m.fit_bounds(st.session_state.bounds)
    else:
        m.set_center(st.session_state.lon, st.session_state.lat, st.session_state.zoom)
    
    # Viene ottenuto il componente streamlit_folium chiamato st_component
    # che servirà per ottenere le diverse informazioni sui disegni/aree
    # selezionate nella mappa
    st_component = st_folium(m, height=600, use_container_width=True)
    # st.json(st_component, expanded=True)

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

    remove_button = st.button("Cancella Aree inserite", disabled=not bool(st.session_state.get('drawings')))
    # Logica per gestire il click sul pulsante
    if remove_button:
        st.session_state.drawings = []
        if 'bounds' in st.session_state:
            del st.session_state['bounds']
        st.session_state.lat = st_component['center']['lat']
        st.session_state.lon = st_component['center']['lng']
        st.session_state.zoom = st_component['zoom']
        st.rerun()


with col2:
    st.session_state.bounds_toggle = st.toggle("Adatta limiti mappa per contenere tutte le aree", value=st.session_state.bounds_toggle)
    
    col_title, col_select = st.columns(2)
    col_title.subheader("Export")
    export_selected = col_select.selectbox("Informazioni relative a", options=["Aree disegnate", "Mappa completa"])
    if(export_selected == "Aree disegnate"):
        st.write("""Quando verranno inserite correttamente delle aree comparirà a sinistra
        l'area per rinominare il file e a destra il pulsante per esportare il relativo GeoJSON.
        Ricordare di premere *Invio* per confermare il nome del file.
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
            default_file_name = "data.geojson" if len(st.session_state.drawings) == 1 else "multi_data.geojson"
            file_name_col, download_col = st.columns(2)
            with file_name_col:
                file_name = st.text_input("Inserisci nome file", placeholder="Inserisci il nome del file", label_visibility="collapsed")
                if not file_name:
                    file_name = default_file_name
                elif not file_name.endswith(".geojson"):
                    file_name += ".geojson"

            st.write("**LISTA AREE DISEGNATE**:")
            st.json(geojson_str, expanded=False)

            with download_col:
                # Aggiungi il pulsante per scaricare il file GeoJSON
                st.download_button(
                    label="Export GeoJSON file",
                    data=geojson_str,
                    file_name=file_name,
                    mime="application/geo+json"
                )
            
    else:
        st.write("""E' possibile scaricare l'immagine della mappa che viene visualizzato al momento a schermo.
        Quindi se ci si sposta o si cambia la zoom verrà ottenuta una immagine diversa.
        """)
        save_image_info_btn = st.button("Salva informazioni mappa attuale", use_container_width=True, disabled=True)
        if save_image_info_btn:
            # Estrai i bounds e lo zoom dall'oggetto st_component
            zoom = st_component['zoom']
            center = st_component['center']
            center_lat = center['lat']
            center_lon = center['lng']
            image_center = [center_lat, center_lon]

            geojson_str = None
            if 'drawings' in st.session_state:
                # Converti i disegni in formato GeoJSON
                features = [Feature(geometry=drawing['geometry'], properties=drawing['properties']) for drawing in st.session_state.drawings]
                feature_collection = FeatureCollection(features)
                geojson_str = json.dumps(feature_collection)
            progress_text = "Ottenendo immagine mappa. Potrebbe richiedere un po' di secondi..."

            with st.spinner(progress_text):
                # Crea l'immagine della mappa
                image_buf = create_map_image(image_center, zoom, geojson_str)
                st.session_state.image_buf = image_buf
            
            # Aggiungi il pulsante per scaricare l'immagine
            st.download_button(
                label="Download Map Image",
                data=st.session_state.image_buf,
                file_name="map_image.png",
                mime="image/png",
                disabled=True
            )
            st.write("**LISTA AREE DISEGNATE**:")
            st.json(geojson_str, expanded=False)
    