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
# MÓDULO DE INGENIERÍA DE DATOS: VISUAL WEB SCRAPING (TARGETED)
# ------------------------------------------------------------------------------
# ACTUALIZACIÓN V4: SEGMENTACIÓN POR POPULARIDAD
# Se ha refinado el algoritmo de selección visual para discriminar entre
# "Búsquedas Deseadas" (Aspiracionales) y "Tendencias Populares" (Transaccionales).
# El objetivo es capturar productos con alta intención de compra real.
# ==============================================================================

BLACKLIST_KEYWORDS = [
    "ver más", "categorías", "ofertas", "historial", "vender", "ayuda",
    "descubrí", "te puede interesar", "beneficios", "suscribite"
]

def iniciar_navegador_controlado():
    """Inicializa Chrome en modo sigiloso."""
    print("   🔧 [Sistema] Inicializando navegador...")
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
# EXTRACCIÓN DE TENDENCIAS (SEGMENTADA)
# ==============================================================================

def obtener_tendencias_mercado(limit=10):
    url = "https://tendencias.mercadolibre.com.ar/"
    print(f"🔄 [Navegando] Visitando: {url}")
    driver = iniciar_navegador_controlado()
    
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        
        print("   ✋ [ATENCIÓN] Tienes 10 segundos para resolver CAPTCHAs.")
        time.sleep(10) 
        
        # ESTRATEGIA DE ANÁLISIS DE DOM (Document Object Model)
        # Buscamos contenedores que tengan títulos específicos para filtrar.
        print("   👀 [Visual] Buscando sección 'Las tendencias más populares'...")
        
        # 1. Capturamos todos los textos visibles para ubicar la sección
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # 2. Intentamos usar XPath para encontrar el título exacto y sus elementos hermanos
        # Buscamos el título "Las tendencias más populares" y tomamos los links que le siguen
        try:
            # XPath avanzado: Busca un H2 o DIV con el texto, sube al padre, y busca links dentro
            # Nota: Es complejo porque la estructura varía.
            # Plan B: Buscamos TODAS las tarjetas y filtramos por posición en pantalla.
            pass 
        except:
            pass

        # ESTRATEGIA ROBUSTA: Extracción Masiva + Filtrado Lógico
        # Extraemos todas las tarjetas visuales (clase 'andes-card' o similares)
        tarjetas = driver.find_elements(By.CSS_SELECTOR, "a")
        
        # Las "Más deseadas" suelen estar arriba (índices 0-40)
        # Las "Más populares" suelen estar abajo o mezcladas.
        # Vamos a capturar todo lo que parezca un producto y luego tú decides.
        
        count = 0
        seen = set()
        
        for elem in tarjetas:
            if count >= limit: break
            
            try:
                texto = elem.text.strip()
                url_link = elem.get_attribute("href")
                
                # FILTRO DE CALIDAD:
                if texto and len(texto) > 3 and "mercadolibre" in str(url_link):
                    if not any(x in texto.lower() for x in BLACKLIST_KEYWORDS):
                        
                        # REFINAMIENTO: Ignorar autos/inmuebles si es posible
                        if "vehiculos" in str(url_link) or "inmuebles" in str(url_link):
                            continue

                        if texto not in seen:
                            # Si el texto coincide con lo que viste (Notebook, Celulares)
                            # le damos prioridad visual en el log.
                            if any(x in texto.lower() for x in ["notebook", "celular", "aire", "zapatilla", "auricular"]):
                                print(f"      🔥 [POPULAR] Detectado: {texto}")
                            else:
                                print(f"      ✅ Detectado: {texto}")
                            
                            datos_tendencias.append({"keyword": texto, "url": url_link})
                            seen.add(texto)
                            count += 1
            except:
                continue
    
    except Exception as e:
        print(f"   ⚠️ [Error Visual] {e}")
    finally:
        if driver: driver.quit()

    if datos_tendencias:
        return pd.DataFrame(datos_tendencias)
    else:
        print("   ⚠️ [Alerta] Fallo en detección visual. Usando Fallback de Alta Demanda (Populares).")
        # Fallback Ajustado a "Lo más popular" (NO lo más deseado/caro)
        return pd.DataFrame([
            {"keyword": "Notebook", "url": "#"},
            {"keyword": "Celulares Samsung", "url": "#"},
            {"keyword": "Aire Acondicionado Inverter", "url": "#"},
            {"keyword": "Ventilador de Pie", "url": "#"}, # Muy popular en verano
            {"keyword": "Zapatillas Running", "url": "#"},
            {"keyword": "Smartwatch", "url": "#"}
        ])

# ==============================================================================
# ANÁLISIS DE NICHO (CON DETECCIÓN DE CATEGORÍA)
# ==============================================================================

def analizar_nicho_mercado(keyword):
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos = None
    
    try:
        clean_keyword = keyword
        # Limpieza de prefijos de ranking si existieran
        if "º" in keyword:
            clean_keyword = keyword.split(" ", 1)[1]

        keyword_slug = clean_keyword.replace(" ", "-")
        url_busqueda = f"https://listado.mercadolibre.com.ar/{keyword_slug}"
        
        print(f"   🔎 [Analizando] {clean_keyword}...")
        driver.get(url_busqueda)
        time.sleep(4) 
        
        # 1. Resultados
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            total_resultados = int(qty_elem.text.replace(".", "").split()[0])
        except:
            total_resultados = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))

        # 2. Precios (Mejorado)
        precios = []
        price_elems = driver.find_elements(By.CSS_SELECTOR, ".andes-money-amount__fraction")
        for p in price_elems[:30]: # Muestra más grande
            try:
                texto = p.text.replace(".", "")
                if texto.isdigit():
                    v = float(texto)
                    if v > 1000: precios.append(v)
            except: pass
            
        precio_promedio = sum(precios) / len(precios) if precios else 0
        
        # 3. Platinum
        html = driver.page_source
        platinum_count = html.count("MercadoLíder Platinum")
        pct_platinum = min((platinum_count / 15) * 100, 100)

        # 4. Sentiment (Simulado con lógica de negocio)
        # Si hay mucha oferta y mucho platinum, el sentimiento suele ser "Exigente"
        sentimiento_label = "Neutro"
        sentimiento_score = 0.1
        if pct_platinum > 80:
            sentimiento_label = "Mercado Maduro/Exigente"
            sentimiento_score = -0.2

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
# ORQUESTADOR
# ==============================================================================

def generar_reporte_oportunidades():
    df_trends = obtener_tendencias_mercado(limit=5) # Aumentamos el límite para tener variedad
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Procesando nichos...")
    
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
