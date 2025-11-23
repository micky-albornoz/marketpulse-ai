import cloudscraper
import pandas as pd
import time
from textblob import TextBlob

# --- CONFIGURACIÓN DEL SCRAPER ---
# Creamos un "navegador" que maneja cookies y desafíos de seguridad automáticamente
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

def obtener_tendencias_top(limit=10):
    """
    Obtiene tendencias REALES usando CloudScraper para evadir bloqueos.
    """
    url = "https://api.mercadolibre.com/trends/MLA"
    print(f"📡 Conectando a Trends (Real Data): {url}...")
    
    try:
        # Usamos scraper.get en lugar de requests.get
        response = scraper.get(url) 
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ÉXITO: {len(data)} tendencias reales descargadas.")
            return pd.DataFrame(data).head(limit)
        else:
            print(f"❌ Error API: Status {response.status_code}")
            return pd.DataFrame()
    
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return pd.DataFrame()

def obtener_preguntas_item(item_id):
    url = f"https://api.mercadolibre.com/questions/search?item_id={item_id}"
    try:
        response = scraper.get(url)
        if response.status_code == 200:
            data = response.json()
            return [q.get('text', '') for q in data.get('questions', [])]
    except:
        pass
    return []

def analizar_sentimiento_preguntas(textos):
    if not textos:
        return 0, "Sin datos / Neutro"
    
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
    Analiza la competencia REAL.
    """
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={keyword}"
    
    try:
        response = scraper.get(url)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            total_resultados = data.get('paging', {}).get('total', 0)
            
            if results:
                precios = [item.get('price', 0) for item in results]
                precio_promedio = sum(precios) / len(precios)
                
                platinum_count = sum(1 for item in results if item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status') == 'platinum')
                pct_platinum = (platinum_count / len(results)) * 100
                
                # Intentamos sacar preguntas reales
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
        print(f"Error analizando {keyword}: {e}")
        pass

    return None

def generar_reporte_oportunidades():
    df_trends = obtener_tendencias_top(limit=5)
    
    if df_trends.empty:
        return pd.DataFrame()

    resultados = []
    print("⏳ Analizando competencia real...")
    
    for index, row in df_trends.iterrows():
        keyword = row['keyword']
        datos = analizar_competencia(keyword)
        if datos:
            datos['ranking_tendencia'] = index + 1
            resultados.append(datos)
        # Random sleep para parecer humano (entre 0.5 y 1.5 seg)
        time.sleep(0.5)

    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        df_final['opportunity_score'] = (
            (1 / (df_final['competencia_cantidad'] + 1)) * (100 - df_final['porcentaje_platinum']) * 10000
        ).round(2)
    
    return df_final