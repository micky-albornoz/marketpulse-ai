import requests
import pandas as pd
import time
from textblob import TextBlob
import platform # Librería para detectar si es Mac o Windows

# --- CONFIGURACIÓN DE IDENTIDAD (HEADERS) ---

# Headers optimizados para MacOS (Chrome)
HEADERS_MAC = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-419,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

# Headers optimizados para Windows (Chrome)
HEADERS_WIN = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-419,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

def get_headers():
    """
    Detecta automáticamente el Sistema Operativo y devuelve
    los headers correctos para minimizar bloqueos.
    """
    sistema = platform.system()
    
    if sistema == 'Darwin': # 'Darwin' es el nombre técnico de MacOS
        print("🍏 Detectado entorno MacOS. Usando headers específicos.")
        return HEADERS_MAC
    else:
        print("🪟 Detectado Windows/Linux. Usando headers estándar.")
        return HEADERS_WIN

def obtener_tendencias_top(limit=10):
    """
    Obtiene tendencias REALES. 
    Si falla, devuelve vacío para mostrar el error en pantalla (CERO datos falsos).
    """
    url = "https://api.mercadolibre.com/trends/MLA"
    headers = get_headers()
    
    print(f"📡 Conectando a Trends: {url}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ÉXITO: {len(data)} tendencias reales descargadas.")
            return pd.DataFrame(data).head(limit)
        else:
            print(f"⚠️ API bloqueó la conexión (Status {response.status_code}).")
            return pd.DataFrame() # Devuelve vacío intencionalmente
    
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return pd.DataFrame() # Devuelve vacío en caso de error

def obtener_preguntas_item(item_id):
    url = f"https://api.mercadolibre.com/questions/search?item_id={item_id}"
    headers = get_headers()
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [q.get('text', '') for q in data.get('questions', [])]
    except:
        pass
    return []

def analizar_sentimiento_preguntas(textos):
    if not textos:
        return 0, "Neutro/Sin Datos"
    
    scores = []
    for t in textos:
        try:
            scores.append(TextBlob(t).sentiment.polarity)
        except:
            pass
            
    if not scores: return 0, "Neutro"

    promedio = sum(scores) / len(scores)
    
    if promedio > 0.1: etiqueta = "Positivo/Interesado"
    elif promedio < -0.1: etiqueta = "Negativo/Quejas"
    else: etiqueta = "Neutro/Dudas Técnicas"
    
    return round(promedio, 2), etiqueta

def analizar_competencia(keyword):
    """
    Analiza la competencia REAL. Si falla, devuelve None.
    NO genera datos aleatorios.
    """
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={keyword}"
    headers = get_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            total_resultados = data.get('paging', {}).get('total', 0)
            
            if results:
                precios = [item.get('price', 0) for item in results]
                precio_promedio = sum(precios) / len(precios)
                
                platinum_count = sum(1 for item in results if item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status') == 'platinum')
                pct_platinum = (platinum_count / len(results)) * 100
                
                top_item_id = results[0].get('id')
                preguntas = obtener_preguntas_item(top_item_id)
                score_sent, label_sent = analizar_sentimiento_preguntas(preguntas)

                return {
                    "keyword": keyword,
                    "competencia_cantidad": total_resultados,
                    "precio_promedio": round(precio_promedio, 2),
                    "porcentaje_platinum": round(pct_platinum, 1),
                    "sentimiento_score": round(score_sent, 2),
                    "sentimiento_label": label_sent,
                    "cant_preguntas_analizadas": len(preguntas)
                }
    except Exception as e:
        print(f"⚠️ Error analizando '{keyword}': {e}")
        pass

    return None # Si algo falla, no retorna nada (no inventa)

def generar_reporte_oportunidades():
    df_trends = obtener_tendencias_top(limit=5)
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ Analizando items uno por uno...")
    
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        datos = analizar_competencia(keyword)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        time.sleep(1) # Pausa ética para evitar bloqueos

    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        df_final['opportunity_score'] = (
            (1 / (df_final['competencia_cantidad'] + 1)) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final