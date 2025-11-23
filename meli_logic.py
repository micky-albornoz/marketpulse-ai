import time
import random
import pandas as pd
import platform
import math
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# MÓDULO DE INGENIERÍA DE DATOS: ANÁLISIS PROFUNDO (V6)
# ------------------------------------------------------------------------------
# CORRECCIONES:
# 1. Detección Platinum mediante inspección de HTML (innerHTML) para capturar
#    íconos y etiquetas no textuales.
# 2. Clarificación de extracción de "Total Resultados" (Lectura de contador).
# ==============================================================================

BLACKLIST_SISTEMA = [
    "ver más", "ver todo", "historial", "vender", "ayuda", "categorías",
    "ofertas", "tiendas oficiales", "moda", "mercado play", "envíos"
]

def iniciar_navegador_controlado():
    sistema_operativo = platform.system()
    print(f"   🔧 [Sistema] Detectado OS: {sistema_operativo}")
    
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    if sistema_operativo == "Windows":
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    else:
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        if sistema_operativo == "Darwin":
            try:
                return webdriver.Chrome(options=options)
            except: pass
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"   ❌ [Error Crítico] Fallo al iniciar driver: {e}")
        return None

# ==============================================================================
# FASE 1: DISCOVERY
# ==============================================================================

def obtener_categorias_populares(limit=5):
    url = "https://tendencias.mercadolibre.com.ar/"
    print(f"🔄 [Discovery] Analizando Hub de Tendencias: {url}")
    
    driver = iniciar_navegador_controlado()
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        print("   ✋ [Espera] 8s para renderizado visual...")
        time.sleep(8) 
        
        print("   👀 [Visual] Buscando etiquetas 'MÁS POPULAR'...")
        badges_populares = driver.find_elements(By.XPATH, "//*[contains(text(), 'MÁS POPULAR')]")
        
        elementos_candidatos = []
        if not badges_populares:
            # Fallback a búsqueda por sección si no hay badges
            xpath_section = "//*[contains(text(), 'tendencias más populares')]/following::div[1]//a"
            elementos_candidatos = driver.find_elements(By.XPATH, xpath_section)
        else:
            for badge in badges_populares:
                try:
                    card = badge.find_element(By.XPATH, "./ancestor::div[contains(@class, 'card') or contains(@class, 'module')]//a")
                    elementos_candidatos.append(card)
                except:
                    try:
                        link = badge.find_element(By.XPATH, "./following::a[1]")
                        elementos_candidatos.append(link)
                    except: pass

        seen = set()
        count = 0
        
        for elem in elementos_candidatos:
            if count >= limit: break
            try:
                texto = elem.text.strip()
                url_link = elem.get_attribute("href")
                if "\n" in texto: texto = texto.split("\n")[-1]
                
                if texto and len(texto) > 2 and "mercadolibre" in str(url_link):
                    if not any(x in texto.lower() for x in BLACKLIST_SISTEMA):
                        if texto not in seen:
                            print(f"      🔥 [Tendencia] {texto}")
                            datos_tendencias.append({"keyword": texto, "url": url_link})
                            seen.add(texto)
                            count += 1
            except: continue
    except Exception as e:
        print(f"   ⚠️ [Excepción Visual] {e}")
    finally:
        if driver: driver.quit()

    if datos_tendencias:
        return pd.DataFrame(datos_tendencias)
    else:
        return pd.DataFrame()

# ==============================================================================
# FASE 2: ANÁLISIS PROFUNDO (DEEP DIVE)
# ==============================================================================

def obtener_detalle_producto(driver, url_producto):
    """Entra a la ficha del producto para leer el rating real."""
    print(f"      👉 [Deep Dive] Entrando al producto líder...")
    try:
        driver.get(url_producto)
        time.sleep(3)
        try:
            rating_elem = driver.find_element(By.CLASS_NAME, "ui-pdp-review__rating")
            rating = float(rating_elem.text.strip())
            print(f"         ⭐ Rating encontrado: {rating}")
            return rating
        except:
            return 0.0
    except:
        return 0.0

def analizar_categoria(tendencia):
    keyword = tendencia['keyword']
    url_categoria = tendencia['url']
    
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos_consolidados = None
    
    try:
        print(f"   🔎 [Sampling] Analizando listado de: {keyword}...")
        driver.get(url_categoria)
        time.sleep(5) 
        
        # 1. Volumen Total (Lectura del Contador)
        total_resultados = 0
        try:
            # Buscamos el texto que dice "XX.XXX resultados"
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            texto_qty = qty_elem.text.replace(".", "").replace(" resultados", "").strip()
            total_resultados = int(texto_qty) if texto_qty.isdigit() else 0
            print(f"      📊 Contador de Competencia Leído: {total_resultados}")
        except:
            total_resultados = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))

        # 2. Muestreo de Productos (Top 15)
        items_muestra = driver.find_elements(By.CLASS_NAME, "ui-search-layout__item")[:15]
        
        precios_muestra = []
        conteo_platinum = 0
        url_primer_producto = None
        
        for i, item in enumerate(items_muestra):
            try:
                # A. Precio
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, ".andes-money-amount__fraction")
                    precio_texto = price_elem.text.replace(".", "")
                    if precio_texto.isdigit():
                        precios_muestra.append(float(precio_texto))
                except: pass
                
                # B. PLATINUM (LÓGICA CORREGIDA)
                # Buscamos en el HTML interno, no solo en el texto visible.
                # Esto detecta clases, atributos alt e íconos ocultos.
                html_tarjeta = item.get_attribute("innerHTML")
                
                # Buscamos variaciones comunes de la marca Platinum
                if "platinum" in html_tarjeta.lower() or "brand_filter" in html_tarjeta:
                    conteo_platinum += 1
                
                # C. URL para Deep Dive
                if i == 0:
                    try:
                        link_elem = item.find_element(By.TAG_NAME, "a")
                        url_primer_producto = link_elem.get_attribute("href")
                    except: pass
                    
            except: continue
        
        # Métricas
        precio_promedio = sum(precios_muestra) / len(precios_muestra) if precios_muestra else 0
        pct_platinum = (conteo_platinum / len(items_muestra)) * 100 if items_muestra else 0
        
        print(f"      🏆 Platinum Detectados en muestra: {conteo_platinum}/{len(items_muestra)} ({pct_platinum}%)")

        # 3. Sentiment Real
        rating_real = 0.0
        if url_primer_producto:
            rating_real = obtener_detalle_producto(driver, url_primer_producto)
            
        if rating_real >= 4.5: sent_label = "Excelente (4.5+)"
        elif rating_real >= 4.0: sent_label = "Bueno (4.0+)"
        elif rating_real > 0: sent_label = "Regular"
        else: sent_label = "Sin Datos"

        datos_consolidados = {
            "keyword": keyword,
            "competencia_cantidad": total_resultados,
            "precio_promedio": round(precio_promedio, 2),
            "porcentaje_platinum": round(pct_platinum, 1),
            "sentimiento_score": rating_real,
            "sentimiento_label": sent_label,
            "cant_preguntas_analizadas": 1 
        }
                
    except Exception as e:
        print(f"   ❌ Error analizando categoría '{keyword}': {e}")
    finally:
        if driver: driver.quit()
        
    return datos_consolidados

# ==============================================================================
# SCORING
# ==============================================================================

def calcular_opportunity_score(row):
    # Normalización para que el score sea legible (0-100)
    
    # Competencia: Si hay >50.000 items, es muy difícil (0 puntos)
    # Si hay <1.000, es fácil (100 puntos)
    comp = row['competencia_cantidad']
    score_comp = max(0, 100 - (comp / 500)) # Decae rápido con mucha competencia
    
    # Platinum: Si hay 100% platinum, score es 0.
    score_plat = 100 - row['porcentaje_platinum']
    
    # Ranking: 1º lugar vale más
    score_rank = (6 - row['ranking_tendencia']) * 20
    
    # Ponderación: Le damos mucho peso a que NO haya Platinum (oportunidad para entrar)
    final_score = (score_comp * 0.2) + (score_plat * 0.6) + (score_rank * 0.2)
    return round(final_score, 1)

def generar_reporte_oportunidades():
    df_trends = obtener_categorias_populares(limit=5) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Iniciando muestreo de categorías...")
    
    for index, row in df_trends.iterrows():
        datos = analizar_categoria(row)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        df_final['opportunity_score'] = df_final.apply(calcular_opportunity_score, axis=1)
    
    return df_final
