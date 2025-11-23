import requests
import pandas as pd
import time
from textblob import TextBlob

# --- CONFIGURACIÓN ANTI-BLOQUEO ---
# Usamos este 'User-Agent' para simular que somos un navegador Chrome real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9',
    'Referer': 'https://www.google.com/'
}

def obtener_tendencias_top(limit=10):
    """
    Obtiene las tendencias de búsqueda más populares de Argentina (MLA).
    """
    url = "https://api.mercadolibre.com/trends/MLA"
    print(f"📡 Conectando a Trends: {url}...") # Debug en terminal
    try:
        response = requests.get(url, headers=HEADERS, timeout=10) # Timeout evita que se cuelgue
        response.raise_for_status()
        data = response.json()
        print(f"✅ Tendencias encontradas: {len(data)}")
        return pd.DataFrame(data).head(limit)
    except Exception as e:
        print(f"❌ Error CRÍTICO obteniendo tendencias: {e}")
        return pd.DataFrame()

def obtener_preguntas_item(item_id):
    """
    Busca las últimas preguntas realizadas a un producto específico.
    """
    url = f"https://api.mercadolibre.com/questions/search?item_id={item_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        data = response.json()
        questions = data.get('questions', [])
        return [q.get('text', '') for q in questions]
    except:
        return []

def analizar_sentimiento_preguntas(textos):
    """
    Usa TextBlob para calcular la polaridad promedio.
    """
    if not textos:
        return 0, "Sin datos"
    
    scores = []
    for texto in textos:
        try:
            blob = TextBlob(texto)
            scores.append(blob.sentiment.polarity)
        except:
            pass # Si falla NLP, ignoramos esa frase
    
    if not scores:
        return 0, "Neutro/Sin Info"

    promedio = sum(scores) / len(scores)
    
    if promedio > 0.1: etiqueta = "Positivo/Interesado"
    elif promedio < -0.1: etiqueta = "Negativo/Quejas"
    else: etiqueta = "Neutro/Dudas Técnicas"
    
    return round(promedio, 2), etiqueta

def analizar_competencia(keyword):
    """
    Analiza la oferta para una palabra clave.
    """
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={keyword}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        results = data.get('results', [])
        total_resultados = data.get('paging', {}).get('total', 0)
        
        if not results:
            return None

        # --- ANÁLISIS DE PRECIOS ---
        precios = [item.get('price', 0) for item in results]
        precio_promedio = sum(precios) / len(precios) if precios else 0
        
        # --- ANÁLISIS DE COMPETIDORES (PLATINUM) ---
        platinum_count = 0
        for item in results:
            reputation = item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status', None)
            if reputation == 'platinum':
                platinum_count += 1
        
        pct_platinum = (platinum_count / len(results)) * 100 if results else 0

        # --- SENTIMENT ANALYSIS ---
        top_item_id = results[0].get('id')
        preguntas = obtener_preguntas_item(top_item_id)
        score_sentimiento, etiqueta_sentimiento = analizar_sentimiento_preguntas(preguntas)

        return {
            "keyword": keyword,
            "competencia_cantidad": total_resultados,
            "precio_promedio": round(precio_promedio, 2),
            "porcentaje_platinum": round(pct_platinum, 1),
            "top_item_id": top_item_id,
            "sentimiento_score": score_sentimiento,
            "sentimiento_label": etiqueta_sentimiento,
            "cant_preguntas_analizadas": len(preguntas)
        }
    except Exception as e:
        print(f"⚠️ Error analizando '{keyword}': {e}")
        return None

def generar_reporte_oportunidades():
    df_trends = obtener_tendencias_top(limit=5)
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    
    # Creamos una barra de progreso en la terminal para que veas que avanza
    print("⏳ Iniciando análisis profundo...")
    
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        print(f"   🔎 Analizando: {keyword}...")
        datos = analizar_competencia(keyword)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        time.sleep(0.5) # Aumentamos un poco la pausa para evitar bloqueos

    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        # Evitamos división por cero sumando 1
        df_final['opportunity_score'] = (
            (1 / (df_final['competencia_cantidad'] + 1)) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final