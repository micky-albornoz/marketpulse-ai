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
# MÓDULO DE INGENIERÍA DE DATOS: VISUAL WEB SCRAPING (REFINADO)
# ------------------------------------------------------------------------------
# ACTUALIZACIÓN V2: FILTROS DE CALIDAD
# Se han incorporado mecanismos de filtrado para distinguir entre contenido real
# (Tendencias) y elementos estructurales de la web (Menús, Footers, Legales).
# ==============================================================================

# Lista de términos que NO son productos y deben ser ignorados
BLACKLIST_KEYWORDS = [
    "mercado libre", "categorías", "vender", "ayuda", "crea tu cuenta", 
    "ingresa", "mis compras", "tiendas oficiales", "ofertas", "historial",
    "moda", "compra internacional", "enviar a", "capital federal", "ver más",
    "acerca de", "términos", "privacidad", "accesibilidad", "descargar app",
    "supermercado", "suscribite", "nivel 6", "disney+", "star+"
]

def iniciar_navegador_controlado():
    print("   🔧 [Sistema] Inicializando navegador Chrome...")
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"   ❌ [Error Crítico] No se pudo abrir Chrome: {e}")
        return None

# ==============================================================================
# LÓGICA DE EXTRACCIÓN DE TENDENCIAS (CON FILTROS)
# ==============================================================================

def es_tendencia_valida(texto, url):
    """
    Filtra enlaces de navegación, menús y basura.
    Devuelve True solo si parece un producto o categoría real.
    """
    texto_lower = texto.lower().strip()
    
    # 1. Filtro de longitud
    if len(texto_lower) < 4: return False
    
    # 2. Filtro de Blacklist (Palabras prohibidas)
    for prohibida in BLACKLIST_KEYWORDS:
        if prohibida in texto_lower:
            return False
            
    # 3. Filtro de URL (Debe parecer una búsqueda o listado)
    # Las tendencias suelen llevar a '/listado/' o '/tendencias/'
    if "registration" in url or "login" in url or "context" in url:
        return False
        
    return True

def obtener_tendencias_mercado(limit=10):
    url = "https://tendencias.mercadolibre.com.ar/"
    
    print(f"🔄 [Navegando] Visitando: {url}")
    driver = iniciar_navegador_controlado()
    
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        
        # --- TIEMPO DE INTERVENCIÓN HUMANA ---
        print("   ✋ [ATENCIÓN] Tienes 15 segundos. Resuelve CAPTCHAs si aparecen.")
        time.sleep(15) 
        
        # Estrategia: Buscamos TODOS los enlaces y filtramos después
        # Esto es más robusto que adivinar el selector exacto hoy.
        elementos = driver.find_elements(By.TAG_NAME, "a")
        
        print(f"   👀 [Visual] Se encontraron {len(elementos)} enlaces totales en la página.")
        
        # Procesamiento y Filtrado
        count = 0
        for elem in elementos:
            if count >= limit: break
            
            try:
                texto = elem.text.strip()
                url_link = elem.get_attribute("href")
                
                if texto and url_link and es_tendencia_valida(texto, url_link):
                    # Evitar duplicados
                    if not any(d['keyword'] == texto for d in datos_tendencias):
                        print(f"      ✅ Detectada tendencia válida: {texto}")
                        datos_tendencias.append({"keyword": texto, "url": url_link})
                        count += 1
            except:
                continue # Si un elemento falla, seguimos con el siguiente
    
    except Exception as e:
        print(f"   ⚠️ [Error Visual] {e}")
    finally:
        if driver: driver.quit()

    if datos_tendencias:
        print(f"   ✅ [Éxito] {len(datos_tendencias)} tendencias limpias extraídas.")
        return pd.DataFrame(datos_tendencias)
    else:
        print("   ⚠️ [Fallo] No se encontraron datos válidos post-filtro.")
        return pd.DataFrame()

# ==============================================================================
# ANÁLISIS DE NICHO
# ==============================================================================

def analizar_nicho_mercado(keyword):
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos = None
    
    try:
        keyword_slug = keyword.replace(" ", "-")
        url_busqueda = f"https://listado.mercadolibre.com.ar/{keyword_slug}"
        
        print(f"   🔎 [Investigando] {keyword}...")
        driver.get(url_busqueda)
        time.sleep(5) 
        
        # 1. Cantidad Resultados
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            total_resultados = int(qty_elem.text.replace(".", "").split()[0])
        except:
            # Si falla, intentamos buscar el texto "X resultados" en toda la página
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                # Buscamos patrones numéricos seguidos de "resultados"
                import re
                match = re.search(r'([\d\.]+)\s+resultados', body_text)
                if match:
                    total_resultados = int(match.group(1).replace(".", ""))
                else:
                    total_resultados = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))
            except:
                total_resultados = 0

        # 2. Precios
        precios = []
        # Selector actualizado y más genérico para precios
        # Buscamos elementos que contengan el símbolo $ y números
        price_elems = driver.find_elements(By.CSS_SELECTOR, ".andes-money-amount__fraction")
        
        for p in price_elems[:20]:
            try:
                texto = p.text.replace(".", "")
                if texto.isdigit():
                    v = float(texto)
                    if v > 500: precios.append(v) # Filtro de precios bajos (cuotas)
            except: pass
            
        precio_promedio = sum(precios) / len(precios) if precios else 0
        
        # 3. Platinum
        html = driver.page_source
        platinum_count = html.count("MercadoLíder Platinum")
        pct_platinum = min((platinum_count / 15) * 100, 100)

        # 4. Sentiment
        sentimiento_label = "Neutro (Análisis Web)"
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
        print(f"   ❌ Error en {keyword}: {e}")
    finally:
        if driver: driver.quit()
        
    return datos

# ==============================================================================
# PIPELINE PRINCIPAL
# ==============================================================================

def generar_reporte_oportunidades():
    df_trends = obtener_tendencias_mercado(limit=3) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Procesando nichos detectados...")
    
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
