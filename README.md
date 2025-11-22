# ✨ MarketPulse AI

<img src="https://img.shields.io/badge/MarketPulse_AI-Intelligent_E--commerce_Gap_Detector-blue?style=for-the-badge" />

**MarketPulse AI** es una solución de *Business Intelligence* desarrollada para detectar automáticamente **Océanos Azules** (oportunidades de mercado de alta demanda y baja competencia) en Mercado Libre.

---

🧑‍💻 **Proyecto desarrollado por Miguel Albornoz** como portafolio técnico para roles de Analista de Negocios y Datos.


🔗 **Demo en Vivo**: [Haz clic aquí para ver la App funcionando](URL_A_MI_APP_REAL) (Reemplazar este link con mi URL real al desplegar)

---

## 📸 Interfaz del Dashboard

(Espacio reservado para la captura de pantalla. Subir una imagen del dashboard funcionando aquí)

## 🎯 Propuesta de Valor

En el retail moderno, la intuición no es suficiente. **MarketPulse AI** resuelve la ineficiencia del análisis manual atacando tres puntos ciegos:

1.  **Detección de Demanda Real**: Conexión directa a la API pública de Mercado Libre (o `/trends`) para identificar qué buscan los usuarios **hoy**.
2.  **Barreras de Entrada (Saturación)**: Algoritmo que cuantifica la competencia analizando el porcentaje de vendedores "Platinum" en la primera página de resultados.
3.  **Análisis Cualitativo con IA**: Utiliza la bilblioteca **TextBlob** que simplifica el procesamiento del lenguaje natural (NLP), proporcionando una API sencilla para leer las preguntas de los compradores y detectar **"pain points"** (quejas o dudas recurrentes).

***

## 💡 Caso de Uso: ¿Qué resuelve?

Imagínate que la herramienta detecta la tendencia: **"Auriculares para dormir"**.

* **Datos**: Hay 5.000 búsquedas diarias.
* **Competencia**: Solo 2 vendedores **Platinum** en la primera página (**Baja barrera**).
* **Sentimiento**: El NLP detecta palabras clave como "batería dura poco" o "son incómodos".
* **Conclusión**: Oportunidad de oro para importar auriculares con "**batería de larga duración**" y diseño ergonómico.

***

## ⚙️ Stack Tecnológico

La arquitectura del proyecto sigue las mejores prácticas de desarrollo en **Python**:

* Core: **Python 3.x**
* Data Fetching: **Requests** (Consumo de APIs RESTful).
* ETL & Análisis: **Pandas** para manipulación de estructuras de datos.
* AI & NLP: **TextBlob** para análisis de sentimiento y procesamiento de texto.
* Frontend: **Streamlit** para la visualización de datos interactiva.
* Viz: **Plotly** para gráficos dinámicos.

***

## 💻 Instalación y Ejecución

1.  Clonar el repositorio:

    ```bash
    git clone https://github.com/micky-albornoz/marketpulse-ai.git
    ```

2.  Instalar dependencias:

    ```bash
    pip install -r requirements.txt
    ```

3.  Lanzar la aplicación:

    ```bash
    streamlit run app.py
    ```

*Este software fue diseñado con fines educativos y de demostración técnica.*
