import time
import json
import pandas as pd
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN DEL NAVEGADOR ---
def iniciar_driver():
    """
    Inicia Chrome con la configuración EXACTA que funcionó en tu test.
    """
    print("   🔧 Preparando navegador...")
    options = Options()
    # Usamos solo lo básico para asegurar que abra la ventana visualmente
    options.add_argument("--start-maximized")
    
    try:
        # Instalación y lanzamiento
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"   ❌ Error al abrir Chrome: {e}")
        return None

def obtener_json_selenium(driver, url):
    """Navega y extrae datos."""
    print(f"   🤖 Navegando a: {url}")
    try:
        driver.get(url)
        # Espera un poco más para asegurar carga visual
        time.sleep(3) 
        
        # Extraemos el texto del body (donde vive el JSON en la API)
        content = driver.find_element(By.TAG_NAME, "body").text
        return json.loads(content)
    except Exception as e:
        print(f"   ⚠️ No se pudo leer JSON: {e}")
        return None

def obtener_tendencias_top(limit=10):
    url = "https://api.mercadolibre.com/trends/MLA"
    
    print("🔄 Abriendo navegador para Tendencias...")
    driver = iniciar_driver()
    
    if not driver: return pd.DataFrame()

    try:
        data = obtener_json_selenium(driver, url)
        if data:
            print(f"   ✅ ÉXITO: {len(data)} tendencias obtenidas.")
            return pd.DataFrame(data).head(limit)
        else:
            print("   ⚠️ La API no devolvió datos.")
            return pd.DataFrame()
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return pd.DataFrame()
    finally:
        if driver:
            print("   🏁 Cerrando ventana de tendencias.")
            driver.quit() 

def analizar_competencia(keyword):
    # Abrimos una nueva ventana limpia para cada búsqueda
    driver = iniciar_driver()
    if not driver: return None
    
    datos_finales = None
    
    try:
        # 1. Buscar en la API de Search
        url_search = f"https://api.mercadolibre.com/sites/MLA/search?q={keyword}"
        data = obtener_json_selenium(driver, url_search)
        
        if data:
            results = data.get('results', [])
            total_resultados = data.get('paging', {}).get('total', 0)
            
            if results:
                precios = [item.get('price', 0) for item in results]
                precio_promedio = sum(precios) / len(precios)
                
                platinum_count = sum(1 for item in results if item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status') == 'platinum')
                pct_platinum = (platinum_count / len(results)) * 100
                
                # 2. Buscar preguntas del top item
                top_item_id = results[0].get('id')
                url_questions = f"https://api.mercadolibre.com/questions/search?item_id={top_item_id}"
                data_questions = obtener_json_selenium(driver, url_questions)
                
                preguntas_texto = []
                if data_questions:
                    preguntas_texto = [q.get('text', '') for q in data_questions.get('questions', [])]
                
                # Análisis de sentimiento
                score_sent = 0
                label_sent = "Neutro"
                if preguntas_texto:
                    scores = [TextBlob(t).sentiment.polarity for t in preguntas_texto]
                    score_sent = sum(scores) / len(scores)
                    if score_sent > 0.1: label_sent = "Positivo"
                    elif score_sent < -0.1: label_sent = "Negativo"

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
        if driver:
            driver.quit()
        
    return datos_finales

def generar_reporte_oportunidades():
    # Limitamos a 3 para la prueba inicial
    df_trends = obtener_tendencias_top(limit=3) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ Iniciando análisis profundo...")
    
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        print(f"   🔎 Investigando: {keyword}...")
        datos = analizar_competencia(keyword)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        df_final['opportunity_score'] = (
            (1 / (df_final['competencia_cantidad'] + 1)) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final
