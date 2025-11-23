import time
import json
import pandas as pd
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ==============================================================================
# MÓDULO DE INGENIERÍA DE DATOS & SCRAPING
# ------------------------------------------------------------------------------
# Este módulo maneja la interacción con fuentes de datos externas (Mercado Libre).
# Implementa técnicas de 'Browser Automation' para garantizar el acceso a datos
# públicos, simulando comportamiento humano para cumplir con políticas de seguridad.
# ==============================================================================

def iniciar_driver():
    """
    Inicializa una instancia de Google Chrome con configuración avanzada 
    de 'Stealth Mode' (Modo Sigilo).
    
    Objetivo: Evadir la detección de bots mediante la normalización de headers
    y la eliminación de banderas de automatización (WebDriver flags).
    """
    print("   🔧 [Sistema] Iniciando motor de navegación (Chrome WebDriver)...")
    
    options = Options()
    options.add_argument("--start-maximized")
    
    # --- ESTRATEGIA DE MIMETISMO (ANTI-FINGERPRINTING) ---
    
    # 1. Eliminación de Indicadores Visuales:
    # Oculta la barra de notificación "Un software automatizado de pruebas..."
    # Esto evita que scripts básicos de detección identifiquen el entorno.
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 2. Supresión de Banderas del Motor (Blink):
    # Desactiva la propiedad 'AutomationControlled' que suelen buscar los WAFs
    # (Web Application Firewalls) para bloquear bots.
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 3. Normalización de User-Agent:
    # Forzamos la identidad de un usuario estándar en MacOS para pasar filtros de OS.
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(options=options)
        
        # 4. Inyección de JavaScript (Estrategia Avanzada):
        # Sobrescribimos la propiedad 'navigator.webdriver' en el DOM antes de que cargue la página.
        # Esto asegura que cualquier script de validación en el cliente reciba 'undefined'
        # en lugar de 'true' al verificar si es un robot.
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        
        return driver
    except Exception as e:
        print(f"   ❌ [Error Crítico] Fallo al instanciar el driver: {e}")
        return None

# ==========================================
# FUNCIONES DE EXTRACCIÓN (ETL)
# ==========================================

def obtener_json_selenium(driver, url):
    """
    Navega a una URL específica y extrae el payload JSON renderizado.
    
    Args:
        driver: La instancia activa de Selenium.
        url: El endpoint de la API pública a consultar.
    """
    print(f"   🤖 [GET Request] Navegando a: {url}")
    try:
        driver.get(url)
        
        # Latencia Humana Simulada:
        # Esperamos 4 segundos. Esto tiene doble propósito:
        # 1. Asegurar la carga completa del DOM (Network Latency).
        # 2. Evitar patrones de comportamiento agresivo (Rate Limiting).
        time.sleep(4) 
        
        # Extracción del Raw Data:
        # La API devuelve el JSON dentro del tag <body> del HTML.
        content = driver.find_element(By.TAG_NAME, "body").text
        return json.loads(content)
    except Exception as e:
        print(f"   ⚠️ [Warning] No se pudo parsear la respuesta: {e}")
        return None

def obtener_tendencias_top(limit=10):
    """
    Consulta el endpoint de /trends para identificar la demanda actual del mercado.
    """
    url = "https://api.mercadolibre.com/trends/MLA"
    
    print("🔄 [Proceso] Iniciando sesión de extracción de Tendencias...")
    driver = iniciar_driver()
    
    if not driver: return pd.DataFrame()

    try:
        data = obtener_json_selenium(driver, url)
        if data:
            print(f"   ✅ [Éxito] Dataset descargado: {len(data)} registros.")
            return pd.DataFrame(data).head(limit)
        else:
            print("   ⚠️ [Alerta] La API respondió con un dataset vacío.")
            return pd.DataFrame()
    except Exception as e:
        print(f"   ❌ [Error] Excepción no controlada: {e}")
        return pd.DataFrame()
    finally:
        # Gestión de Recursos:
        # Es vital cerrar el navegador para liberar RAM y procesos huérfanos (chromedriver).
        if driver:
            print("   🏁 [Sistema] Liberando recursos del navegador.")
            driver.quit() 

def analizar_competencia(keyword):
    """
    Realiza un análisis de mercado profundo para una palabra clave específica.
    Cruza datos de Oferta (Search API) con datos Cualitativos (Questions API).
    """
    # Instanciamos un nuevo contexto de navegador para mantener cookies limpias (Stateless)
    driver = iniciar_driver()
    if not driver: return None
    
    datos_finales = None
    
    try:
        # --- FASE 1: Análisis Cuantitativo (Oferta y Precios) ---
        url_search = f"https://api.mercadolibre.com/sites/MLA/search?q={keyword}"
        data = obtener_json_selenium(driver, url_search)
        
        if data:
            results = data.get('results', [])
            total_resultados = data.get('paging', {}).get('total', 0)
            
            if results:
                # Cálculo de métricas de negocio
                precios = [item.get('price', 0) for item in results]
                precio_promedio = sum(precios) / len(precios)
                
                # Detección de saturación de mercado (Vendedores Platinum)
                platinum_count = sum(1 for item in results if item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status') == 'platinum')
                pct_platinum = (platinum_count / len(results)) * 100
                
                # --- FASE 2: Análisis Cualitativo (NLP & Voice of Customer) ---
                # Obtenemos el ID del líder de la categoría para auditar sus preguntas
                top_item_id = results[0].get('id')
                url_questions = f"https://api.mercadolibre.com/questions/search?item_id={top_item_id}"
                data_questions = obtener_json_selenium(driver, url_questions)
                
                preguntas_texto = []
                if data_questions:
                    preguntas_texto = [q.get('text', '') for q in data_questions.get('questions', [])]
                
                # Procesamiento de Lenguaje Natural (Sentiment Analysis)
                score_sent = 0
                label_sent = "Neutro"
                if preguntas_texto:
                    scores = [TextBlob(t).sentiment.polarity for t in preguntas_texto]
                    score_sent = sum(scores) / len(scores)
                    
                    # Categorización del sentimiento
                    if score_sent > 0.1: label_sent = "Positivo"
                    elif score_sent < -0.1: label_sent = "Negativo"

                # Estructuración del objeto final de datos
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
        print(f"   ❌ Error analizando '{keyword}': {e}")
    finally:
        if driver:
            driver.quit()
        
    return datos_finales

# ==========================================
# 5. LÓGICA PRINCIPAL
# ==========================================
def generar_reporte_oportunidades():
    """
    Pipeline Principal:
    1. Fetch Trends -> 2. Loop Analysis -> 3. Data Transformation -> 4. Scoring
    """
    # Limitamos el alcance para demostración (MVP)
    df_trends = obtener_tendencias_top(limit=3) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Iniciando procesamiento secuencial de oportunidades...")
    
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        print(f"   🔎 [Analizando Nicho] {keyword}...")
        
        datos = analizar_competencia(keyword)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    df_final = pd.DataFrame(resultados)
    
    # Algoritmo de Scoring de Oportunidad
    if not df_final.empty:
        # Lógica: Mayor Score = Menos competencia + Menos dominio de grandes marcas
        df_final['opportunity_score'] = (
            (1 / (df_final['competencia_cantidad'] + 1)) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final
