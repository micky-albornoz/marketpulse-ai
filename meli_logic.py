import time
import json
import pandas as pd
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ==========================================
# 1. CONFIGURACIÓN DEL NAVEGADOR (DRIVER)
# ==========================================
def iniciar_driver():
    """
    Esta función se encarga de configurar y abrir una ventana de Google Chrome
    controlada por código (Selenium).
    """
    print("   🔧 [Paso 1] Inicializando configuración de Chrome...")
    
    # Creamos un objeto de opciones para personalizar cómo se abre Chrome
    options = Options()
    options.add_argument("--start-maximized")  # Abre la ventana en pantalla completa
    
    # --- Argumentos Técnicos para evitar errores en distintos sistemas ---
    # Estos comandos ayudan a que Chrome no se bloquee en entornos restringidos (como Mac o Linux)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu") 
    
    try:
        # En Selenium 4.10+, esta línea descarga y configura el driver automáticamente.
        # Ya no necesitamos herramientas externas.
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"   ❌ Error crítico al lanzar el navegador: {e}")
        return None

# ==========================================
# 2. FUNCIÓN GENÉRICA PARA OBTENER DATOS
# ==========================================
def obtener_json_selenium(driver, url):
    """
    Esta función es nuestro 'mensajero'. Le decimos a qué URL ir,
    espera a que cargue, y nos devuelve el texto que encuentre (el JSON).
    """
    print(f"   🤖 [Navegando] Destino: {url}")
    try:
        driver.get(url) # Ordena al navegador ir a la dirección web
        
        # --- ESPERA ESTRATÉGICA ---
        # Esperamos 3 segundos para dar tiempo a que la página cargue completamente.
        # Si no esperamos, podríamos intentar leer una página en blanco.
        time.sleep(3) 
        
        # Buscamos la etiqueta <body> del HTML, que es donde la API de Mercado Libre
        # muestra los datos en formato texto.
        content = driver.find_element(By.TAG_NAME, "body").text
        
        # Convertimos ese texto en un diccionario de Python (JSON)
        return json.loads(content)
    except Exception as e:
        print(f"   ⚠️ No se pudo leer los datos de la URL: {e}")
        return None

# ==========================================
# 3. OBTENCIÓN DE TENDENCIAS (DATA EXTRACTION)
# ==========================================
def obtener_tendencias_top(limit=10):
    """
    Obtiene las palabras más buscadas en Mercado Libre Argentina (MLA).
    """
    url = "https://api.mercadolibre.com/trends/MLA"
    
    print("🔄 [Inicio] Abriendo navegador para consultar Tendencias...")
    driver = iniciar_driver()
    
    if not driver: return pd.DataFrame() # Si falla el driver, devolvemos tabla vacía

    try:
        data = obtener_json_selenium(driver, url)
        if data:
            print(f"   ✅ ÉXITO: Se descargaron {len(data)} tendencias.")
            # Convertimos la lista de datos en una Tabla (DataFrame) y devolvemos las primeras 'limit'
            return pd.DataFrame(data).head(limit)
        else:
            print("   ⚠️ La API no devolvió datos (JSON vacío).")
            return pd.DataFrame()
    except Exception as e:
        print(f"   ❌ Error general en tendencias: {e}")
        return pd.DataFrame()
    finally:
        # IMPORTANTE: Siempre cerrar el navegador al terminar para liberar memoria
        if driver:
            print("   🏁 [Fin] Cerrando ventana de tendencias.")
            driver.quit() 

# ==========================================
# 4. ANÁLISIS PROFUNDO DE COMPETENCIA
# ==========================================
def analizar_competencia(keyword):
    """
    Para una palabra clave (ej: 'Auriculares'), investiga:
    - Cuántos vendedores hay.
    - Precios promedio.
    - Qué dicen los clientes (Sentimiento).
    """
    # Abrimos una nueva ventana limpia para cada búsqueda
    driver = iniciar_driver()
    if not driver: return None
    
    datos_finales = None
    
    try:
        # --- PASO A: Buscar el producto ---
        # Construimos la URL de búsqueda de la API
        url_search = f"https://api.mercadolibre.com/sites/MLA/search?q={keyword}"
        data = obtener_json_selenium(driver, url_search)
        
        if data:
            # Extraemos la lista de resultados y el total de competidores
            results = data.get('results', [])
            total_resultados = data.get('paging', {}).get('total', 0)
            
            if results:
                # Calculamos precio promedio de la primera página
                precios = [item.get('price', 0) for item in results]
                precio_promedio = sum(precios) / len(precios)
                
                # Contamos cuántos son vendedores 'Platinum' (Los "monstruos" de la categoría)
                platinum_count = sum(1 for item in results if item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status') == 'platinum')
                pct_platinum = (platinum_count / len(results)) * 100
                
                # --- PASO B: Analizar preguntas del mejor posicionado ---
                # Tomamos el ID del primer producto que aparece
                top_item_id = results[0].get('id')
                url_questions = f"https://api.mercadolibre.com/questions/search?item_id={top_item_id}"
                data_questions = obtener_json_selenium(driver, url_questions)
                
                preguntas_texto = []
                if data_questions:
                    # Guardamos solo el texto de las preguntas
                    preguntas_texto = [q.get('text', '') for q in data_questions.get('questions', [])]
                
                # --- PASO C: Inteligencia Artificial (Sentiment Analysis) ---
                score_sent = 0
                label_sent = "Neutro"
                if preguntas_texto:
                    # Usamos TextBlob para analizar si las preguntas son positivas o negativas
                    scores = [TextBlob(t).sentiment.polarity for t in preguntas_texto]
                    score_sent = sum(scores) / len(scores)
                    
                    # Etiquetamos el resultado numérico
                    if score_sent > 0.1: label_sent = "Positivo"
                    elif score_sent < -0.1: label_sent = "Negativo"

                # Empaquetamos todo en un diccionario limpio
                datos_finales = {
                    "keyword": keyword,
                    "competencia_cantidad": total_resultados,
                    "precio_promedio": round(precio_promedio, 2),
                    "porcentaje_platinum": round(pct_platinum, 1),
                    "sentimiento_score": round(score_sent, 2),
                    "sentimiento_label": label_sent,
                    "cant_preguntas_analizadas": len(preguntas_texto)
                }
                
    except Exception as e:
        print(f"Error analizando {keyword}: {e}")
    finally:
        # Cerramos el navegador de esta consulta específica
        if driver:
            driver.quit()
        
    return datos_finales

# ==========================================
# 5. CONTROLADOR PRINCIPAL (ORQUESTADOR)
# ==========================================
def generar_reporte_oportunidades():
    """
    Función Maestra: Llama a todas las anteriores y construye la tabla final.
    """
    # 1. Obtenemos las tendencias (Limitamos a 3 para pruebas rápidas)
    df_trends = obtener_tendencias_top(limit=3) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ Iniciando análisis profundo ítem por ítem...")
    
    # 2. Iteramos (recorremos) cada tendencia encontrada
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        print(f"   🔎 [Investigando] {keyword}...")
        
        # 3. Analizamos cada una
        datos = analizar_competencia(keyword)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    # 4. Creamos la tabla final
    df_final = pd.DataFrame(resultados)
    
    # 5. Calculamos el 'Opportunity Score' (Fórmula personalizada)
    if not df_final.empty:
        # Lógica: Queremos BAJA competencia y BAJOS Platinum.
        # Si la competencia es baja, el score sube.
        df_final['opportunity_score'] = (
            (1 / (df_final['competencia_cantidad'] + 1)) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final
