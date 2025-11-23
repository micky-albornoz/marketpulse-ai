import requests
import pandas as pd
import time
from textblob import TextBlob

def obtener_tendencias_top(limit=10):
    """
    Obtiene las tendencias de búsqueda más populares de Argentina (MLA).
    """
    url = "https://api.mercadolibre.com/trends/MLA"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data).head(limit)
    except Exception as e:
        print(f"Error obteniendo tendencias: {e}")
        return pd.DataFrame()

def obtener_preguntas_item(item_id):
    """
    Busca las últimas preguntas realizadas a un producto específico
    para analizar qué están diciendo los clientes.
    """
    url = f"https://api.mercadolibre.com/questions/search?item_id={item_id}"
    try:
        response = requests.get(url)
        data = response.json()
        questions = data.get('questions', [])
        # Retornamos solo el texto de las preguntas
        return [q.get('text', '') for q in questions]
    except:
        return []

def analizar_sentimiento_preguntas(textos):
    """
    Usa TextBlob para calcular la polaridad promedio de una lista de textos.
    Polaridad: -1 (Muy Negativo) a +1 (Muy Positivo).
    """
    if not textos:
        return 0, "Sin datos"
    
    scores = []
    for texto in textos:
        # TextBlob funciona mejor en inglés, pero para demo simple sirve en español
        # o se puede traducir. Aquí usaremos el texto directo para simplificar.
        blob = TextBlob(texto)
        scores.append(blob.sentiment.polarity)
    
    promedio = sum(scores) / len(scores)
    
    if promedio > 0.1: etiqueta = "Positivo/Interesado"
    elif promedio < -0.1: etiqueta = "Negativo/Quejas"
    else: etiqueta = "Neutro/Dudas Técnicas"
    
    return round(promedio, 2), etiqueta

def analizar_competencia(keyword):
    """
    Analiza la oferta para una palabra clave:
    1. Volumen de competencia.
    2. Presencia de vendedores Platinum (Barrera de entrada).
    3. Sentimiento del mercado (basado en preguntas del Top 1).
    """
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={keyword}"
    
    try:
        response = requests.get(url)
        data = response.json()
        results = data.get('results', [])
        total_resultados = data.get('paging', {}).get('total', 0)
        
        if not results:
            return None

        # --- ANÁLISIS DE PRECIOS Y ESTADO ---
        precios = [item.get('price', 0) for item in results]
        precio_promedio = sum(precios) / len(precios) if precios else 0
        
        # --- ANÁLISIS DE COMPETIDORES (PLATINUM) ---
        # Contamos cuántos de los primeros 50 resultados son de "MercadoLíder Platinum"
        platinum_count = 0
        for item in results:
            reputation = item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status', None)
            if reputation == 'platinum':
                platinum_count += 1
        
        pct_platinum = (platinum_count / len(results)) * 100 if results else 0

        # --- SENTIMENT ANALYSIS (BONUS) ---
        # Tomamos el ítem #1 orgánico para ver sus preguntas
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
        print(f"Error en {keyword}: {e}")
        return None

def generar_reporte_oportunidades():
    df_trends = obtener_tendencias_top(limit=5) # Reducimos a 5 para que sea rápido con el análisis extra
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    status_bar = None # Placeholder si quisiéramos barra de progreso

    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        datos = analizar_competencia(keyword)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        time.sleep(0.2) # Respetamos a la API

    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        # Ajuste de Score:
        # Alta Competencia (-), Muchos Platinum (-) -> Score bajo
        # Baja Competencia (+), Pocos Platinum (+) -> Score alto
        # Usamos inversa para que mayor score sea mejor oportunidad
        df_final['opportunity_score'] = (
            (1 / (df_final['competencia_cantidad'] + 1)) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final