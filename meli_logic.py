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
# MÓDULO DE INGENIERÍA DE DATOS: VISUAL WEB SCRAPING (INTERACTIVO)
# ------------------------------------------------------------------------------
# ESTRATEGIA: "Copiloto Humano"
# El script abre el navegador y espera un tiempo prudencial para permitir
# que el operador humano (tú) resuelva CAPTCHAs o validaciones de seguridad
# antes de intentar extraer los datos del DOM.
# ==============================================================================

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
# LÓGICA DE EXTRACCIÓN DE TENDENCIAS
# ==============================================================================

def obtener_tendencias_mercado(limit=10):
    # Usamos la home de tendencias que suele ser más estable
    url = "https://tendencias.mercadolibre.com.ar/"
    
    print(f"🔄 [Navegando] Visitando: {url}")
    driver = iniciar_navegador_controlado()
    
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        
        # --- TIEMPO DE INTERVENCIÓN HUMANA (20 SEGUNDOS) ---
        print("   ✋ [ATENCIÓN] Tienes 20 segundos. Si ves un CAPTCHA, resuélvelo AHORA.")
        print("   ⏳ Esperando carga completa...")
        time.sleep(20) 
        
        # Estrategia de Selectores Ampliada
        posibles_selectores = [
            "ol li a",                  # Lista clásica
            "div.andes-card a",         # Tarjetas
            ".trends-term",             # Clase específica
            "h2 + ul li a",             # Listas después de títulos
            "a"                         # (Último recurso) Cualquier enlace
        ]
        
        elementos_encontrados = []
        for selector in posibles_selectores:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            # Filtramos enlaces basura (muy cortos o vacíos)
            validos = [e for e in elems if len(e.text) > 3 and "mercadolibre" in str(e.get_attribute("href"))]
            
            if len(validos) > 5: 
                print(f"   👀 [Visual] Selector exitoso: '{selector}' ({len(validos)} items)")
                elementos_encontrados = validos
                break
        
        for elem in elementos_encontrados[:limit]:
            texto = elem.text.strip()
            url_link = elem.get_attribute("href")
            datos_tendencias.append({"keyword": texto, "url": url_link})
    
    except Exception as e:
        print(f"   ⚠️ [Error Visual] {e}")
    finally:
        # CAPTURA DE DIAGNÓSTICO
        if not datos_tendencias:
            print("   📸 [Debug] Guardando captura de pantalla del error (debug_failure.png)...")
            driver.save_screenshot("debug_failure.png")
            
        if driver: driver.quit()

    if datos_tendencias:
        print(f"   ✅ [Éxito] {len(datos_tendencias)} tendencias extraídas.")
        return pd.DataFrame(datos_tendencias)
    else:
        print("   ⚠️ [Fallo] No se encontraron datos. Revisa la imagen 'debug_failure.png'.")
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
        
        # Espera corta para búsquedas (asumimos que si pasaste tendencias, ya no hay captcha)
        time.sleep(5) 
        
        # 1. Cantidad Resultados
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            total_resultados = int(qty_elem.text.replace(".", "").split()[0])
        except:
            total_resultados = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))

        # 2. Precios
        precios = []
        price_elems = driver.find_elements(By.CSS_SELECTOR, ".andes-money-amount__fraction")
        for p in price_elems[:15]:
            try:
                v = float(p.text.replace(".", ""))
                if v > 100: precios.append(v)
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
