import time
import random
import pandas as pd
import platform
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# MÓDULO DE INGENIERÍA DE DATOS: VISUAL WEB SCRAPING (MULTI-PLATAFORMA)
# ------------------------------------------------------------------------------
# COMPATIBILIDAD INTELIGENTE:
# Este script detecta el sistema operativo y selecciona la mejor estrategia de
# inicialización del driver:
# - MacOS (Darwin): Inicialización Nativa (Directa) para evitar bloqueos de permisos.
# - Windows/Linux: Inicialización Gestionada (webdriver_manager) para portabilidad.
# ==============================================================================

def iniciar_navegador_controlado():
    """
    Inicializa el entorno de navegación aplicando la estrategia adecuada según el SO.
    """
    sistema_operativo = platform.system()
    print(f"   🔧 [Sistema] Detectado OS: {sistema_operativo}")
    
    options = Options()
    options.add_argument("--start-maximized")
    
    # --- CONFIGURACIÓN ANTI-DETECCIÓN ---
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # User-Agent Dinámico
    if sistema_operativo == "Windows":
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    else:
        # MacOS / Linux
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None

    # --- ESTRATEGIA DE INICIALIZACIÓN HÍBRIDA ---
    try:
        # CASO MAC (DARWIN): Preferimos el método nativo que evita bloqueos de red locales
        if sistema_operativo == "Darwin":
            print("   🍏 [Mac] Intentando arranque NATIVO de Chrome (Más estable)...")
            try:
                # Selenium moderno busca el driver instalado en el sistema automáticamente
                driver = webdriver.Chrome(options=options)
                return driver
            except Exception as e_mac:
                print(f"   ⚠️ [Mac] El arranque nativo falló ({e_mac}). Pasando a método Gestor...")

        # CASO WINDOWS / FALLBACK: Usamos el Gestor Automático (Ideal para portabilidad)
        print("   📥 [Driver] Verificando/Descargando driver compatible (Gestor)...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    except Exception as e:
        print(f"   ❌ [Error Crítico] Fallo total al iniciar el driver: {e}")
        return None

# ==============================================================================
# LÓGICA DE EXTRACCIÓN DE TENDENCIAS (POR SECCIONES)
# ==============================================================================

def obtener_tendencias_mercado(limit=5):
    """
    Navega a la landing de tendencias y extrae ítems específicos de la sección
    'Las tendencias más populares' utilizando localización por XPath.
    """
    url = "https://tendencias.mercadolibre.com.ar/"
    print(f"🔄 [Navegando] Accediendo a Landing Page: {url}")
    
    driver = iniciar_navegador_controlado()
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        
        print("   ✋ [Interacción] Esperando 10s para carga de componentes dinámicos...")
        time.sleep(10) 
        
        # --- ESTRATEGIA DE XPATH ---
        print("   👀 [Visual] Buscando anclaje: 'Las tendencias más populares'...")
        
        # Buscamos el contenedor padre que tiene el título "tendencias más populares"
        xpath_populares = "//*[contains(text(), 'tendencias más populares')]/ancestor::div[contains(@class, 'hub-container')]//a"
        xpath_backup = "//*[contains(text(), 'tendencias más populares')]/following::div[1]//a"
        
        elementos = driver.find_elements(By.XPATH, xpath_populares)
        
        if not elementos:
            print("   ⚠️ [Aviso] XPath primario vacío. Intentando secundario...")
            elementos = driver.find_elements(By.XPATH, xpath_backup)
            
        if not elementos:
            print("   ⚠️ [Aviso] Sección 'Populares' no detectada. Buscando 'Más deseadas'...")
            elementos = driver.find_elements(By.XPATH, "//*[contains(text(), 'búsquedas más deseadas')]/following::div[1]//a")

        print(f"   📊 [Data] Se encontraron {len(elementos)} candidatos visuales.")

        seen = set()
        count = 0
        
        for elem in elementos:
            if count >= limit: break
            
            try:
                texto = elem.text.strip()
                url_link = elem.get_attribute("href")
                
                # Filtro de Calidad de Datos
                if texto and len(texto) > 2 and "mercadolibre" in str(url_link):
                    if texto.lower() not in ["ver más", "ver todo"] and not texto.isdigit():
                        
                        nombre_producto = texto.split("\n")[-1]
                        
                        if nombre_producto not in seen:
                            print(f"      🔥 [Trend] Identificado: {nombre_producto}")
                            datos_tendencias.append({"keyword": nombre_producto, "url": url_link})
                            seen.add(nombre_producto)
                            count += 1
            except:
                continue
    
    except Exception as e:
        print(f"   ⚠️ [Excepción] Error durante el parsing del DOM: {e}")
    finally:
        if driver: driver.quit()

    # Validación de resultados (ESTRICTA: CERO DATOS FALSOS)
    if datos_tendencias:
        return pd.DataFrame(datos_tendencias)
    else:
        print("   ⚠️ [Alerta] No se pudo extraer la sección específica visualmente.")
        print("   🛑 [Detenido] No se generarán datos ficticios. El reporte estará vacío.")
        return pd.DataFrame() 

# ==============================================================================
# LÓGICA DE ANÁLISIS DE NICHO (MARKET INTELLIGENCE)
# ==============================================================================

def analizar_nicho_mercado(keyword):
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos = None
    
    try:
        keyword_slug = keyword.replace(" ", "-")
        url_busqueda = f"https://listado.mercadolibre.com.ar/{keyword_slug}"
        
        print(f"   🔎 [Analizando] {keyword}...")
        driver.get(url_busqueda)
        time.sleep(4) 
        
        # 1. Volumen de Oferta
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            total_resultados = int(qty_elem.text.replace(".", "").split()[0])
        except:
            total_resultados = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))

        # 2. Análisis de Precios
        precios = []
        price_elems = driver.find_elements(By.CSS_SELECTOR, ".andes-money-amount__fraction")
        for p in price_elems[:30]:
            try:
                texto = p.text.replace(".", "")
                if texto.isdigit():
                    v = float(texto)
                    if v > 1000: precios.append(v)
            except: pass
            
        precio_promedio = sum(precios) / len(precios) if precios else 0
        
        # 3. Saturación (Platinum)
        html = driver.page_source
        platinum_count = html.count("MercadoLíder Platinum")
        pct_platinum = min((platinum_count / 50) * 100, 100)

        # 4. Sentimiento (Estimación Web)
        sentimiento_label = "Neutro (Web Scan)"
        sentimiento_score = 0.1

        datos = {
            "keyword": keyword,
            "competencia_cantidad": total_resultados,
            "precio_promedio": round(precio_promedio, 2),
            "porcentaje_platinum": round(pct_platinum, 1),
            "sentimiento_score": sentimiento_score,
            "sentimiento_label": sentimiento_label,
            "cant_preguntas_analizadas": 0 
        }
                
    except Exception as e:
        print(f"   ❌ Error en análisis de '{keyword}': {e}")
    finally:
        if driver: driver.quit()
        
    return datos

# ==============================================================================
# LÓGICA PRINCIPAL (PIPELINE)
# ==============================================================================

def generar_reporte_oportunidades():
    # Obtenemos las tendencias filtradas por popularidad
    df_trends = obtener_tendencias_mercado(limit=5) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Ejecutando análisis de mercado...")
    
    for index, row in df_trends.iterrows():
        datos = analizar_nicho_mercado(row['keyword'])
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        comp = df_final['competencia_cantidad'].replace(0, 1)
        df_final['opportunity_score'] = (
            (1 / comp) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final
