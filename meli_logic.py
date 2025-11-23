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
# MÓDULO DE INGENIERÍA DE DATOS: ANÁLISIS DE CATEGORÍAS POPULARES
# ------------------------------------------------------------------------------
# ESTRATEGIA TÉCNICA: "Category Sampling" (Muestreo de Categorías)
#
# 1. Discovery: Identificamos visualmente las tarjetas etiquetadas como
#    "MÁS POPULAR" en la home de tendencias. No usamos listas hardcodeadas.
# 2. Drill-Down: Navegamos al listado real de cada tendencia.
# 3. Sampling: En lugar de asumir un solo precio, tomamos una muestra estadística
#    de los primeros N resultados orgánicos para calcular métricas del nicho
#    (Precio Promedio, Saturación de Oferta, etc.).
# ==============================================================================

# Palabras clave para filtrar elementos de navegación que no son productos
BLACKLIST_SISTEMA = [
    "ver más", "ver todo", "historial", "vender", "ayuda", "categorías",
    "ofertas", "tiendas oficiales", "moda", "mercado play", "envíos"
]

def iniciar_navegador_controlado():
    """
    Inicializa el entorno de navegación con configuración cross-platform.
    """
    sistema_operativo = platform.system()
    print(f"   🔧 [Sistema] Detectado OS: {sistema_operativo}")
    
    options = Options()
    options.add_argument("--start-maximized")
    
    # Configuración Anti-Detección para evitar bloqueos
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # User-Agent Dinámico
    if sistema_operativo == "Windows":
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    else:
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        # Intentamos método nativo para Mac primero
        if sistema_operativo == "Darwin":
            try:
                return webdriver.Chrome(options=options)
            except: pass

        # Método gestor universal
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    except Exception as e:
        print(f"   ❌ [Error Crítico] Fallo al iniciar driver: {e}")
        return None

# ==============================================================================
# FASE 1: IDENTIFICACIÓN DE TENDENCIAS POPULARES
# ==============================================================================

def obtener_categorias_populares(limit=5):
    """
    Escanea la sección visual 'Las tendencias más populares' y extrae
    las categorías líderes (ej: Notebook, Celulares).
    """
    url = "https://tendencias.mercadolibre.com.ar/"
    print(f"🔄 [Discovery] Analizando Hub de Tendencias: {url}")
    
    driver = iniciar_navegador_controlado()
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        print("   ✋ [Espera] 8s para renderizado visual...")
        time.sleep(8) 
        
        # ESTRATEGIA VISUAL: Buscar etiquetas "MÁS POPULAR"
        # En lugar de adivinar el contenedor, buscamos el "badge" azul que dice "MÁS POPULAR".
        # Luego subimos al contenedor padre para encontrar el enlace del producto.
        
        print("   👀 [Visual] Buscando etiquetas 'MÁS POPULAR'...")
        
        # XPath: Busca elementos que contengan el texto "MÁS POPULAR"
        # y navega hacia el enlace contenedor o hermano.
        badges_populares = driver.find_elements(By.XPATH, "//*[contains(text(), 'MÁS POPULAR')]")
        
        if not badges_populares:
            print("   ⚠️ [Aviso] No se detectaron badges 'MÁS POPULAR'. Intentando estrategia por sección...")
            # Fallback: Buscar por el título de la sección
            xpath_section = "//*[contains(text(), 'tendencias más populares')]/following::div[1]//a"
            elementos_candidatos = driver.find_elements(By.XPATH, xpath_section)
        else:
            # Si encontramos badges, buscamos el enlace más cercano a cada badge
            elementos_candidatos = []
            for badge in badges_populares:
                try:
                    # Intentamos encontrar el enlace padre o hermano del badge
                    # (La estructura suele ser: Card -> Badge + Imagen + Título(Link))
                    card = badge.find_element(By.XPATH, "./ancestor::div[contains(@class, 'card') or contains(@class, 'module')]//a")
                    elementos_candidatos.append(card)
                except:
                    # Si falla el ancestro estricto, buscamos el siguiente enlace
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
                
                # Limpieza: A veces el texto incluye "1º MÁS POPULAR\nNombre". Limpiamos.
                if "\n" in texto:
                    texto = texto.split("\n")[-1]
                
                if texto and len(texto) > 2 and "mercadolibre" in str(url_link):
                    if not any(x in texto.lower() for x in BLACKLIST_SISTEMA):
                        if texto not in seen:
                            print(f"      🔥 [Tendencia Detectada] Categoría: {texto}")
                            datos_tendencias.append({"keyword": texto, "url": url_link})
                            seen.add(texto)
                            count += 1
            except:
                continue
    
    except Exception as e:
        print(f"   ⚠️ [Excepción Visual] {e}")
    finally:
        if driver: driver.quit()

    if datos_tendencias:
        return pd.DataFrame(datos_tendencias)
    else:
        print("   🛑 [Stop] No se detectaron tendencias populares visualmente. No se usarán datos ficticios.")
        return pd.DataFrame()

# ==============================================================================
# FASE 2: MUESTREO Y ANÁLISIS DE CATEGORÍA
# ==============================================================================

def analizar_categoria(tendencia):
    """
    Navega al listado de una categoría (ej: Notebooks) y toma una muestra
    de los primeros resultados para calcular métricas del nicho.
    """
    keyword = tendencia['keyword']
    url_categoria = tendencia['url']
    
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos_consolidados = None
    
    try:
        print(f"   🔎 [Sampling] Analizando listado de: {keyword}...")
        print(f"      URL: {url_categoria}")
        
        driver.get(url_categoria)
        time.sleep(5) 
        
        # 1. Volumen Total (Cantidad de Resultados)
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            texto_qty = qty_elem.text.replace(".", "").replace(" resultados", "").strip()
            total_resultados = int(texto_qty) if texto_qty.isdigit() else 0
        except:
            # Estimación basada en elementos visibles si no hay contador
            total_resultados = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))

        # 2. Muestreo de Productos (Top 15 orgánicos)
        # No miramos un solo producto, sino el comportamiento del grupo.
        items_muestra = driver.find_elements(By.CLASS_NAME, "ui-search-layout__item")[:15]
        
        precios_muestra = []
        conteo_platinum = 0
        
        for item in items_muestra:
            try:
                # Extraer precio del item
                price_elem = item.find_element(By.CSS_SELECTOR, ".andes-money-amount__fraction")
                precio_texto = price_elem.text.replace(".", "")
                if precio_texto.isdigit():
                    precios_muestra.append(float(precio_texto))
                
                # Verificar si es Platinum (buscando el icono o texto dentro de la tarjeta)
                if "Platinum" in item.get_attribute("innerHTML"):
                    conteo_platinum += 1
            except:
                continue
        
        # Cálculo de Métricas sobre la Muestra
        if precios_muestra:
            precio_promedio = sum(precios_muestra) / len(precios_muestra)
        else:
            precio_promedio = 0
            
        # Saturación: Qué % de la primera página está dominada por Platinum
        if items_muestra:
            pct_platinum = (conteo_platinum / len(items_muestra)) * 100
        else:
            pct_platinum = 0

        # Sentiment: En un barrido de categoría, asumimos neutro
        # (Para detalle real habría que entrar producto por producto, muy lento para demo)
        sentimiento_label = "Neutro (Análisis de Listado)"
        sentimiento_score = 0.1

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
        print(f"   ❌ Error analizando categoría '{keyword}': {e}")
    finally:
        if driver: driver.quit()
        
    return datos_consolidados

# ==============================================================================
# ORQUESTADOR PRINCIPAL
# ==============================================================================

def generar_reporte_oportunidades():
    # 1. Obtener categorías populares reales (Sin hardcoding)
    df_trends = obtener_categorias_populares(limit=5) 
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Iniciando muestreo de categorías...")
    
    for index, row in df_trends.iterrows():
        # 2. Analizar cada categoría detectada
        datos = analizar_categoria(row)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        # Score: Alta demanda (ranking top) + Baja Saturación Platinum
        # (Invertimos el ranking para que 1 sea mejor que 5)
        ranking_weight = (6 - df_final['ranking_tendencia']) * 1000
        platinum_penalty = df_final['porcentaje_platinum'] * 100
        
        df_final['opportunity_score'] = (ranking_weight - platinum_penalty).clip(lower=0)
    
    return df_final
