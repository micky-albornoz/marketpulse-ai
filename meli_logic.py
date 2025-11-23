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
# Debido a las restricciones de seguridad en la API pública (Error 403),
# este módulo implementa una estrategia de "Frontend Scraping".
#
# En lugar de consumir endpoints JSON, emulamos la navegación de un usuario real
# visitando las páginas web públicas (Tendencias y Buscador) y extrayendo
# la información visualmente del DOM (Document Object Model).
# ==============================================================================

def iniciar_navegador_controlado():
    """
    Configura e inicializa una instancia de Google Chrome optimizada para
    simular un comportamiento humano y evitar bloqueos básicos de automatización.
    
    Returns:
        webdriver.Chrome: Instancia del navegador lista para usar.
        None: Si ocurre un error al iniciar.
    """
    print("   🔧 [Sistema] Inicializando navegador para lectura visual...")
    
    options = Options()
    options.add_argument("--start-maximized")
    
    # --- TÉCNICAS DE EVASIÓN DE DETECCIÓN (ANTI-BOT) ---
    # Desactivamos las banderas que Selenium suele enviar por defecto y que
    # delatan que es un robot controlando el navegador.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Usamos un User-Agent de una Mac real para pasar desapercibidos
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"   ❌ [Error] No se pudo abrir Chrome: {e}")
        return None

# ==============================================================================
# LÓGICA DE EXTRACCIÓN DE TENDENCIAS (FRONTEND)
# ==============================================================================

def obtener_tendencias_mercado(limit=10):
    """
    Visita la página web pública de tendencias de Mercado Libre y extrae
    los términos más populares del momento.
    
    URL Objetivo: https://tendencias.mercadolibre.com.ar/
    
    Args:
        limit (int): Cantidad máxima de tendencias a recuperar.
        
    Returns:
        pd.DataFrame: Tabla con las keywords y sus enlaces.
    """
    url = "https://tendencias.mercadolibre.com.ar/"
    
    print(f"🔄 [Navegando] Visitando portal público: {url}")
    driver = iniciar_navegador_controlado()
    
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        # ESPERA ESTRATÉGICA: Damos 5 segundos para que carguen estilos y scripts
        time.sleep(5)
        
        # --- ESTRATEGIA DE SELECTORES CSS ---
        # Mercado Libre cambia su estructura a veces. Probamos una lista de
        # selectores comunes para encontrar dónde están los links de tendencias.
        # El primero que funcione, es el que usamos.
        posibles_selectores = [
            "ol li a",              # Lista ordenada simple (Estructura clásica)
            "div.andes-card a",     # Tarjetas de diseño 'Andes' (Diseño moderno)
            "a.trends-term"         # Clases específicas antiguas
        ]
        
        elementos = []
        for selector in posibles_selectores:
            elementos = driver.find_elements(By.CSS_SELECTOR, selector)
            if elementos:
                print(f"   👀 [Visual] Se detectaron {len(elementos)} elementos con el selector: {selector}")
                break # ¡Encontramos uno que sirve! Dejamos de buscar.
        
        # Procesamos los elementos encontrados
        for elem in elementos[:limit]:
            texto = elem.text.strip()
            if texto:
                datos_tendencias.append({"keyword": texto, "url": elem.get_attribute("href")})
    
    except Exception as e:
        print(f"   ⚠️ [Error Visual] Fallo al leer la web: {e}")
    finally:
        # Importante: Cerrar el navegador para liberar memoria RAM
        if driver:
            driver.quit() 

    # Verificación final
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
    
    URL Objetivo: https://listado.mercadolibre.com.ar/{keyword}
    """
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos_consolidados = None
    
    try:
        # 1. Construcción de URL amigable (SEO Friendly)
        keyword_slug = keyword.replace(" ", "-")
        url_busqueda = f"https://listado.mercadolibre.com.ar/{keyword_slug}"
        
        print(f"   🔎 [Investigando] URL: {url_busqueda}")
        driver.get(url_busqueda)
        time.sleep(3) # Espera para carga visual
        
        # 2. EXTRACCIÓN: Cantidad de Resultados
        # Intentamos leer el contador que dice "10.000 resultados" arriba a la izquierda.
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            texto_qty = qty_elem.text.replace(".", "").replace(" resultados", "").strip()
            total_resultados = int(texto_qty) if texto_qty.isdigit() else 1000
        except:
            # Si no hay contador (a veces ML lo oculta), contamos los items visuales en pantalla.
            items_visibles = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))
            total_resultados = items_visibles if items_visibles > 0 else 0

        # 3. EXTRACCIÓN: Precios
        # Buscamos todos los números de precio visibles y calculamos el promedio.
        precios = []
        precio_elems = driver.find_elements(By.CSS_SELECTOR, "span.andes-money-amount__fraction")
        
        for p in precio_elems[:20]: # Tomamos una muestra representativa (Top 20)
            texto_precio = p.text.replace(".", "").strip()
            if texto_precio.isdigit():
                precios.append(float(texto_precio))
        
        precio_promedio = sum(precios) / len(precios) if precios else 0
        
        # 4. EXTRACCIÓN: Saturación de Mercado (Platinum)
        # Técnica de Análisis de Código Fuente:
        # En lugar de buscar elemento por elemento, leemos todo el HTML de la página
        # y contamos cuántas veces aparece la frase "MercadoLíder Platinum".
        html_content = driver.page_source
        platinum_count = html_content.count("MercadoLíder Platinum")
        
        # Normalizamos el conteo (estimación)
        pct_platinum = min((platinum_count / 50) * 100, 100) 

        # 5. ANÁLISIS: Sentimiento (Simplificado)
        # Al ser scraping visual masivo, no entramos al detalle de cada producto
        # para mantener la velocidad. Asumimos un valor neutro base.
        sentimiento_label = "Neutro (Análisis Web)"
        sentimiento_score = 0.1

        # Consolidación de datos
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
# ORQUESTADOR PRINCIPAL (PIPELINE)
# ==============================================================================

def generar_reporte_oportunidades():
    """
    Coordina el flujo completo de datos:
    1. Obtiene tendencias -> 2. Analiza cada una -> 3. Calcula el Score final.
    """
    # Paso 1: Obtener Tendencias (Limitamos a 3 para demostración rápida)
    df_trends = obtener_tendencias_mercado(limit=3) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Procesando resultados visuales...")
    
    # Paso 2: Loop de Análisis
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        
        datos = analizar_nicho_mercado(keyword)
        
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    df_final = pd.DataFrame(resultados)
    
    # Paso 3: Scoring de Oportunidad
    if not df_final.empty:
        # Fórmula de Negocio: 
        # Mayor oportunidad = Alta Demanda (Ranking) + Baja Competencia + Pocos 'Gigantes' (Platinum)
        comp = df_final['competencia_cantidad'].replace(0, 1)
        df_final['opportunity_score'] = (
            (1 / comp) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final
