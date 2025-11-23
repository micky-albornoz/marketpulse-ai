import streamlit as st
import pandas as pd
import plotly.express as px
import meli_logic

# Configuración de la página con el nuevo nombre
st.set_page_config(page_title="MarketPulse AI", layout="wide", page_icon="⚡")

# Encabezado con estilo más "SaaS"
st.title("⚡ MarketPulse AI")
st.markdown("""
### Detecta Océanos Azules en E-commerce con Inteligencia Artificial.
Esta herramienta escanea tendencias de mercado en tiempo real, analiza la saturación de vendedores y utiliza **NLP (Procesamiento de Lenguaje Natural)** para entender la voz del cliente.
""")

# Sidebar para controles (hace que se vea más pro)
with st.sidebar:
    st.header("⚙️ Configuración")
    st.info("Conectado a API: Mercado Libre (MLA)")
    limit_trends = st.slider("Límite de Tendencias a Analizar", 5, 20, 5)
    st.write("---")
    st.caption("MarketPulse AI v1.0.0")

if st.button("🚀 Iniciar Escaneo de Mercado", type="primary"):
    with st.spinner('Analizando Tendencias, Competencia y Sentimiento (AI)...'):
        # Usamos la lógica que ya creamos, pero es agnóstica a la marca
        df = meli_logic.generar_reporte_oportunidades()
        
        if not df.empty:
            st.success("¡Análisis de Inteligencia Comercial finalizado!")
            
            # --- KPI PRINCIPALES ---
            # Ordenamos por mejor oportunidad
            best_opp = df.sort_values('opportunity_score', ascending=False).iloc[0]
            
            # Contenedores métricos con estilo
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔥 Top Oportunidad", best_opp['keyword'])
            col2.metric("🛡 Saturación Mercado", f"{best_opp['porcentaje_platinum']}%", delta_color="inverse", help="% de vendedores Platinum en la primera página")
            col3.metric("💬 Sentimiento Cliente", best_opp['sentimiento_label'], help="Basado en análisis de preguntas recientes")
            col4.metric("💰 Precio Promedio", f"$ {best_opp['precio_promedio']}")
            
            st.divider()

            # --- VISUALIZACIÓN AVANZADA ---
            tab1, tab2 = st.tabs(["📊 Matriz de Competencia", "🧠 Análisis de Sentimiento"])
            
            with tab1:
                st.subheader("Barreras de Entrada (Dominio Platinum)")
                st.caption("Identifica nichos donde los grandes vendedores (Platinum) aún no dominan.")
                fig_bar = px.bar(
                    df, 
                    x='keyword', 
                    y='porcentaje_platinum',
                    color='porcentaje_platinum',
                    text_auto=True,
                    labels={'porcentaje_platinum': '% Dominio Platinum', 'keyword': 'Tendencia'},
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with tab2:
                st.subheader("La Voz del Cliente (AI Sentiment Analysis)")
                st.caption("Gráfico de dispersión: ¿De qué se quejan los usuarios en categorías saturadas?")
                fig_scatter = px.scatter(
                    df,
                    x='competencia_cantidad',
                    y='sentimiento_score',
                    size='cant_preguntas_analizadas',
                    color='sentimiento_label',
                    hover_name='keyword',
                    labels={'competencia_cantidad': 'Volumen de Competencia', 'sentimiento_score': 'Score de Sentimiento (-1 a 1)'},
                    color_discrete_map={
                        "Positivo/Interesado": "#00CC96", 
                        "Neutro/Dudas Técnicas": "#AB63FA", 
                        "Negativo/Quejas": "#EF553B"
                    }
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            # --- DATOS CRUDOS ---
            st.subheader("📂 Exportar Datos para Estrategia")
            st.dataframe(
                df.style.background_gradient(subset=['opportunity_score'], cmap='Greens'),
                use_container_width=True
            )
            
        else:
            st.error("No se pudieron obtener datos en este momento. Verifique la conexión con la API.")

st.markdown("---")
st.caption("⚡ MarketPulse AI | Demo Técnica de Portafolio Profesional")