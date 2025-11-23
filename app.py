import streamlit as st
import pandas as pd
import plotly.express as px
import meli_logic

# Configuración de la página
st.set_page_config(page_title="MarketPulse AI", layout="wide", page_icon="⚡")

# Título y Header
st.title("⚡ MarketPulse AI")
st.markdown("""
### Inteligencia de Mercado en Tiempo Real
Esta herramienta consume la API oficial de Mercado Libre para detectar oportunidades de negocio, analizando oferta, precios y barreras de entrada en las categorías de mayor tendencia.
""")

# Sidebar con info técnica
with st.sidebar:
    st.header("⚙️ Configuración")
    st.info("Fuente de Datos: API Oficial Mercado Libre")
    st.caption("MarketPulse AI v2.1.0 | Prod Build")

# Botón de Acción
if st.button("🚀 Iniciar Escaneo de Mercado", type="primary"):
    with st.spinner('Conectando con servidores de Mercado Libre...'):
        # Llamada al Backend
        df = meli_logic.generar_reporte_oportunidades()
        
        if not df.empty:
            st.success("¡Análisis completado con éxito!")
            
            # --- KPI PRINCIPALES (Top Opportunity) ---
            best_opp = df.sort_values('opportunity_score', ascending=False).iloc[0]
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔥 Mejor Oportunidad", best_opp['keyword'], help="Nicho con mejor balance Demanda/Competencia")
            col2.metric("🛡 Saturación Platinum", f"{best_opp['porcentaje_platinum']}%", delta_color="inverse", help="% de la primera página ocupada por grandes vendedores")
            col3.metric("⭐ Calificación Estimada", f"{best_opp['sentimiento_score']} / 5", help="Rating promedio del nicho")
            col4.metric("💎 Opportunity Score", f"{best_opp['opportunity_score']}/100", help="Puntaje algorítmico. Más alto indica mejor oportunidad de entrada.")
            
            st.divider()

            # --- VISUALIZACIÓN DE DATOS ---
            tab1, tab2 = st.tabs(["📊 Matriz de Barreras", "💰 Análisis de Precios"])
            
            with tab1:
                # Gráfico de Dispersión: Competencia vs Dominio
                fig = px.scatter(
                    df,
                    x='competencia_cantidad',
                    y='porcentaje_platinum',
                    size='opportunity_score',
                    color='keyword',
                    title="Matriz de Competencia",
                    labels={'competencia_cantidad': 'Volumen de Resultados', 'porcentaje_platinum': '% Dominio Platinum'},
                    hover_data=['precio_promedio']
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                # Gráfico de Barras: Ticket Promedio
                fig_bar = px.bar(
                    df,
                    x='keyword',
                    y='precio_promedio',
                    color='opportunity_score',
                    title="Ticket Promedio por Categoría ($ ARS)",
                    text_auto='.2s'
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- TABLA DE DATOS RAW ---
            st.subheader("📋 Reporte Detallado")
            st.dataframe(
                df[['ranking_tendencia', 'keyword', 'competencia_cantidad', 'precio_promedio', 'porcentaje_platinum', 'sentimiento_score', 'opportunity_score']]
                .sort_values('opportunity_score', ascending=False)
                .style.background_gradient(subset=['opportunity_score'], cmap='Greens'),
                use_container_width=True
            )
            
        else:
            st.error("No se pudieron obtener datos. Posible bloqueo temporal de API (Error 403) o falta de Token.")

st.markdown("---")
st.caption("⚡ Desarrollado para demostración técnica de Scraping & Data Engineering.")
