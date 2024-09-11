import streamlit as st
import json
import requests
import geopandas as gpd
import numpy as np
from PIL import Image, ImageOps
from io import BytesIO, StringIO
from streamlit_image_comparison import image_comparison
from utils import setup_sidebar

# ========================================================================
# Definizione di Funzioni

# Funzione per calcolare il centro delle coordinate
def calculate_center(coordinates):
    # Estrai tutte le singole coordinate dai poligoni
    flat_coords = [coord for sublist in coordinates for coord in sublist]
    
    # Calcola il centro
    center_lat = np.mean([coord[1] for coord in flat_coords])
    center_lon = np.mean([coord[0] for coord in flat_coords])
    
    return center_lat, center_lon

# Funzione per calcolare il bounding box dalle coordinate
def calculate_bounding_box(coordinates_list):
    # Estrai tutte le coordinate e convertile in una lista piatta
    flat_coords = [coord for sublist in coordinates_list for coord in sublist]
    
    # Calcola le coordinate minime e massime
    min_lon = min(coord[0] for coord in flat_coords)
    max_lon = max(coord[0] for coord in flat_coords)
    min_lat = min(coord[1] for coord in flat_coords)
    max_lat = max(coord[1] for coord in flat_coords)
    
    return min_lon, min_lat, max_lon, max_lat

# Funzione per calcoare la risoluzione spaziale dell'immagine (metri per pixel)
def calculate_resolution(bbox, image_dim, pixel_density=1):
    min_lon, min_lat, max_lon, max_lat = bbox
    width, height = image_dim

    # Calcolo del centro del bounding box
    center_lat = (min_lat + max_lat) / 2

    # Calcolo della dimensione in metri del bounding box
    # 111320 è la distanza approssimativa in metri di un grado di latitudine
    lat_distance = (max_lat - min_lat) * 111320
    lon_distance = (max_lon - min_lon) * 111320 * np.cos(np.radians(center_lat))

    # Dimensione dell'immagine considerando la densità dei pixel
    width *= pixel_density
    height *= pixel_density

    # Calcolo della risoluzione spaziale (metri per pixel)
    resolution_lat = lat_distance / height
    resolution_lon = lon_distance / width

    # Calcolo dell'area di un pixel (metri quadrati per pixel)
    area_pixel = resolution_lat * resolution_lon

    return resolution_lat, resolution_lon, area_pixel

# Funzione per ottenere una immagine statica grazie all'API di MapBox
@st.cache_data(show_spinner="Fetching data from API...")
def get_static_map_image(bbox):
    mapbox_api_key = st.secrets["api_keys"]["static_image_mapbox"]
    url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{bbox}/600x600@2x?access_token={mapbox_api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        st.error("Errore durante il recupero dell'immagine statica della mappa.")

# Funzione per convertire una immagine in bianco e nero
@st.cache_data()
def convert_to_bw(image_bytes):
    # Apri l'immagine utilizzando PIL
    img = Image.open(BytesIO(image_bytes))
    # Converti l'immagine in scala di grigi
    img_bw = img.convert('L')
    # Ritorna l'immagine convertita in scala di grigi
    return img_bw

# Funzione per convertire una immagine in una scala di colori pseudotermica
@st.cache_data()
def convert_to_thermal(image_bytes, first_color, second_color):
    # Apri l'immagine utilizzando PIL
    img = Image.open(BytesIO(image_bytes))
    # Converti l'immagine in scala di grigi
    img_gray = img.convert('L')
    # Applica un effetto di mappa termica
    img_thermal = ImageOps.colorize(img_gray, black=first_color, white=second_color, midpoint=128)
    return img_thermal

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % tuple(rgb)
# =============================================================================
# Struttura della Web App

# Set up Streamlit page
st.set_page_config(layout="wide")
setup_sidebar()

# Dichiarazione delle variabili di stato per memorizzare le informazioni del file GeoJSON
uploaded_geojson = None
last_static_map_image = None

# Title
st.markdown("<h1 style='text-align: center; margin-top: -60px;'>GeoJson Analysis</h1>", unsafe_allow_html=True)
st.header("Introduzione")
# Introduzione
st.write("""In questa sezione della Web App è possibile caricare un file **GeoJSON** che 
         rappresenta l'area geografica contente le features presenti all'interno del file. 
         I file GeoJSON validi sono solo quelli con features aventi *Geometry* uguale a "**Polygon**".
         E' possibile ottenere un file GeoJSON corretto seguendo le istruzioni nella pagina Home 
         della Web App e attraverso la pagina **Interactive Map**. 
         """)
st.write("""Dopo aver caricato un file adeguato verrà visualizzata l'immagine satellitare,
         ottenuta grazie alla API chiamata Static Images API fornita da **MapBox** ([documentazione qui](https://docs.mapbox.com/api/maps/static-images/)) e
         i dati geospaziali come coordinate, risoluzione spaziale e CRS (Coordinate Reference System). 
         E' possibile inoltre selezionare un layer da applicare al di sopra della immagine ottenuta. Grazie all'utilizzo di uno *Slider* si potrà
         fare il confronto tra l'immagine originale e quella con il layer applicato.
         """)

with st.expander("Apri per vedere le **istruzioni** per lo **Slider** di confronto delle immagini"):
                            st.write("""
                            Puoi utilizzare lo slider per il confronto delle due immagini nel seguente modo:

                            1. **Click sull'immagine:** Facendo click direttamente sull'immagine si può spostare lo slider nella posizione desiderata.

                            2. **Trascina lo slider:** Tieni premuto lo slider e trascina verso destra e sinistra per regolarlo.

                            3. **Controllo dello slider:** Una volta interagito con lo slider potrebbe continuare a muoversi nonostante si sia rilasciato il mouse. 
                            In questo caso fare click sullo slider stesso (senza trascinarlo) per "rilasciarlo" e interrompere il movimento.
                                    
                            """)
uploader_col, select_col = st.columns(2)
with uploader_col:
    # File uploader per caricare il file GeoJSON contenente le diverse informazioni
    data = st.file_uploader(
                "File uploader per GeoJson",
                type=["geojson"], 
            )
    
with select_col:
    # Selectbox per selezionare i diversi layer/algoritmi da applicare all'immagine
    selected_layer = st.selectbox("Seleziona layer da applicare all'immagine", 
                                        options=["Black and White (BW)", "Pseudo Thermal (PT)"])
    black_col, white_col = st.columns(2)


if data is not None:
    # Controllo se il file GeoJSON appena caricato è diverso da quello precedente
    # così da evitare di eseguire di nuovo tutte le operazioni
    if uploaded_geojson != data:
        # Se inserisco un nuovo file diverso da quello precedente allora lo salvo
        uploaded_geojson = data

        file_contents = uploaded_geojson.read().decode('utf-8')
        
        geojson_data = json.load(StringIO(file_contents))
        gdp_data = gpd.read_file(StringIO(file_contents))
        crs_data = gdp_data.crs

        # Verifica se il file contiene almeno una feature, cioè un'area selezionata,
        # verificando se è presente l'attributo features oppure se la lunghezza
        # della lista di features è uguale a 0. 
        if 'features' not in geojson_data or len(geojson_data['features']) == 0:
            st.error("Il file GeoJSON non contiene alcuna area selezionata.")
        else:
            # Controlla se i tipi di geometria presenti nel file sono tutti di tipo
            # Polygon, altrimenti non analizzare ulteriormente
            valid_geometry = True
            for feature in geojson_data['features']:
                if feature['geometry']['type'] not in ['Polygon', 'MultiPolygon']:
                    valid_geometry = False
                    break
            
            if valid_geometry:
                # Se la geometria è valida, cioè di tipo Polygon allora estrae 
                # le coordinate salvandole in una lista
                coordinates = []
                for feature in geojson_data['features']:
                    coords = feature['geometry']['coordinates'][0][:-1]  # Considera solo il contorno esterno
                    coordinates.append(coords)
                
                # Visualizza le coordinate solo se necessario
                if coordinates:
                    # Calcola il centro dell'area selezionata
                    center_lat, center_lon = calculate_center(coordinates)

                    # Calcola il bounding box
                    min_lon, min_lat, max_lon, max_lat = calculate_bounding_box(coordinates)
                    bbox = [min_lon, min_lat, max_lon, max_lat]

                    # Calcola la risoluzione spaziale
                    image_dim = (600, 600)  # Dimensioni base dell'immagine (larghezza, altezza)
                    pixel_density = 2  # Densità dei pixel (@2x)
                    resolution_lat, resolution_lon, resolution_area= calculate_resolution(bbox, image_dim, pixel_density)
                    rounded_res_lat = round(resolution_lat, 4)
                    rounded_res_lon = round(resolution_lon, 4)
                    rounded_res_area = round(resolution_area, 4)

                    # Ottieni l'immagine statica solo se è diversa dall'ultima memorizzata
                    if last_static_map_image is None or last_static_map_image['bbox'] != bbox:
                        # Ottieni l'immagine statica tramite chiamata API e la salva
                        # grazie al sessione state
                        static_map_bytes = get_static_map_image(bbox)
                        # Converte l'immagine statica in un oggetto PIL
                        static_map_image = Image.open(BytesIO(static_map_bytes))
                        # Memorizza l'immagine statica e il bounding box
                        last_static_map_image = {'image': static_map_image, 'bbox': bbox}
                        
                    else:
                        # Utilizza l'ultima immagine statica memorizzata senza fare nuovamente
                        # la chiamata API
                        static_map_image = last_static_map_image['image']

                    col1, col2 = st.columns(2)

                    with col1:
                        # Sezione per mostrare informazioni relative all'immagine ottenuta
                        st.subheader("Info Aggiuntive")
                        c1 = st.container(border=True)
                        with c1:        
                            st.markdown(f"""
                                <div style="display: flex; flex-direction: column; gap: 10px;">
                                    <div style="padding: 15px 15px 0 15px; border: 2px solid #cccccc; border-radius: 8px; background-color: #f0f2f6;">
                                        <p style='font-size: 25px; font-weight: 600;'>CRS ({crs_data})</p>
                                    </div>
                                    <div style="padding: 15px; border: 2px solid #cccccc; border-radius: 8px; background-color: #f0f2f6; display: flex; justify-content: space-between; align-items: stretch;">
                                        <div style="flex: 1; padding-right: 15px; border-right: 2px solid grey;">
                                            <p style='font-size: 25px; font-weight: 600;'>Coordinate dei Vertici</p>
                                            <p>Min Latitude: {min_lat}</p>
                                            <p>Max Latitude: {max_lat}</p>
                                            <p>Min Longitude: {min_lon}</p>
                                            <p>Max Longitude: {max_lon}</p>
                                        </div>
                                        <div style="flex: 1; padding-left: 15px;">
                                            <p style='font-size: 25px; font-weight: 600;'>Coordinate del Centro</p>
                                            <p>Latitude: {center_lat}</p>
                                            <p>Longitude: {center_lon}</p>
                                        </div>
                                    </div>
                                    <div style="padding: 15px 15px 0 15px; border: 2px solid #cccccc; margin-bottom: 20px; border-radius: 8px; background-color: #f0f2f6;">
                                        <p style='font-size: 25px; font-weight: 600;'>Risoluzione Spaziale</p>
                                        <p>Lat Resolution: {round(resolution_lat, 6)} m/pixel</p>
                                        <p>Lon Resolution: {round(resolution_lon, 6)} m/pixel</p>
                                        <p>Area del pixel: {round(resolution_area, 6)} m²/pixel</p>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)



                            
                    with col2:
                        # Sezione per mostrare immagine con il layer applicato e con lo slider di confronto
                        st.subheader("Immagine Satellitare")
                        if selected_layer == "Black and White (BW)":
                            # Converti l'immagine statica in bianco e nero
                            img_bw = convert_to_bw(static_map_bytes)
                            image_comparison(
                                img1=static_map_image,
                                img2= img_bw,
                                label1="Mappa",
                                label2="BW",
                                width=580,
                                starting_position=85,
                                show_labels=True,
                                make_responsive=True,
                                in_memory=True,
                            )
                        elif selected_layer == "Pseudo Thermal (PT)":
                            first_color = black_col.color_picker("Seleziona il colore per i toni **scuri** dell'immagine", value="#000000",
                                                                    help="Questo colore sostituisce i toni più scuri dell'immagine originale. Selezionare un colore scuro, come il blu navy o il verde foresta, per mantenere le aree scure ben definite e ricche di dettagli.")
                            second_color = white_col.color_picker("Seleziona il colore per i toni **chiari** dell'immagine", value="#FF0000",
                                                                    help="Questo colore viene utilizzato per le aree più luminose della mappa. Colori chiari come il giallo o il lavanda possono illuminare l'immagine e mettere in risalto le caratteristiche chiave.")
                            # Converti l'immagine statica in pseudo thermal
                            img_pt = convert_to_thermal(static_map_bytes, first_color, second_color)
                            image_comparison(
                                img1=static_map_image,
                                img2= img_pt,
                                label1="Mappa",
                                label2="PT",
                                width=580,
                                starting_position=85,
                                show_labels=True,
                                make_responsive=True,
                                in_memory=True,
                            )
            else:
                st.error("Il file GeoJSON deve contenere solo geometrie di tipo Polygon.")

    
