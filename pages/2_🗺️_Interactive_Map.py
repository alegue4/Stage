import streamlit as st
from streamlit_folium import st_folium
import leafmap.foliumap as leafmap
import folium
from folium.plugins import Draw
import json
from geojson import Feature, FeatureCollection
from utils import setup_sidebar

# ============ DICHIARAZIONE E DEFINIZIONE DI FUNZIONI ===============

# Funzione che viene chiamata all'inizio del corpo principale del codice 
# per inizializzare i valori iniziali come latitudine e longitudine (coordinate
# U14 Milano Bicocca), livello di zoom mappa, lista di aree/disegni e stato del
# toggle nelle opzioni mappa
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
    if 'feature_clicked_list' not in st.session_state:
        st.session_state.feature_clicked_list = []
    if 'options' not in st.session_state:
        st.session_state.options = ["Acqua", "Campo Agricolo", "Edificio", "Strada", "Vegetazione"]
    if 'last_name_selected' not in st.session_state:
        st.session_state.last_name_selected = "Acqua"

# Funzione per creare mappa con il modulo foliumap di leafmap sulla quale
# viene applicato il basemap satellite e l'interfaccia di disegno per 
# poter interagire sopra di essa
def create_map():
    # Crea Mappa iniziale con leafmap e il modulo foliumap e aggiunge il
    # basemap SATELLITE
    # Creazione della mappa utilizzando leafmap.foliumap.Map
    m = leafmap.Map(
        locate_control=True, 
        scale_control=True,
        # fullscreen_control=False,
        # minimap_control = True,
        google_map = "SATELLITE",
        layers_control = True,
        plugin_LatLngPopup=False,
        center=(st.session_state.lat, st.session_state.lon), 
        zoom=st.session_state.zoom,
        draw_control=False,  # Disattiviamo il draw_control
    )

    # L'aggiunta del wms layer per ora non funziona, non ho capito bene 
    wms_url = 'https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php?language=ita'

    # Aggiungi il layer WMS
    #m.add_wms_layer(
        #url=wms_url,
        #layers='CP.CadastralZoning',
        #name='Catasto',
        #attribution='Cartografia dell\'Agenzia delle Entrate',
        #format='image/png',
        #transparent=True,
        #opacity=1.0,
        #shown=True
    #)

    # Aggiunta del LayerControl tramite folium
    # folium.LayerControl().add_to(m)

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

    return m

# Metodo che permette l'aggiunta dei geojson alla mappa in modo che questi siano
# visibili e con annessi il tooltip relativo alle proprie informazioni. Serve inoltre
# per cambiare il colore dell'area quando questa viene selezionata/deselezionata.
# Per aggiungere i geojson alla mappa scorre la lista dei disegni inseriti ed estrae
# le loro proprietà assegnando il colore se sono selezionate o meno.
def add_geojson_to_map(drawings, m):
    for drawing in drawings:
        # Verifica se il disegno ha la proprietà 'properties'
        if 'properties' in drawing:
            properties = drawing['properties']
            if properties:
                popup_text = "<br>".join([f"{key}: {value}" for key, value in properties.items()])
                # Se il disegno corrente è uguale alla feature cliccata, lo colora di rosso
                if st.session_state.feature_clicked_list != [] and drawing in st.session_state.feature_clicked_list:
                    folium.GeoJson(
                        drawing,
                        tooltip=popup_text,
                        style_function=lambda x: {
                            'fillColor': 'red',
                            'color': 'red',
                            'weight': 2
                            }
                    ).add_to(m)
                else:
                    folium.GeoJson(
                        drawing,
                        tooltip=popup_text
                    ).add_to(m)
            else:
                folium.GeoJson(drawing).add_to(m)
        else:
            folium.GeoJson(drawing).add_to(m)

# Funzione per calcolare i bounds di tutte le aree inserite.
# Questa funziona viene chiamata ogni volta che viene aggiunta una nuova area alla
# mappa o quando viene inserito un file tramite il pulsante di import. Questo perchè
# la mappa deve contenere tutte le aree disegnate in modo da farle inizialmente
# vedere tutte all'utente.
@st.cache_data
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
def set_info_area(last_drawing, st_component):
    last_name_selected = st.session_state.last_name_selected
    for index, option in enumerate(st.session_state.options):
        if option== last_name_selected:
            index_selected = index
            break
    name = st.selectbox("Seleziona nome area selezionata", 
                        options=st.session_state.options, 
                        index=index_selected,
                        placeholder="Seleziona un'opzione")
    name_selected = st.text_input("Text input per nome area", label_visibility='collapsed', 
                                  placeholder="Inserisci manualmente il nome dell'area selezionata").strip()
    if st.button("Salva Informazioni"):
        if name_selected:
            st.session_state.last_name_selected = name_selected
            name = name_selected
            if name_selected not in st.session_state.options:
                st.session_state.options.append(name_selected)
                st.session_state.options = sorted([opt.strip() for opt in st.session_state.options])
        else:
            st.session_state.last_name_selected = name
        last_drawing['properties']['name'] = name.lower()
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
        
# Funzione che legge e analizza il contenuto del file GeoJSON 
# importato all'interno del file uploader
def read_imported_geojson(uploaded_file):
    try:
        # Legge il contenuto del file GeoJSON
        geojson_data = json.load(uploaded_file)
        # st.write(geojson_data)
        
        # Verifica se il file GeoJSON contiene delle features
        if 'features' not in geojson_data or not geojson_data['features']:
            st.error("Il file GeoJSON caricato non contiene aree selezionate (features). Per favore carica un file valido.")
            st.session_state.drawings = []
        else:
            # Converte il geojson, passato come input, in una stringa
            current_file_content = json.dumps(geojson_data)
            # st.write(current_file_content)

            # Converte la lista drawings in formato GeoJSON e lo converte in una stringa
            # per confrontarlo con il file di input
            features = [Feature(geometry=drawing['geometry'], properties=drawing['properties']) for drawing in st.session_state.drawings]
            feature_collection = FeatureCollection(features)
            geojson_str = json.dumps(feature_collection)

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
                
    except json.JSONDecodeError:
        st.error("Errore nella lettura del file GeoJSON. Assicurati che il file sia in un formato valido.")
        st.session_state.drawings = []

# Funzione avente 2 parametri, le coordinate del punto cliccato all'interno
# di un'area presente sulla mappa, e la lista completa di disegni.
# Basandosi sul metodo is_inside_polygon scorre tutta la lista per trovare 
# la feature esatta e la ritorna al chiamante
def find_feature(last_object_clicked, drawings):
    lat = last_object_clicked['lat']
    lng = last_object_clicked['lng']
    
    for feature in drawings:
        coordinates = feature['geometry']['coordinates'][0]  # Per estrarre coordinate del poligono
        if is_inside_polygon(lat, lng, coordinates):
            return feature

    return None

# Funzione che ha come parametri latitudine e longitudine del punto cliccato,
# le quali vengono confrontate con le coordinate dei vertici del poligono 
# per vedere se queste sono presenti al suo interno. Se sì significa che il punto
# cliccato è corrispondente alla feature. Viene utilizzato l'algoritmo di Ray Casting
def is_inside_polygon(lat, lng, coordinates):
    # Utilizza l'algoritmo di Ray Casting per verificare se le coordinate sono all'interno del poligono
    num_vertices = len(coordinates)
    is_inside = False
    j = num_vertices - 1

    for i in range(num_vertices):
        xi, yi = coordinates[i]
        xj, yj = coordinates[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            is_inside = not is_inside
        j = i

    return is_inside

# Funzione che rimuove dalla lista totale di disegni importati o inseriti
# tutti quelli che l'utente seleziona. Visibili a schermo perchè cambiano colore
def remove_areas(drawings):
    # Viene creata una nuova lista che conterrà solo i disegni non selezionati
    updated_drawings = [feature for feature in drawings if feature not in st.session_state.feature_clicked_list]
    return updated_drawings

# Funzione che rimuove dalla lista tutti i disegni con la tipologia 
# specificata, sia che l'insieme di tipologie sia singolo che multiplo.
def remove_areas_by_name(drawings, selected_names):
    filtered_drawings = [feature for feature in drawings if feature['properties']['name'] not in selected_names]
    return filtered_drawings

# Funzione che serve per salvare lo stato attuale della mappa e fare un rerun per
# aggiornare il contenuto. Questo metodo viene utilizzato quando vengono cancellate aree
# dalla mappa e quindi bisogna fare un rerun per mostrare la mappa nuovamente senza 
# le aree eliminate. Grazie a questo metodo serve per non spostare la mappa se si 
# interagisce con essa.
def save_map_state_and_rerun(st_component):
    if 'bounds' in st.session_state:
        del st.session_state['bounds']
    st.session_state.lat = st_component['center']['lat']
    st.session_state.lon = st_component['center']['lng']
    st.session_state.zoom = st_component['zoom']
    st.rerun()

# ============ DEFINIZIONE SIDEBAR E STRUTTURA PAGINA ===============

st.set_page_config(layout="wide")
setup_sidebar()

st.markdown("<h1 style='text-align: center; margin-top: -60px;'>Interactive Map</h1>", unsafe_allow_html=True)

# ============ INIZIALIZZAZIONE VALORI UTILI ===============

# Funzione per inizializzare valori iniziali come latitudine,
# longitudine, zoom mappa, etc...
initialize_session_state()

# ============ CODICE PRINCIPALE DELLA PAGINA ===============

with st.container(border=True):
    col1, col2 = st.columns([6, 3])
    # Nella colonna col1 è presente la sezione riguardante la mappa
    with col1:
        with col2:
            with st.container(border=True):
                st.markdown("<h4 style='text-align: center; margin-top: -15px'>Import</h4>", unsafe_allow_html=True)
                #st.write("""Nella sezione di **Import** è possibile caricare un file GeoJSON precedentemente salvato, in modo tale da visualizzare le
                #           aree e le relative informazioni all'interno della mappa. È eventualmente possibile aggiungere nuove aree a quelle già presenti
                #          e scaricare la lista aggiornata con il pulsante di *Export*.
                #""")
                uploaded_file = st.file_uploader("Carica un file GeoJSON", type=["geojson"], 
                                                        key="file_uploader", 
                                                        help="""Il file GeoJSON deve contenere features e deve avere una struttura adeguata. 
                                                        Cliccare sul pulsante X per togliere il file inserito non cambia la mappa.""")

                if uploaded_file is not None:
                    read_imported_geojson(uploaded_file)
                else:
                    st.session_state.last_uploaded_file = None
        # Mappa chiamata m ottenuta per creare una mappa con
        # diverse impostazioni come zoom, basemap, layer di disegno 
        m = create_map()

        # Questo if consente di avere un pop up quando si passa sopra
        # ad un'area disegnata mostrando il suo nome relativo inserito
        # in alla sua creazione. Per farlo cerca se è presente la lista
        # di aree disegnate nel session state e se la trova estrae il nome
        # dalle properties di ciascuna e lo assegna alla relativa figura in modo tale
        # che sia visibile al momento dell'hover dell'area selezionata 
        if 'drawings' in st.session_state:
            add_geojson_to_map(st.session_state.drawings, m)

        # Centra la mappa ai limiti delle coordinate
        if 'bounds' in st.session_state:
            m.fit_bounds(st.session_state.bounds)
        else:
            m.set_center(st.session_state.lon, st.session_state.lat, st.session_state.zoom)
        
        # Viene ottenuto il componente streamlit_folium chiamato st_component
        # che servirà per ottenere le diverse informazioni sui disegni/aree
        # selezionate nella mappa
        st_component = st_folium(m, use_container_width=True)
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

        # Questo if ottiene l'oggetto last_object_clicked contenente le coordinate
        # di un punto cliccato dall'utente su un'area disegnata. Tramite queste coordinateà
        # viene trovata la feature/area sulla mappa che le contiene e a seconda se è presente o meno
        # nella lista delle feature selezionate allora verrà aggiunta/tolta (selezionata/deselezionata)
        if st_component.get('last_object_clicked') is not None:
            last_object_clicked_coordinates = st_component['last_object_clicked']
            feature_clicked = find_feature(last_object_clicked_coordinates, st.session_state.drawings)
            if feature_clicked not in st.session_state.feature_clicked_list:
                st.session_state.feature_clicked_list.append(feature_clicked)
            else:
                st.session_state.feature_clicked_list.remove(feature_clicked)
            
            save_map_state_and_rerun(st_component)

        # st.json(st.session_state.last_uploaded_file)
        # st.write(st.session_state.drawings)

    # Nella colonna col2 è presente la sezione riguardante le opzioni e l'export della mappa     
    with col2:
        with st.container(border=True):
            st.markdown("<h4 style='text-align: center; margin-top: -15px'>Controlli Mappa</h4>", unsafe_allow_html=True)
            new_toggle_value = st.toggle("Contieni tutte le aree inserite", value=st.session_state.bounds_toggle, 
                                        help="""Attiva l'opzione "Contieni tutte le aree inserite" per fare in modo che la mappa
                                        si sposti automaticamente (all'aggiunta di una nuova area) in modo da rendere tutte le aree visibili. 
                                        Se l'opzione è disattivata, la mappa invece rimarrà ferma all'ultima posizione.""")
            if new_toggle_value != st.session_state.bounds_toggle:
                st.session_state.bounds_toggle = new_toggle_value
                st.rerun()

            st.markdown("<p style='margin-bottom: -20px'>Seleziona il tipo di cancellazione</p>", unsafe_allow_html=True)
            tab1, tab2, tab3 = st.tabs(["Canc. per selezione", "Canc. per tipologia", "Tutte le aree"])

            # Caso in cui si sceglie l'eliminazione di aree per selezione (click sull'area)
            with tab1:
                st.info("Clicca su un'area per selezionarla/deselezionarla")
                remove_single_area_button = st.button("Cancella una o più aree", disabled=not bool(st.session_state.get('feature_clicked_list')), use_container_width=True)
                # st.write(st.session_state.drawings)
                if remove_single_area_button:
                    drawings = remove_areas(st.session_state.drawings)
                    st.session_state.drawings = drawings
                    st.session_state.feature_clicked_list = []
                    save_map_state_and_rerun(st_component)

            # Caso in cui si sceglie eliminazione per tipologia (per properties: name)
            with tab2:
                name_area = st.multiselect("Seleziona una o più tipologia di aree da cancellare", 
                                           options=st.session_state.options,
                                           placeholder="Scegli un'opzione")
                name_area_correct = [name.lower() for name in name_area]
                # st.write(name_area_correct)
                remove_area_by_name_button = st.button("Cancella aree", disabled=not bool(st.session_state.get('drawings')), use_container_width=True)
                if remove_area_by_name_button:
                    drawings = remove_areas_by_name(st.session_state.drawings, name_area_correct)
                    st.session_state.drawings = drawings
                    save_map_state_and_rerun(st_component)

            # Caso in cui si sceglie eliminazione totale di tutte le aree inserite
            with tab3:
                remove_all_button = st.button("Cancella tutte le aree inserite", disabled=not bool(st.session_state.get('drawings')), use_container_width=True)
                if remove_all_button:
                    st.session_state.drawings = []
                    st.session_state.feature_clicked_list = []
                    save_map_state_and_rerun(st_component)

        with st.container(border=True):
            st.markdown("<h4 style='text-align: center; margin-top: -15px'>Export</h4>", unsafe_allow_html=True)
            # Questo if controlla se è presente una lista di disegni/aree selezionate e
            # dopo averli convertiti in un formato GeoJSON adeguato è possibile scaricare
            # il file contenente tutte le informazioni.
            if 'drawings' in st.session_state:
                # Converti i disegni in formato GeoJSON
                features = [Feature(geometry=drawing['geometry'], properties=drawing['properties']) for drawing in st.session_state.drawings]
                feature_collection = FeatureCollection(features)
                geojson_str = json.dumps(feature_collection)

                # Determina il nome del file in base alla lunghezza della lista dei disegni
                default_file_name = "data.geojson"
                if len(st.session_state.drawings) == 0:
                    default_file_name = "empty.geojson"
                elif len(st.session_state.drawings) > 1:
                    default_file_name = "multi_data.geojson"
                file_name = st.text_input("Inserisci nome file", help="""Il nome che verrà inserito rappresenterà il nome del file
                                          nel quale verrà rinominato il file esportato. IMPORTANTE premere il pulsante *Invio* per 
                                          confermare il nome inserito.""")
                if not file_name:
                    file_name = default_file_name
                elif not file_name.endswith(".geojson"):
                    file_name += ".geojson"

                # Aggiungi il pulsante per scaricare il file GeoJSON
                st.download_button(
                    label="Export GeoJSON file",
                    data=geojson_str,
                    file_name=file_name,
                    mime="application/geo+json",
                    use_container_width=True
                )

                #st.write(st.session_state.drawings)
                st.json(geojson_str, expanded=False)


# --------- PARTE DESCRITTIVA --------------
st.header("Introduzione")

st.write("""Questa pagina della Web App permette la visualizzazione di una mappa interattiva grazie alla libreria
         di **Leafmap** con la possibilità di modificare, disegnare aree e salvare relative informazioni. Le 2 principali funzioni
         di questa sezione sono:
        """)
st.write("""
- **Esportazione** di un file in formato GeoJSON rappresentante le aree disegnate sulla mappa interattiva.
- **Importazione** di un file GeoJSON salvato in precedenza per visualizzare a schermo le aree e le relative informazioni.
""")

st.subheader("Mappa")
st.write("""Sulla mappa interattiva è possibile utilizzare i diversi elementi di disegno e di ricerca forniti dall'interfaccia 
grafica di **Leafmap**. Gli elementi principali sono:
""")
st.write(""" 
- Pulsanti di ***Zoom in*** e ***Zoom out*** per fare zoom sulla mappa.
        
- Pulsante ***Full Screen*** per visualizzare la mappa a schermo intero.
- Elemento ***Show where I am*** per attivare la geolocalizzazione e ottenere 
l'area approssimativa.
- Pulsante di ***Ricerca*** per ottenere un luogo o una via precisa.
- Elemento ***Draw a polygon*** per disegnare un poligoni con un numero di lati variabile.
- Elemento ***Draw a rectangle*** per disegnare un rettangoli di dimensione variabile.
""")

