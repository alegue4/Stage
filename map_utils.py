import time
import io
import os
import json
import io
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import leafmap  # Assicurati di avere leafmap installato

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
