import time
import json
import pandas as pd
from textblob import TextBlob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ==============================================================================
# MÓDULO DE INGENIERÍA DE DATOS: EXTRACCIÓN Y ANÁLISIS
# ------------------------------------------------------------------------------
# Este módulo gestiona la interacción automatizada con fuentes de datos externas.
# Utiliza un motor de navegación controlado (Selenium WebDriver) para garantizar
# la correcta interpretación de sitios web dinámicos (SPA - Single Page Applications)
# y asegurar la obtención fidedigna de métricas de mercado en tiempo real.
# ==============================================================================

def iniciar_navegador_controlado():
    """
    Configura e inicializa una instancia del navegador Chrome para la extracción de datos.
    
    Se aplican configuraciones específicas para:
    1. Maximizar el área de visualización (Viewport).
    2. Asegurar compatibilidad con entornos de ejecución modernos (MacOS/Linux/Windows).
    3. Limpiar indicadores de automatización para obtener una experiencia de usuario estándar.
    
    Returns:
        webdriver.Chrome: Instancia activa del navegador lista para operar.
        None: Si ocurre un error crítico durante la inicialización.
    """
    print("   🔧 [Sistema] Inicializando motor de navegación (Chrome WebDriver)...")
    
    options = Options()
    options.add_argument("--start-maximized")
    
    # --- CONFIGURACIÓN DE ESTABILIDAD Y COMPATIBILIDAD ---
    # Estas banderas son necesarias para que Chrome opere fluidamente en entornos
    # con gestión de memoria restrictiva o sin entorno gráfico (aunque aquí usamos GUI).
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # --- NORMALIZACIÓN DEL ENTORNO ---
    # Eliminamos banderas que alteran el comportamiento estándar del navegador
    # para asegurar que la página se renderice tal como la vería un usuario final.
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        # Selenium 4+ gestiona automáticamente los drivers binarios necesarios.
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"   ❌ [Error Crítico] No se pudo iniciar el entorno de navegación: {e}")
        return None

def ejecutar_solicitud_json(driver, url):
    """
    Realiza una navegación a la URL especificada y extrae el payload de datos (JSON)
    renderizado en el cuerpo del documento.

    Args:
        driver (webdriver): La instancia activa del navegador.
        url (str): El endpoint o dirección web a consultar.

    Returns:
        dict: Datos parseados en formato diccionario si la extracción es exitosa.
        None: Si ocurre un error de red o de parseo.
    """
    print(f"   🤖 [Solicitud] Navegando a endpoint: {url}")
    try:
        driver.get(url)
        
        # TIEMPO DE ESPERA DE RENDERIZADO (WAIT TIME)
        # Pausa técnica de 3 segundos para permitir la carga asíncrona de recursos
        # y asegurar que el DOM esté completamente disponible antes de leer.
        time.sleep(3) 
        
        # Extracción del contenido textual del elemento <body>
        content = driver.find_element(By.TAG_NAME, "body").text
        return json.loads(content)
    except Exception as e:
        print(f"   ⚠️ [Excepción] Fallo en la lectura de datos: {e}")
        return None

# ==============================================================================
# LÓGICA DE EXTRACCIÓN DE TENDENCIAS (DATA SOURCING)
# ==============================================================================

def obtener_tendencias_mercado(limit=10):
    """
    Consulta la fuente de datos de tendencias para identificar los términos
    de mayor interés actual en el mercado (High Intent Keywords).

    Args:
        limit (int): Cantidad máxima de tendencias a retornar.

    Returns:
        pd.DataFrame: Tabla con las palabras clave y sus metadatos.
    """
    url = "https://api.mercadolibre.com/trends/MLA"
    
    print("🔄 [Proceso] Iniciando sesión de extracción de Tendencias...")
    driver = iniciar_navegador_controlado()
    
    if not driver: 
        return pd.DataFrame() # Retorno vacío ante fallo de infraestructura

    try:
        data = ejecutar_solicitud_json(driver, url)
        if data:
            print(f"   ✅ [Éxito] Dataset descargado: {len(data)} registros encontrados.")
            return pd.DataFrame(data).head(limit)
        else:
            print("   ⚠️ [Alerta] La fuente de datos no devolvió registros.")
            return pd.DataFrame()
    except Exception as e:
        print(f"   ❌ [Error] Excepción no controlada en tendencias: {e}")
        return pd.DataFrame()
    finally:
        # GESTIÓN DE RECURSOS:
        # Es imperativo cerrar la sesión del navegador para liberar memoria RAM y CPU.
        if driver:
            print("   🏁 [Sistema] Finalizando sesión de navegador.")
            driver.quit() 

# ==============================================================================
# LÓGICA DE ANÁLISIS DE NICHO (MARKET INTELLIGENCE)
# ==============================================================================

def analizar_nicho_mercado(keyword):
    """
    Ejecuta un análisis profundo sobre una palabra clave específica.
    Cruza datos cuantitativos (Oferta) con cualitativos (Sentimiento).

    Args:
        keyword (str): El término de búsqueda a investigar.

    Returns:
        dict: Objeto con métricas consolidadas (Precio, Competencia, Sentimiento).
        None: Si no es posible obtener datos suficientes.
    """
    # Instanciamos un nuevo contexto de navegador para asegurar una sesión limpia (Stateless)
    driver = iniciar_navegador_controlado()
    if not driver: return None
    
    datos_consolidados = None
    
    try:
        # --- FASE 1: Análisis Cuantitativo de la Oferta ---
        url_search = f"https://api.mercadolibre.com/sites/MLA/search?q={keyword}"
        data = ejecutar_solicitud_json(driver, url_search)
        
        if data:
            results = data.get('results', [])
            total_resultados = data.get('paging', {}).get('total', 0)
            
            if results:
                # Cálculo de métricas estadísticas básicas
                precios = [item.get('price', 0) for item in results]
                precio_promedio = sum(precios) / len(precios)
                
                # Identificación de saturación de mercado (Dominio de vendedores Platinum)
                platinum_count = sum(1 for item in results if item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status') == 'platinum')
                pct_platinum = (platinum_count / len(results)) * 100
                
                # --- FASE 2: Análisis Cualitativo (Voz del Cliente) ---
                # Identificamos al líder de la categoría para auditar su feedback
                top_item_id = results[0].get('id')
                url_questions = f"https://api.mercadolibre.com/questions/search?item_id={top_item_id}"
                data_questions = ejecutar_solicitud_json(driver, url_questions)
                
                preguntas_texto = []
                if data_questions:
                    preguntas_texto = [q.get('text', '') for q in data_questions.get('questions', [])]
                
                # Procesamiento de Lenguaje Natural (Sentiment Analysis)
                score_sent = 0
                label_sent = "Neutro"
                if preguntas_texto:
                    scores = [TextBlob(t).sentiment.polarity for t in preguntas_texto]
                    score_sent = sum(scores) / len(scores)
                    
                    # Categorización del resultado numérico
                    if score_sent > 0.1: label_sent = "Positivo"
                    elif score_sent < -0.1: label_sent = "Negativo"

                # Estructuración del objeto de datos final
                datos_consolidados = {
                    "keyword": keyword,
                    "competencia_cantidad": total_resultados,
                    "precio_promedio": round(precio_promedio, 2),
                    "porcentaje_platinum": round(pct_platinum, 1),
                    "sentimiento_score": round(score_sent, 2),
                    "sentimiento_label": label_sent,
                    "cant_preguntas_analizadas": len(preguntas_texto)
                }
                
    except Exception as e:
        print(f"   ❌ Error durante el análisis de '{keyword}': {e}")
    finally:
        if driver:
            driver.quit()
        
    return datos_consolidados

# ==============================================================================
# LÓGICA PRINCIPAL DE PROCESAMIENTO (PIPELINE)
# ==============================================================================

def generar_reporte_oportunidades():
    """
    Punto de entrada principal. Ejecuta el flujo completo de inteligencia de negocios:
    1. Identificación de Oportunidades (Tendencias).
    2. Enriquecimiento de Datos (Análisis Competitivo).
    3. Cálculo de Scoring (Algoritmo de Oportunidad).
    
    Returns:
        pd.DataFrame: Reporte final estructurado listo para visualización.
    """
    # Definimos el alcance del análisis (Limitado a 3 para eficiencia en demostraciones)
    df_trends = obtener_tendencias_mercado(limit=3) 
    
    # Validación de integridad de datos
    if df_trends.empty:
        print("   ⚠️ [Aviso] No hay datos de tendencias para procesar.")
        return pd.DataFrame()

    resultados_procesados = []
    print("⏳ [Pipeline] Iniciando procesamiento secuencial de nichos...")
    
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        print(f"   🔎 [Analizando Nicho] {keyword}...")
        
        # Ejecución del análisis profundo
        datos = analizar_nicho_mercado(keyword)
        
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados_procesados.append(datos)
        
    df_final = pd.DataFrame(resultados_procesados)
    
    # Algoritmo de Scoring de Oportunidad (Opportunity Index)
    if not df_final.empty:
        # Fórmula: Prioriza nichos con alta demanda pero baja saturación de competidores fuertes.
        # (Evitamos división por cero sumando 1 al denominador)
        df_final['opportunity_score'] = (
            (1 / (df_final['competencia_cantidad'] + 1)) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final
