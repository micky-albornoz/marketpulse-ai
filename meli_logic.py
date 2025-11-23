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
# MÓDULO DE INGENIERÍA DE DATOS: ANÁLISIS PROFUNDO (DEEP DIVE)
# ------------------------------------------------------------------------------
# CAMBIOS MAYORES V5:
# 1. PLATINUM: Detección iterativa ítem por ítem (más precisa que el HTML global).
# 2. SENTIMIENTO: Navegación real a la ficha del producto líder para leer estrellas.
# 3. SCORING: Normalización de métricas para un puntaje 0-100 legible.
# ==============================================================================

BLACKLIST_SISTEMA = [
    "ver más", "ver todo", "historial", "vender", "ayuda", "categorías",
    "ofertas", "tiendas oficiales", "moda", "mercado play", "envíos"
]

def iniciar_navegador_controlado():
    """Inicializa el navegador con configuración anti-bloqueo."""
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
# FASE 1: DISCOVERY (Igual que antes, funciona bien)
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
        
        if not badges_populares:
            print("   ⚠️ [Aviso] No se detectaron badges. Intentando fallback por sección...")
            xpath_section = "//*[contains(text(), 'tendencias más populares')]/following::div[1]//a"
            elementos_candidatos = driver.find_elements(By.XPATH, xpath_section)
        else:
            elementos_candidatos = []
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
        print("   🛑 [Stop] No se detectaron tendencias.")
        return pd.DataFrame()

# ==============================================================================
# FASE 2: ANÁLISIS PROFUNDO (DEEP DIVE)
# ==============================================================================

def obtener_detalle_producto(driver, url_producto):
    """
    Entra a la ficha del producto para leer el rating real (Estrellas).
    """
    print(f"      👉 [Deep Dive] Entrando al producto líder...")
    try:
        driver.get(url_producto)
        time.sleep(3)
        
        # Buscamos el rating (número grande, ej: "4.7")
        # Selectores comunes de rating en ficha de producto
        try:
            rating_elem = driver.find_element(By.CLASS_NAME, "ui-pdp-review__rating")
            rating = float(rating_elem.text.strip())
            print(f"         ⭐ Rating encontrado: {rating}")
            return rating
        except:
            print("         ⚠️ No se encontró rating visible.")
            return 0.0
    except Exception as e:
        print(f"         ❌ Error leyendo producto: {e}")
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
        
        # 1. Volumen Total
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            texto_qty = qty_elem.text.replace(".", "").replace(" resultados", "").strip()
            total_resultados = int(texto_qty) if texto_qty.isdigit() else 0
        except:
            total_resultados = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))

        # 2. Muestreo de Productos (Top 15)
        items_muestra = driver.find_elements(By.CLASS_NAME, "ui-search-layout__item")[:15]
        
        precios_muestra = []
        conteo_platinum = 0
        url_primer_producto = None
        
        print(f"      📊 Analizando muestra de {len(items_muestra)} items...")
        
        for i, item in enumerate(items_muestra):
            try:
                texto_item = item.text  # Leemos TODO el texto de la tarjeta
                
                # A. Precio
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, ".andes-money-amount__fraction")
                    precio_texto = price_elem.text.replace(".", "")
                    if precio_texto.isdigit():
                        precios_muestra.append(float(precio_texto))
                except: pass
                
                # B. Platinum (Búsqueda textual directa en la tarjeta)
                # Esto es más robusto que buscar clases ocultas
                if "Platinum" in texto_item or "Promocionado" in texto_item: # Promocionado suele ser de grandes vendedores
                    conteo_platinum += 1
                
                # C. Guardamos URL del primer orgánico para Deep Dive
                if i == 0: # El primero de la lista
                    try:
                        link_elem = item.find_element(By.TAG_NAME, "a")
                        url_primer_producto = link_elem.get_attribute("href")
                    except: pass
                    
            except: continue
        
        # Cálculo de Métricas
        precio_promedio = sum(precios_muestra) / len(precios_muestra) if precios_muestra else 0
        
        # Saturación Real
        pct_platinum = (conteo_platinum / len(items_muestra)) * 100 if items_muestra else 0
        print(f"      🏆 Saturación Platinum detectada: {pct_platinum}%")

        # 3. Sentiment Real (Deep Dive)
        rating_real = 0.0
        if url_primer_producto:
            rating_real = obtener_detalle_producto(driver, url_primer_producto)
            
        # Mapeo de Rating a Sentiment Label
        if rating_real >= 4.5: sent_label = "Excelente (4.5+)"
        elif rating_real >= 4.0: sent_label = "Bueno (4.0+)"
        elif rating_real > 0: sent_label = "Regular"
        else: sent_label = "Sin Datos"

        datos_consolidados = {
            "keyword": keyword,
            "competencia_cantidad": total_resultados,
            "precio_promedio": round(precio_promedio, 2),
            "porcentaje_platinum": round(pct_platinum, 1),
            "sentimiento_score": rating_real, # Guardamos el rating real (ej: 4.7)
            "sentimiento_label": sent_label,
            "cant_preguntas_analizadas": 1 
        }
                
    except Exception as e:
        print(f"   ❌ Error analizando categoría '{keyword}': {e}")
    finally:
        if driver: driver.quit()
        
    return datos_consolidados

# ==============================================================================
# SCORING Y ORQUESTACIÓN
# ==============================================================================

def calcular_opportunity_score(row):
    """
    Calcula un puntaje de 0 a 100 basado en métricas clave.
    """
    # 1. Factor Competencia (Inverso): Menos es mejor.
    # Si hay > 10,000 items, el factor baja.
    comp = row['competencia_cantidad']
    if comp == 0: score_comp = 50
    else: score_comp = max(0, 100 - (math.log10(comp) * 20)) # Escala logarítmica para suavizar números grandes
    
    # 2. Factor Barrera (Platinum): Menos es mejor.
    score_plat = 100 - row['porcentaje_platinum']
    
    # 3. Factor Demanda (Ranking): Menor ranking (1º) es mejor.
    score_rank = (6 - row['ranking_tendencia']) * 20 # 1º=100, 5º=20
    
    # Promedio ponderado
    final_score = (score_comp * 0.3) + (score_plat * 0.4) + (score_rank * 0.3)
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
        # Aplicamos el nuevo algoritmo de scoring
        df_final['opportunity_score'] = df_final.apply(calcular_opportunity_score, axis=1)
    
    return df_final
