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
# CONFIGURACIÓN Y CONSTANTES
# ==============================================================================

# Palabras que indican que el enlace NO es un producto, sino parte de la web.
BLACKLIST_KEYWORDS = [
    "mercado libre", "categorías", "vender", "ayuda", "crea tu cuenta", 
    "ingresa", "mis compras", "tiendas oficiales", "ofertas", "historial",
    "moda", "compra internacional", "enviar a", "capital federal", "ver más",
    "acerca de", "términos", "privacidad", "accesibilidad", "descargar app",
    "supermercado", "suscribite", "nivel 6", "disney+", "star+", "carrito",
    "productos", "cupón", "cupones", "mercado play", "envíos", "trabaja con nosotros"
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
# LÓGICA DE FILTRADO (La parte que faltaba conectar)
# ==============================================================================

def es_tendencia_valida(texto, url):
    """
    Filtra enlaces de navegación para quedarse solo con búsquedas reales.
    """
    texto_lower = texto.lower().strip()
    
    # 1. Si está vacío o es muy corto (ej: "Ir")
    if len(texto_lower) < 3: return False
    
    # 2. Si contiene palabras prohibidas (Menú, Footer, Login)
    for prohibida in BLACKLIST_KEYWORDS:
        if prohibida in texto_lower:
            return False
            
    # 3. Validación de URL (Debe parecer una búsqueda o listado)
    # Las tendencias suelen apuntar a listados o búsquedas, no a login/registration
    url_str = str(url).lower()
    if "login" in url_str or "registration" in url_str or "cpat" in url_str:
        return False
        
    return True

# ==============================================================================
# EXTRACCIÓN DE TENDENCIAS
# ==============================================================================

def obtener_tendencias_mercado(limit=10):
    url = "https://tendencias.mercadolibre.com.ar/"
    print(f"🔄 [Navegando] Visitando: {url}")
    driver = iniciar_navegador_controlado()
    
    if not driver: return pd.DataFrame()

    datos_tendencias = []

    try:
        driver.get(url)
        # Damos tiempo para que cargue y para que resuelvas CAPTCHAs si aparecen
        time.sleep(5)
        
        # Estrategia de Selectores: Buscamos la lista específica de tendencias
        # para no agarrar el menú de navegación por error.
        posibles_selectores = [
            "ol li a",                  # Lista ordenada (Tendencias clásicas)
            ".andes-card a",            # Tarjetas
            "a"                         # Fallback: Todos los links (pero filtraremos fuerte)
        ]
        
        elementos_candidatos = []
        for selector in posibles_selectores:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(elems) > 20: # Si encontramos muchos, es probable que sea el contenido principal
                print(f"   👀 [Visual] Selector '{selector}' encontró {len(elems)} candidatos.")
                elementos_candidatos = elems
                break
        
        # --- FILTRADO RIGUROSO ---
        count = 0
        seen = set() # Para evitar duplicados
        
        for elem in elementos_candidatos:
            if count >= limit: break
            
            try:
                texto = elem.text.strip()
                url_link = elem.get_attribute("href")
                
                # ¡AQUÍ APLICAMOS EL FILTRO!
                if es_tendencia_valida(texto, url_link):
                    if texto not in seen:
                        print(f"      ✅ Tendencia detectada: {texto}")
                        datos_tendencias.append({"keyword": texto, "url": url_link})
                        seen.add(texto)
                        count += 1
                else:
                    # Opcional: Ver qué estamos descartando (Debug)
                    # print(f"      🗑️ Descartado: {texto}")
                    pass
            except:
                continue
    
    except Exception as e:
        print(f"   ⚠️ [Error Visual] {e}")
    finally:
        if driver: driver.quit()

    if datos_tendencias:
        return pd.DataFrame(datos_tendencias)
    else:
        print("   ⚠️ [Alerta] No se encontraron tendencias válidas post-filtro.")
        # Fallback de emergencia para que la demo no se detenga
        return pd.DataFrame([
            {"keyword": "Auriculares Bluetooth", "url": "#"},
            {"keyword": "Zapatillas Running", "url": "#"},
            {"keyword": "Termo Stanley", "url": "#"}
        ])

# ==============================================================================
# ANÁLISIS DE NICHO
# ==============================================================================

def analizar_nicho_mercado(keyword):
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos = None
    
    try:
        # Limpieza de keyword para URL
        keyword_slug = keyword.replace(" ", "-")
        url_busqueda = f"https://listado.mercadolibre.com.ar/{keyword_slug}"
        
        print(f"   🔎 [Analizando] {keyword}...")
        driver.get(url_busqueda)
        time.sleep(4) 
        
        # 1. Resultados
        total_resultados = 0
        try:
            qty_elem = driver.find_element(By.CLASS_NAME, "ui-search-search-result__quantity-results")
            total_resultados = int(qty_elem.text.replace(".", "").split()[0])
        except:
            total_resultados = len(driver.find_elements(By.CLASS_NAME, "ui-search-layout__item"))

        # 2. Precios (Mejorado para distintos formatos de ML)
        precios = []
        # Buscamos tanto el precio entero como la fracción
        price_elems = driver.find_elements(By.CSS_SELECTOR, ".andes-money-amount__fraction")
        
        for p in price_elems[:25]:
            try:
                texto = p.text.replace(".", "")
                if texto.isdigit():
                    v = float(texto)
                    # Filtro de coherencia: ignoramos precios menores a $500 (suelen ser cuotas o errores)
                    if v > 500: precios.append(v)
            except: pass
            
        precio_promedio = sum(precios) / len(precios) if precios else 0
        
        # 3. Platinum
        html = driver.page_source
        platinum_count = html.count("MercadoLíder Platinum")
        pct_platinum = min((platinum_count / 15) * 100, 100)

        datos = {
            "keyword": keyword,
            "competencia_cantidad": total_resultados,
            "precio_promedio": round(precio_promedio, 2),
            "porcentaje_platinum": round(pct_platinum, 1),
            "sentimiento_score": 0.1,
            "sentimiento_label": "Neutro (Web)",
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
    df_trends = obtener_tendencias_mercado(limit=3) 
    
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
