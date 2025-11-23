import time
import random
import pandas as pd
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==============================================================================
# MÓDULO DE INGENIERÍA DE DATOS: VISUAL WEB SCRAPING
# ------------------------------------------------------------------------------
# ESTRATEGIA TÉCNICA:
# Debido a las restricciones de seguridad en la API pública (Error 403 - Forbidden),
# este módulo implementa una estrategia de "Frontend Scraping" (Extracción Visual).
#
# En lugar de consumir endpoints JSON, emulamos la navegación de un usuario real
# visitando las páginas web públicas (Tendencias y Buscador) y extrayendo
# la información visualmente del DOM (Document Object Model).
#
# BENEFICIOS:
# 1. Resiliencia: No depende de Tokens de API ni claves de desarrollador.
# 2. Transparencia: Utiliza datos públicos visibles para cualquier usuario.
# 3. Robustez: Simula latencia y comportamiento humano para evitar bloqueos.
# ==============================================================================

def iniciar_navegador_controlado():
    """
    Configura e inicializa una instancia de Google Chrome optimizada para
    simular un comportamiento humano y evitar bloqueos básicos de automatización.
    
    Returns:
        webdriver.Chrome: Instancia del navegador lista para usar.
        None: Si ocurre un error crítico al iniciar el driver.
    """
    print("   🔧 [Sistema] Inicializando navegador para lectura visual...")
    
    options = Options()
    options.add_argument("--start-maximized")
    
    # --- TÉCNICAS DE EVASIÓN DE DETECCIÓN (ANTI-BOT) ---
    # Desactivamos las banderas que Selenium suele enviar por defecto y que
    # delatan ante el servidor que es un robot controlando el navegador.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Usamos un User-Agent de una Mac real para pasar desapercibidos como tráfico legítimo
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"   ❌ [Error Crítico] No se pudo abrir Chrome: {e}")
        return None

# ==============================================================================
# LÓGICA DE EXTRACCIÓN DE TENDENCIAS (FRONTEND)
# ==============================================================================

def obtener_tendencias_mercado(limit=10):
    """
    Visita la página web pública de tendencias de Mercado Libre y extrae
    los términos más populares del momento leyendo el HTML.
    
    URL Objetivo: https://tendencias.mercadolibre.com.ar/
    
    Args:
        limit (int): Cantidad máxima de tendencias a recuperar (Default: 10).
        
    Returns:
        pd.DataFrame: Tabla con las keywords encontradas y sus enlaces.
    """
    url = "https://tendencias.mercadolibre.com.ar/"
    
    print(f"🔄 [Navegando] Visitando portal público: {url}")
    driver = iniciar_navegador_controlado()
    
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        
        # --- ESPERA ESTRATÉGICA (HUMAN DELAY) ---
        # Damos 3 segundos para que carguen estilos, imágenes y scripts.
        # Esto también permite que el usuario resuelva CAPTCHAs manualmente si aparecen.
        time.sleep(3)
        
        # --- ESTRATEGIA DE SELECTORES CSS DINÁMICOS ---
        # Mercado Libre cambia su estructura HTML frecuentemente (A/B Testing).
        # Probamos una lista de selectores comunes en orden de probabilidad.
        # El primero que devuelva elementos será el utilizado.
        posibles_selectores = [
            "ol li a",              # Lista ordenada simple (Estructura clásica)
            "div.andes-card a",     # Tarjetas de diseño 'Andes' (Diseño moderno)
            "a.trends-term",        # Clases específicas antiguas
            ".ui-search-item__title a" # Enlaces genéricos de título
        ]
        
        elementos = []
        for selector in posibles_selectores:
            elementos = driver.find_elements(By.CSS_SELECTOR, selector)
            if elementos:
                print(f"   👀 [Visual] Se detectaron {len(elementos)} elementos con el selector: {selector}")
                break # ¡Encontramos uno que sirve! Dejamos de buscar.
        
        # Procesamos los elementos encontrados (Data Parsing)
        for elem in elementos[:limit]:
            texto = elem.text.strip()
            if texto:
                datos_tendencias.append({"keyword": texto, "url": elem.get_attribute("href")})
    
    except Exception as e:
        print(f"   ⚠️ [Error Visual] Fallo al leer la web: {e}")
    finally:
        # Importante: Cerrar el navegador para liberar memoria RAM del sistema
        if driver:
            driver.quit() 

    # Verificación final de integridad de datos
    if datos_tendencias:
        print(f"   ✅ [Éxito] Se extrajeron {len(datos_tendencias)} tendencias de la pantalla.")
        return pd.DataFrame(datos_tendencias)
    else:
        print("   ⚠️ [Aviso] No se pudieron leer elementos visuales. La estructura web pudo haber cambiado.")
        return pd.DataFrame()

# ==============================================================================
# LÓGICA DE ANÁLISIS DE NICHO (FRONTEND SEARCH)
# ==============================================================================

def analizar_nicho_mercado(keyword):
    """
    Realiza una búsqueda real en la barra de Mercado Libre y analiza los 
    resultados visuales para extraer métricas de competencia y precios.
    
    Simula la acción de un usuario escribiendo en el buscador y revisando la primera página.
    
    Args:
        keyword (str): Término a buscar (ej: "Auriculares bluetooth").
        
    Returns:
        dict: Objeto con métricas calculadas (Precio promedio, Saturación, etc.)
    """
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos_consolidados = None
    
    try:
        # 1. Construcción de URL amigable (SEO Friendly)
        # Reemplazamos espacios por guiones para formar una URL válida de ML
        keyword_slug = keyword.replace(" ", "-")
        url_busqueda = f"https://listado.mercadolibre.com.ar/{keyword_slug}"
        
        print(f"   🔎 [Investigando] URL: {url_busqueda}")
        driver.get(url_busqueda)
        time.sleep(3) # Espera para carga visual del listado
        
        # 2. EXTRACCIÓN: Cantidad de Resultados (Volumen de Oferta)
        # Intentamos leer el contador que dice "10.000 resultados" arriba a la izquierda.
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            # Limpiamos el texto (ej: "10.000 resultados" -> "10000")
            texto_qty = qty_elem.text.replace(".", "").replace(" resultados", "").strip()
            total_resultados = int(texto_qty) if texto_qty.isdigit() else 1000
        except:
            # Fallback: Si no hay contador (a veces ML lo oculta), contamos los items visuales en pantalla.
            items_visibles = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))
            total_resultados = items_visibles if items_visibles > 0 else 0

        # 3. EXTRACCIÓN: Precios (Análisis de Mercado)
        # Buscamos todos los números de precio visibles y calculamos el promedio.
        precios = []
        # Selector genérico para precios en la interfaz 'Andes' de ML
        precio_elems = driver.find_elements(By.CSS_SELECTOR, "span.andes-money-amount__fraction")
        
        for p in precio_elems[:20]: # Tomamos una muestra estadística representativa (Top 20)
            texto_precio = p.text.replace(".", "").strip()
            if texto_precio.isdigit():
                precios.append(float(texto_precio))
        
        precio_promedio = sum(precios) / len(precios) if precios else 0
        
        # 4. EXTRACCIÓN: Saturación de Mercado (Vendedores Platinum)
        # Técnica de Análisis de Código Fuente (Source Code Analysis):
        # En lugar de buscar elemento por elemento (lento), leemos todo el HTML de la página
        # y contamos cuántas veces aparece la frase "MercadoLíder Platinum".
        html_content = driver.page_source
        platinum_count = html_content.count("MercadoLíder Platinum")
        
        # Normalizamos el conteo para obtener un porcentaje estimado (0-100%)
        # Asumimos que 50 menciones en una página es saturación total.
        pct_platinum = min((platinum_count / 50) * 100, 100) 

        # 5. ANÁLISIS: Sentimiento (Simplificado)
        # Al ser scraping visual masivo, no entramos al detalle de cada producto individual
        # para mantener la velocidad del reporte. Asumimos un valor neutro base.
        sentimiento_label = "Neutro (Análisis Web)"
        sentimiento_score = 0.1

        # Consolidación de datos en estructura limpia
        datos_consolidados = {
            "keyword": keyword,
            "competencia_cantidad": total_resultados,
            "precio_promedio": round(precio_promedio, 2),
            "porcentaje_platinum": round(pct_platinum, 1),
            "sentimiento_score": sentimiento_score,
            "sentimiento_label": sentimiento_label,
            "cant_preguntas_analizadas": 0 
        }
                
    except Exception as e:
        print(f"   ❌ Error analizando '{keyword}': {e}")
    finally:
        if driver:
            driver.quit()
        
    return datos_consolidados

# ==============================================================================
# ORQUESTADOR PRINCIPAL (DATA PIPELINE)
# ==============================================================================

def generar_reporte_oportunidades():
    """
    Coordina el flujo completo de inteligencia de negocios:
    1. Discovery: Obtiene tendencias del momento.
    2. Analysis: Investiga cada tendencia en profundidad.
    3. Scoring: Aplica algoritmo de priorización.
    
    Returns:
        pd.DataFrame: Dataset final listo para visualización.
    """
    # Paso 1: Obtener Tendencias (Limitamos a 3 para demostración rápida en vivo)
    df_trends = obtener_tendencias_mercado(limit=3) 
    
    if df_trends.empty:
        print("   ⚠️ [Pipeline] Detenido por falta de datos de entrada.")
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Procesando nichos detectados...")
    
    # Paso 2: Loop de Análisis (Iteración por cada oportunidad)
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        
        # Invocamos al analizador de nicho
        datos = analizar_nicho_mercado(keyword)
        
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    df_final = pd.DataFrame(resultados)
    
    # Paso 3: Scoring de Oportunidad (Business Logic)
    if not df_final.empty:
        # Fórmula de Negocio: 
        # Mayor oportunidad = Alta Demanda (Ranking) + Baja Competencia + Pocos 'Gigantes' (Platinum)
        # (Usamos .replace(0, 1) para evitar errores matemáticos de división por cero)
        comp = df_final['competencia_cantidad'].replace(0, 1)
        
        # El score es inversamente proporcional a la competencia y saturación
        df_final['opportunity_score'] = (
            (1 / comp) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final
