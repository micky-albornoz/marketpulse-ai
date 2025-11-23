# ✨ MarketPulse AI

<img src="https://img.shields.io/badge/MarketPulse_AI-Intelligent_E--commerce_Gap_Detector-blue?style=for-the-badge" />

**MarketPulse AI** es una solución de *Business Intelligence* desarrollada para detectar automáticamente **Océanos Azules** (oportunidades de mercado de alta demanda y baja competencia) en Mercado Libre.

---

🧑‍💻 **Proyecto desarrollado por Miguel Albornoz** como portafolio técnico para roles de Analista de Negocios y Datos.

---

## 📸 Interfaz del Dashboard

(Espacio reservado para la captura de pantalla. Subir una imagen del dashboard funcionando aquí)

## 🎯 Propuesta de Valor

En el retail moderno, la intuición no es suficiente. MarketPulse AI resuelve la ineficiencia del análisis manual atacando tres puntos ciegos mediante el consumo de datos reales::

1.  **Detección de Demanda Real**: Conexión directa a la API pública de Mercado Libre (o `/trends`) para identificar qué buscan los usuarios en tiempo real.
2.  **Barreras de Entrada (Saturación)**: Algoritmo que cuantifica la competencia analizando el porcentaje de vendedores "Platinum" en los primeros 50 resultados orgánicos.
3.  **Análisis de Sentimiento con IA**: Utiliza la librería *TextBlob* para aplicar técnicas de *NLP (Procesamiento de Lenguaje Natural)*, permitiendo evaluar cualitativamente la satisfacción del mercado.
4.  **Scoring de Oportunidad:**: Modelo matemático que pondera demanda vs. oferta para sugerir nichos rentables con un puntaje unificado (0-100).

***

## 💡 Caso de Uso: ¿Qué resuelve?

Imagínate que la herramienta detecta la tendencia: **"Auriculares para dormir"**.

* **Datos**: Hay 5.000 búsquedas diarias.
* **Competencia**: Solo 2 vendedores **Platinum** en la primera página (**Baja barrera**).
* **Sentimiento**: El NLP detecta palabras clave como "batería dura poco" o "son incómodos".
* **Conclusión**: Oportunidad de oro para importar auriculares con "**batería de larga duración**" y diseño ergonómico.

***

## 🛠️ Stack Tecnológico

La arquitectura del proyecto sigue las mejores prácticas de desarrollo en Python e integración de APIs:

* **Core:** `Python 3.x`
* **Data Fetching:** `Requests` (Consumo de API RESTful de Mercado Libre con manejo de Rate Limiting).
* **ETL & Análisis:** `Pandas` para normalización y transformación de datasets JSON.
* **AI & NLP:** `TextBlob` para análisis de sentimiento (proxy).
* **Frontend:** `Streamlit` para la visualización de datos interactiva.
* **Viz:** `Plotly` para gráficos dinámicos.

***

## 💻 Instalación y Ejecución

1. **Clonar el repositorio:**

```bash
git clone https://github.com/micky-albornoz/marketpulse-ai.git
```

2. **Instalar dependencias:**

```bash
pip install -r requirements.txt
```

3. **Configuración (Opcional):** Si dispone de un `ACCESS_TOKEN` de Mercado Libre, puede configurarlo en `meli_logic.py` para evitar límites de cuota pública.

4. **Lanzar la aplicación:**

```bash
streamlit run app.py
```

---

*Este software fue diseñado con fines educativos y de demostración técnica.*
