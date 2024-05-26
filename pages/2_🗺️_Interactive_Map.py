import streamlit as st
from streamlit_folium import st_folium
import leafmap.foliumap as leafmap
import folium
from folium.plugins import Draw, Search
import json
from geojson import Feature, FeatureCollection
import time
import io
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def create_map_image(center, zoom, geojson_data):
    lat, lon = center

    # Crea Mappa iniziale con leafmap e il modulo foliumap e aggiunge il basemap SATELLITE
    m = leafmap.Map(
        locate_control=False,
        scale_control=False,
        plugin_LatLngPopup=False,
        center=(lat, lon),
        zoom=zoom,
        draw_control=False,
    )
    m.add_basemap("SATELLITE")
    # Definisci lo stile per le feature GeoJSON
    style = {
        "fillColor": "#3388ff",  # Colore di riempimento blu
        "color": "#3388ff",      # Colore dei bordi blu
        "weight": 2,             # Spessore dei bordi
        "fillOpacity": 0.3       # Opacità di riempimento (30%)
    }
    if geojson_data:
        m.add_geojson(json.loads(geojson_data), style=style)
    # Salvare la mappa in un file HTML temporaneo
    map_path = 'map.html'
    m.save(map_path)

    # Utilizzare selenium per fare uno screenshot della mappa
    options = Options()
    options.add_argument('--headless') # Avvia il browser senza interfaccia grafica
    options.add_argument('--no-sandbox') # Disabilita sandbox del browser 
    options.add_argument('--disable-dev-shm-usage') # Disabilita uso memoria condivisa
    options.add_argument('--disable-gpu') # Disabilita accelerazione scheda video, non necessaria in mod. headless
    options.add_argument('--window-size=800,800') # Dimensione finestra del browser
    options.add_argument('--log-level=3')  # Supprime i log non necessari

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get('file://' + os.path.abspath(map_path))

        # Attendere che la mappa sia completamente caricata
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'leaflet-tile'))
        )

        time.sleep(2)  # Aggiungi una breve pausa per assicurarti che tutte le tile siano caricate
        img_data = driver.get_screenshot_as_png()
    finally:
        driver.quit()

    # Salvare lo screenshot come buffer
    buf = io.BytesIO(img_data)
    buf.seek(0)

    # Rimuovere il file HTML temporaneo
    os.remove(map_path)

    return buf

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
@st.experimental_dialog("Inserisci le informazioni per l'area selezionata")
def set_info_area(last_drawing, m):
    
    name = st.text_input("Inserisci il nome dell'area selezionata")      
    if st.button("Salva Informazioni"):
        last_drawing['properties']['name'] = name
        if 'drawings' not in st.session_state:
            st.session_state.drawings = []
        st.session_state.drawings.append(last_drawing)

        # Calcola i bounds e aggiorna il session state
        st.session_state.bounds = calculate_bounds(st.session_state.drawings)

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
        uploaded_file = st.file_uploader("Carica un file GeoJSON", type=["geojson"], key="file_uploader", help="Cliccare sul pulsante X per togliere il file inserito non cambia la mappa.")

        if uploaded_file is not None:
            # Legge il contenuto del file GeoJSON
            geojson_data = json.load(uploaded_file)
            st.json(geojson_data, expanded=False)
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
                    
                # Calcola i bounds e aggiorna il session state
                st.session_state.bounds = calculate_bounds(st.session_state.drawings)
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

    # Centra la mappa ai limiti delle coordinate
    if 'bounds' in st.session_state:
        m.fit_bounds(st.session_state.bounds)

    # Viene ottenuto il componente streamlit_folium chiamato st_component
    # che servirà per ottenere le diverse informazioni sui disegni/aree
    # selezionate nella mappa
    st_component = st_folium(m, height=600, use_container_width=True)
    st.json(st_component, expanded=False)

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
        
            with download_col:
                # Aggiungi il pulsante per scaricare il file GeoJSON
                st.download_button(
                    label="Export GeoJSON file",
                    data=geojson_str,
                    file_name=file_name,
                    mime="application/geo+json"
                )
            st.json(geojson_str, expanded=False)
    else:
        st.write("""E' possibile scaricare l'immagine della mappa che viene visualizzato al momento a schermo.
        Quindi se ci si sposta o si cambia la zoom verrà ottenuta una immagine diversa.
        """)
        if st.button("Salva informazioni mappa attuale", use_container_width=True):
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
                mime="image/png"
            )
            st.write("**LISTA AREE DISEGNATE**:")
            st.json(geojson_str, expanded=False)
    