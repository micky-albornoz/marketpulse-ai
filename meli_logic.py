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
# MÓDULO DE INGENIERÍA DE DATOS: AUDITORÍA PROFUNDA (V8)
# ------------------------------------------------------------------------------
# ESTRATEGIA: "FULL DEEP DIVE"
# En lugar de estimar datos desde el listado de búsqueda (que puede ocultar info),
# el script navega individualmente a las fichas de los productos top para
# auditar sus credenciales (Platinum, Tienda Oficial) con certeza absoluta.
# ==============================================================================

BLACKLIST_SISTEMA = [
    "ver más", "ver todo", "historial", "vender", "ayuda", "categorías",
    "ofertas", "tiendas oficiales", "moda", "mercado play", "envíos", "suscribite"
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
# FASE 1: DISCOVERY (Igual que antes)
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
# FASE 2: AUDITORÍA PROFUNDA (DEEP DIVE)
# ==============================================================================

def auditar_producto(driver, url_producto):
    """
    Navega a la ficha del producto y extrae: Precio, Rating y Estatus Platinum.
    """
    try:
        driver.get(url_producto)
        time.sleep(2) # Espera rápida
        
        # 1. Detección de Platinum / Tienda Oficial
        # Buscamos en todo el texto visible de la página para asegurar precisión
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        page_source = driver.page_source.lower()
        
        es_platinum = False
        
        # Criterios estrictos basados en tu observación
        if "mercadolíder platinum" in page_text:
            es_platinum = True
        elif "tienda oficial" in page_text and "ver más datos de" not in page_text: 
            # A veces dice "Ver más datos de Tienda Oficial X" en productos que no lo son, cuidado.
            # Pero generalmente "Tienda oficial" arriba a la derecha es válido.
            es_platinum = True
        elif "platinum" in page_source: # Búsqueda en código fuente (clases CSS o atributos alt)
            es_platinum = True
            
        # 2. Precio
        precio = 0.0
        try:
            # Buscamos el meta tag de precio que es más limpio
            meta_price = driver.find_element(By.CSS_SELECTOR, "meta[itemprop='price']")
            precio = float(meta_price.get_attribute("content"))
        except:
            pass # Si falla, no importa, es secundario
            
        # 3. Rating
        rating = 0.0
        try:
            rating_elem = driver.find_element(By.CLASS_NAME, "ui-pdp-review__rating")
            rating = float(rating_elem.text.strip())
        except: pass

        return {
            "precio": precio,
            "es_platinum": es_platinum,
            "rating": rating
        }

    except Exception as e:
        return None

def analizar_categoria(tendencia):
    keyword = tendencia['keyword']
    url_categoria = tendencia['url']
    
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos_consolidados = None
    
    try:
        print(f"   🔎 [Auditoría] Ingresando a categoría: {keyword}...")
        driver.get(url_categoria)
        time.sleep(4) 
        
        # 1. Volumen Total (Contador)
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            texto_qty = qty_elem.text.replace(".", "").replace(" resultados", "").strip()
            total_resultados = int(texto_qty) if texto_qty.isdigit() else 0
            print(f"      📊 Competencia Total: {total_resultados}")
        except:
            total_resultados = 1000 # Default si no se puede leer

        # 2. Captura de Links para Auditoría (Top 5 Orgánicos)
        # Ignoramos los patrocinados ("Ads") si es posible, aunque ML los mezcla.
        items = driver.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item a.ui-search-link")
        
        # Filtramos duplicados y nos quedamos con los primeros 5 únicos
        urls_a_auditar = []
        seen_urls = set()
        for item in items:
            href = item.get_attribute("href")
            if href and "mercadolibre" in href and href not in seen_urls:
                urls_a_auditar.append(href)
                seen_urls.add(href)
            if len(urls_a_auditar) >= 5: break
            
        print(f"      🕵️ Auditando {len(urls_a_auditar)} productos líderes uno por uno...")
        
        precios = []
        ratings = []
        platinums_encontrados = 0
        
        for url_prod in urls_a_auditar:
            datos_prod = auditar_producto(driver, url_prod)
            if datos_prod:
                if datos_prod['precio'] > 0: precios.append(datos_prod['precio'])
                if datos_prod['rating'] > 0: ratings.append(datos_prod['rating'])
                if datos_prod['es_platinum']: platinums_encontrados += 1
        
        # Consolidación de Métricas
        precio_promedio = sum(precios) / len(precios) if precios else 0
        rating_promedio = sum(ratings) / len(ratings) if ratings else 0
        
        # Cálculo real de saturación
        pct_platinum = (platinums_encontrados / len(urls_a_auditar)) * 100 if urls_a_auditar else 0
        print(f"      🏆 Resultado Auditoría: {pct_platinum}% son Platinum/Oficiales")

        # Label de Sentimiento
        if rating_promedio >= 4.5: sent_label = "Excelente (4.5+)"
        elif rating_promedio >= 4.0: sent_label = "Bueno (4.0+)"
        elif rating_promedio > 0: sent_label = "Regular"
        else: sent_label = "Sin Datos"

        datos_consolidados = {
            "keyword": keyword,
            "competencia_cantidad": total_resultados,
            "precio_promedio": round(precio_promedio, 2),
            "porcentaje_platinum": round(pct_platinum, 1),
            "sentimiento_score": round(rating_promedio, 1),
            "sentimiento_label": sent_label,
            "cant_preguntas_analizadas": len(urls_a_auditar)
        }
                
    except Exception as e:
        print(f"   ❌ Error en auditoría: {e}")
    finally:
        if driver: driver.quit()
        
    return datos_consolidados

# ==============================================================================
# SCORING
# ==============================================================================

def calcular_opportunity_score(row):
    comp = row['competencia_cantidad']
    
    # Lógica de Scoring ajustada
    if comp < 1000: score_comp = 100
    elif comp < 10000: score_comp = 70
    elif comp < 50000: score_comp = 40
    else: score_comp = 10
    
    # Si hay mucho platinum, es difícil entrar -> Score baja
    score_plat = 100 - row['porcentaje_platinum']
    
    score_rank = (6 - row['ranking_tendencia']) * 20
    
    final_score = (score_comp * 0.25) + (score_plat * 0.55) + (score_rank * 0.2)
    return round(final_score, 1)

def generar_reporte_oportunidades():
    df_trends = obtener_categorias_populares(limit=5) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Iniciando auditoría de mercado...")
    
    for index, row in df_trends.iterrows():
        datos = analizar_categoria(row)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        df_final['opportunity_score'] = df_final.apply(calcular_opportunity_score, axis=1)
    
    return df_final
