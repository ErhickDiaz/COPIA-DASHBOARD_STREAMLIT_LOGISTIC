import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from io import StringIO, BytesIO
from datetime import datetime
from shareplum import Site
from shareplum import Office365
from shareplum.site import Version

def realizar_webscraping():

    global df_pallets  # Asegurarnos de que estamos utilizando la variable global

            # Credenciales
    username = "kevin.urtubia01@grupobimbo.com"
    password = "Soporte.2028"
    sharepoint_url = "https://gbconnect.sharepoint.com"
    site_url = "/sites/Torredetransportacin"

    # Autenticación en SharePoint
    authcookie = Office365(sharepoint_url, username=username, password=password).GetCookies()
    site = Site(sharepoint_url + site_url, version=Version.v365, authcookie=authcookie)
    
    # Configuración del navegador Edge
    edge_options = webdriver.EdgeOptions()
    edge_options.add_argument("--disable-notifications")
    edge_options.add_argument("--disable-backgrounding-occluded-windows")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.join(os.path.expanduser('~'), 'Descargas'),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    driver = webdriver.Edge(options=edge_options)
    driver.maximize_window()

    try:
        # Realiza el scraping y la manipulación de la página web
        driver.get("https://a17.wms.ocs.oraclecloud.com/bimbo/index/")

        username = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "username")))
        password = driver.find_element(By.ID, "password")

        username.send_keys("torre_moni")
        password.send_keys("ideal-2024")
        password.send_keys(Keys.RETURN)

        KU = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "dijit_form_DropDownButton_1")))
        ActionChains(driver).move_to_element(KU).click().perform()

        vista_button = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//td[@class='dijitReset dijitMenuItemLabel' and text()='Vista']")))
        vista_button.click()

        kevintrans_button = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//td[@class='dijitReset dijitMenuItemLabel' and text()='KEVINTRANS']")))
        kevintrans_button.click()

        time.sleep(5)

        #---------------------------------------------------------------------------------------------------------------------------
        #Trabajo ASN Entrada --> Camiones en tránsito -----------------------------------------------------------------------------
        #---------------------------------------------------------------------------------------------------------------------------

        filtering_select = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="dijit_form_FilteringSelect_2"]')))
        filtering_select.send_keys("ASN Entrada")
        filtering_select.send_keys(Keys.RETURN)

        time.sleep(5)

        lupa = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div#view_GridAction_4 span.dijitReset.dijitStretch.dijitButtonContents[title='Buscar']")))
        driver.execute_script("arguments[0].click();", lupa)

        GrabBusq = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, 'dijit_TitlePane_0_titleBarNode')))
        GrabBusq.click()

        input_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//div[@class='dijitTitlePaneContentInner']//div[contains(@class, 'dijitTextBox dijitComboBox dijitValidationTextBox')]//input[@class='dijitReset dijitInputInner' and @role='textbox']")))
        
        time.sleep(2)

        input_field.send_keys('Transito')
        input_field.send_keys(Keys.RETURN)

        time.sleep(5)

        button_buscar = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//span[@class='dijitReset dijitInline dijitButtonText' and text()='Buscar']")))
        driver.execute_script("arguments[0].click();", button_buscar)

        time.sleep(5)

        export_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//span[@name='IBShipmentView.common_grid_export_action']")))
        export_button.click()

        export_csv_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//span[@role='button' and @aria-labelledby='dijit_form_Button_52_label']")))
        export_csv_button.click()

        time.sleep(5)

        accept_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.NAME, "dialog.alert.ok")))
        accept_button.click()

        time.sleep(10)

        download_link = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.LINK_TEXT, "Descargar")))
        download_link.click()

        time.sleep(10)

        # Ruta de la carpeta de descargas
        ruta_descargas = os.path.join(os.path.expanduser('~'), 'Descargas')

        # Busca el archivo más reciente en la carpeta de descargas
        files = os.listdir(ruta_descargas)
        paths = [os.path.join(ruta_descargas, basename) for basename in files]
        latest_file = max(paths, key=os.path.getctime)

        # Leer el archivo descargado
        # Cargar el archivo CSV
        Tractos_transito = pd.read_csv(latest_file, sep=';')

        # Filtrar las columnas que te interesan
        Tractos_transito = Tractos_transito[['Nro ASN', 'Estado', 'LPNs Env', 'UnOrigOrd', 'Registro de hora de modificaciÃ³n']]

        # Renombrar 'Nro ASN' a 'Desde' y extraer los caracteres del segundo al cuarto
        Tractos_transito['Desde'] = Tractos_transito['Nro ASN'].str[1:4]

        # Añadir una columna 'Hasta' con el valor "HKO - CEDIS"
        Tractos_transito['Hasta'] = "CEDIS"

        # Renombrar las columnas
        Tractos_transito.rename(columns={'UnOrigOrd': 'Bult. Env','Registro de hora de modificaciÃ³n': 'Hora de salida'}, inplace=True)
        
        reemplazos = {
                "GAX": "P. Chillán",
                "HKL": "P. Ideal",
                "HKN": "NB",
                "WGY": "Barcel"
                }
        
        Tractos_transito['Desde'] = Tractos_transito['Desde'].replace(reemplazos)

        # Reordenar las columnas para que 'Hasta' esté después de 'Desde'
        Tractos_transito = Tractos_transito[['Desde', 'Hasta', 'Estado', 'LPNs Env', 'Bult. Env', 'Hora de salida']]

        Tractos_transito['Hora de salida'] = pd.to_datetime(Tractos_transito['Hora de salida'], format='%d/%m/%Y %H:%M:%S')
        Tractos_transito = Tractos_transito.sort_values(by='Hora de salida')
        Tractos_transito.reset_index(drop=True, inplace=True)

        # Guardar el DataFrame actualizado directamente en SharePoint
        output = StringIO()
        Tractos_transito.to_csv(output, index=False)

        folder_url = "Documentos Compartidos/Dashboard_Streamlit/Tractos_Transito_Pre_primaria"

        # Acceder a la carpeta de SharePoint
        folder = site.Folder(folder_url)

        folder.upload_file(output.getvalue().encode("utf-8"), "Tractos_Transito_Pre_Primaria.csv")

        print("Archivo Tractos_Transito_Pre_Primaria.csv subido exitosamente a SharePoint.")

        #---------------------------------------------------------------------------------------------------------------------------
        #Trabajo OBLPNS --> Saturación Plantas -------------------------------------------------------------------------------------
        #---------------------------------------------------------------------------------------------------------------------------

        filtering_select = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="dijit_form_FilteringSelect_2"]')))
        filtering_select.send_keys("OB LPNs")
        filtering_select.send_keys(Keys.RETURN)

        time.sleep(5)

        sucursal = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, 'dijit_form_DropDownButton_0')))
        sucursal.click()
        
        time.sleep(5)

        input_sucursal = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//label[@for='dijit_form_FilteringSelect_0']/following::td[1]//input[@class='dijitReset dijitInputInner' and @type='text']")))
        input_sucursal.click()
        input_sucursal.clear()
        time.sleep(3)
        input_sucursal.send_keys('HKL')
        input_sucursal.send_keys(Keys.RETURN)

        time.sleep(5)

        cambSucur = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//span[@id="dijit_form_Button_0_label" and text()="Camb CantPack"]')))
        driver.execute_script("arguments[0].click();", cambSucur)

        time.sleep(5)

        lupa = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.dijitReset.dijitStretch.dijitButtonContents[title='Buscar']")))
        driver.execute_script("arguments[0].click();", lupa)

        GrabBusq = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button']//span[text()='Graba Busqueda']")))
        GrabBusq.click()

        input_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//div[@class='dijitTitlePaneContentInner']//div[contains(@class, 'dijitTextBox dijitComboBox dijitValidationTextBox')]//input[@class='dijitReset dijitInputInner' and @role='textbox']")))
        
        time.sleep(2)

        input_field.send_keys('Saturación Planta')
        input_field.send_keys(Keys.RETURN)

        time.sleep(5)

        button_buscar = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//span[@class='dijitReset dijitInline dijitButtonText' and text()='Buscar']")))
        driver.execute_script("arguments[0].click();", button_buscar)

        time.sleep(5)

        export_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.dijitDropDownButton[name='ObContainerView.common_grid_export_action']")))
        export_button.click()

        export_csv_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.NAME, "ObContainerView.common_grid_export_csv_action")))
        export_csv_button.click()

        time.sleep(5)
        accept_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.NAME, "dialog.alert.ok")))
        accept_button.click()

        time.sleep(10)
        download_link = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.LINK_TEXT, "Descargar")))
        download_link.click()

        time.sleep(10)

        # Procesar el archivo descargado y obtener la saturación
        print("--------------------------------------------------------")
        print("Finalizada la extracción de datos en WMS.")
        print("--------------------------------------------------------")
        print("Comienzo de trabajo con bases de datos:")
        print("")

        # Busca el archivo más reciente en la carpeta de descargas
        files = os.listdir(ruta_descargas)
        paths = [os.path.join(ruta_descargas, basename) for basename in files]
        latest_file = max(paths, key=os.path.getctime)

        # Leer el archivo descargado
        OBLPNS = pd.read_csv(latest_file)
        numero_filas = OBLPNS.shape[0]

        # Calcular la saturación
        Saturación = round((numero_filas / 110)*100, 2)

        print(f"La saturación es de {Saturación} %.")
        print("--------------------------------------------------------")

        folder_url_2 = "Documentos Compartidos/Dashboard_Streamlit/Saturacin_WMS"

        # Acceder a la carpeta de SharePoint
        folder2 = site.Folder(folder_url_2)

        # Nombre del archivo en SharePoint
        historical_data_file = f"historico_saturaciones_{datetime.now().strftime('%Y_%m_%d')}.csv"

        # Descargar el archivo si existe en SharePoint
        try:
            file_content = folder2.get_file(historical_data_file)
            file_str = BytesIO(file_content).getvalue().decode("utf-8")
            historico_df = pd.read_csv(StringIO(file_str))
        except Exception as e:
            # Si el archivo no existe, crear un nuevo DataFrame
            print(f"No se encontró el archivo {historical_data_file}, creando uno nuevo.")
            historico_df = pd.DataFrame(columns=["Fecha", "Saturación", "N° de pallets"])

        # Agregar nueva fila con la información actualizada
        nueva_fila = pd.DataFrame({
            'Fecha': [pd.Timestamp.now()],
            'Saturación': [Saturación],
            "N° de pallets": [numero_filas]
        })

        # Concatenar la nueva fila al DataFrame histórico
        historico_df = pd.concat([historico_df, nueva_fila], ignore_index=True)

        # Guardar el DataFrame actualizado directamente en SharePoint
        output = StringIO()
        historico_df.to_csv(output, index=False)
        folder2.upload_file(output.getvalue().encode("utf-8"), historical_data_file)

        print(f"Archivo '{historical_data_file}' subido exitosamente a SharePoint.")

        # Devolver la saturación calculada y los DataFrames
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        driver.quit()

# Función para ejecutar con reintentos
def ejecutar_con_reintentos():
    max_intentos = 3  # Número máximo de intentos
    intentos = 0
    intervalo_entre_intentos = 5  # Segundos entre intentos

    while intentos < max_intentos:
        exito = realizar_webscraping()  # Llamar al web scraping
        if exito:
            print("Proceso completado exitosamente.")
            break  # Si fue exitoso, terminar el bucle
        else:
            intentos += 1
            if intentos < max_intentos:
                print(f"Reintentando en {intervalo_entre_intentos} segundos...")
                time.sleep(intervalo_entre_intentos)  # Esperar antes de reintentar
            else:
                print("Se alcanzó el número máximo de intentos fallidos.")

if __name__ == "__main__":
    while True:
        ejecutar_con_reintentos()  # Ejecutar el scraping con reintentos
        print("Esperando 13 minutos para la próxima ejecución...")
        time.sleep(13 * 60)  # Esperar 13 minutos (13 * 60 segundos)

