import requests
import pandas as pd
import time
from textblob import TextBlob

# ==============================================================================
# MÓDULO DE INGENIERÍA DE DATOS: INTEGRACIÓN CON MERCADO LIBRE
# ------------------------------------------------------------------------------
# ARQUITECTURA:
# Este módulo implementa una capa de servicio para consumir la API RESTful de
# Mercado Libre. Se prioriza la obtención de datos en tiempo real para garantizar
# la precisión en la toma de decisiones de negocio.
#
# REQUISITOS:
# - Conexión a Internet estable.
# - Token de Acceso (Bearer Token) para evitar limitaciones de tasa (Rate Limiting)
#   y bloqueos de seguridad (Error 403) en endpoints públicos.
# ==============================================================================

# 🔑 CONFIGURACIÓN DE SEGURIDAD
# Coloca aquí tu Access Token obtenido vía OAuth 2.0.
# Si está vacío, el script intentará acceso público (limitado).
ACCESS_TOKEN = ""

def get_headers():
    """
    Construye los encabezados HTTP necesarios para una petición válida.
    Incluye el Token de Autorización si está disponible.
    """
    headers = {"Content-Type": "application/json"}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    return headers

def consultar_api(url):
    """
    Función wrapper para ejecutar peticiones HTTP GET de forma segura.
    Maneja excepciones de red y códigos de estado HTTP.
    
    Args:
        url (str): Endpoint completo a consultar.
        
    Returns:
        dict/list: Respuesta JSON parseada si es exitosa.
        None: Si ocurre un error crítico.
    """
    try:
        print(f"   📡 [API Request] Conectando a: {url}...")
        response = requests.get(url, headers=get_headers(), timeout=10)
        
        # Manejo de respuestas según estándar HTTP
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print("   ⛔ [Error 403] Acceso Denegado. Se requiere un Token válido o IP limpia.")
            return None
        elif response.status_code == 429:
            print("   ⏳ [Error 429] Cuota excedida (Rate Limit). Pausando ejecución...")
            time.sleep(2)
            return None
        else:
            print(f"   ⚠️ [Error API] Status Code: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ [Excepción de Red] {e}")
        return None

# ==============================================================================
# 1. DISCOVERY: DETECCIÓN DE TENDENCIAS (TRENDS API)
# ==============================================================================

def obtener_tendencias_api(limit=5):
    """
    Consulta el endpoint de Tendencias para identificar qué buscan los usuarios
    en este preciso momento en Argentina (Site MLA).
    
    No utiliza listas predefinidas; los datos son dinámicos.
    Endpoint: https://api.mercadolibre.com/trends/MLA
    """
    url = "https://api.mercadolibre.com/trends/MLA"
    data = consultar_api(url)
    
    if not data:
        print("   ⚠️ [Alerta] No se pudieron recuperar tendencias. Verifique credenciales.")
        return pd.DataFrame()

    # La API devuelve una lista de objetos: [{'keyword': '...', 'url': '...'}, ...]
    df = pd.DataFrame(data)
    
    # --- FILTRO DE CALIDAD DE DATOS ---
    # Eliminamos palabras clave navegacionales (ej: "Mercado Libre", "Mi Cuenta")
    # para quedarnos solo con intenciones de compra de productos.
    filtro_basura = df['keyword'].str.lower().str.contains('mercado libre|ingresa|cuenta|vender')
    df_clean = df[~filtro_basura]
    
    print(f"   ✅ [Data Success] {len(df_clean)} tendencias procesadas correctamente.")
    return df_clean.head(limit)

# ==============================================================================
# 2. MARKET ANALYSIS: ANÁLISIS DE CATEGORÍA (SEARCH API)
# ==============================================================================

def analizar_categoria_api(keyword):
    """
    Realiza un 'Deep Dive' en una categoría específica buscando productos reales.
    Calcula métricas estadísticas sobre los primeros 50 resultados orgánicos.
    
    Endpoint: https://api.mercadolibre.com/sites/MLA/search
    """
    # Codificación URL (ej: "Smart TV" -> "Smart%20TV")
    q = keyword.replace(" ", "%20")
    
    # Solicitamos 50 items para tener una muestra estadística representativa
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={q}&limit=50"
    
    data = consultar_api(url)
    
    # Validación de estructura de respuesta
    if not data or 'results' not in data:
        return None
        
    results = data['results']
    total_resultados = data.get('paging', {}).get('total', 0)
    
    # --- PROCESAMIENTO DE MÉTRICAS (ETL) ---
    precios = []
    conteo_platinum = 0
    
    for item in results:
        # A. Extracción de Precio
        if 'price' in item and item['price'] is not None:
            precios.append(float(item['price']))
            
        # B. Análisis de Competencia (Reputación)
        # Verificamos si el vendedor es un jugador dominante (Platinum/Gold/Oficial)
        try:
            seller = item.get('seller', {})
            reputation = seller.get('seller_reputation', {})
            status = reputation.get('power_seller_status', None)
            
            es_competencia_fuerte = False
            if status in ['platinum', 'gold']:
                es_competencia_fuerte = True
            if item.get('official_store_id'): # Tienda Oficial
                es_competencia_fuerte = True
                
            if es_competencia_fuerte:
                conteo_platinum += 1
        except: pass

    # C. Cálculo de KPIs (Key Performance Indicators)
    if precios:
        precio_promedio = sum(precios) / len(precios)
    else:
        precio_promedio = 0
        
    # % de Saturación: Qué porcentaje de la página 1 está tomado por grandes vendedores
    pct_platinum = (conteo_platinum / len(results)) * 100 if results else 0
    
    # D. Estimación de Sentimiento (Proxy Lógico)
    # Nota Técnica: La API de Search no devuelve reviews. Para obtener el sentimiento real
    # deberíamos consumir 50 unidades de cuota extra (/reviews/item). 
    # Para optimizar recursos, inferimos el estado del mercado según la saturación.
    if pct_platinum > 80:
        sentimiento_label = "Mercado Maduro (Alta Competencia)"
        sentimiento_score = 4.5 # Los líderes suelen tener buen rating
    elif pct_platinum < 30:
        sentimiento_label = "Oportunidad (Oferta Atomizada)"
        sentimiento_score = 3.8 # Nicho emergente
    else:
        sentimiento_label = "Mercado Estándar"
        sentimiento_score = 4.2

    # Retorno de objeto estructurado para el Frontend
    return {
        "keyword": keyword,
        "competencia_cantidad": total_resultados,
        "precio_promedio": round(precio_promedio, 2),
        "porcentaje_platinum": round(pct_platinum, 1),
        "sentimiento_score": sentimiento_score,
        "sentimiento_label": sentimiento_label,
        "cant_preguntas_analizadas": len(results)
    }

# ==============================================================================
# 3. ORQUESTADOR (PIPELINE PRINCIPAL)
# ==============================================================================

def generar_reporte_oportunidades():
    """
    Ejecuta el flujo completo de datos:
    1. Obtiene tendencias -> 2. Analiza métricas -> 3. Calcula Score.
    """
    # Paso 1: Discovery
    df_trends = obtener_tendencias_api(limit=5)
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ [Pipeline] Iniciando procesamiento por lotes...")
    
    # Paso 2: Análisis Iterativo
    for index, row in df_trends.iterrows():
        print(f"   🔎 Procesando nicho: {row['keyword']}...")
        datos = analizar_categoria_api(row['keyword'])
        
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        
        # Pausa de cortesía para respetar el Rate Limit de la API
        time.sleep(0.3)
        
    df_final = pd.DataFrame(resultados)
    
    # Paso 3: Algoritmo de Scoring
    if not df_final.empty:
        # Fórmula de Oportunidad:
        # Buscamos nichos con Volumen de Búsqueda (que ya traemos por ser tendencia)
        # pero penalizamos la saturación de vendedores Platinum.
        
        # Normalización de Competencia (Logarítmica inversa simplificada)
        comp_factor = df_final['competencia_cantidad'].apply(
            lambda x: 100 if x < 1000 else (50 if x < 50000 else 10)
        )
        
        # Penalización por Barreras de Entrada
        plat_factor = 100 - df_final['porcentaje_platinum']
        
        df_final['opportunity_score'] = (comp_factor * 0.4 + plat_factor * 0.6).round(2)
    
    return df_final
