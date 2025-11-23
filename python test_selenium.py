from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

print("--- INICIO DE DIAGNÓSTICO ---")

print("1. Intentando descargar/verificar el driver de Chrome...")
try:
    ruta_driver = ChromeDriverManager().install()
    print(f"✅ Driver detectado en: {ruta_driver}")
except Exception as e:
    print(f"❌ Error descargando driver: {e}")
    exit()

print("2. Intentando abrir el navegador Chrome...")
try:
    service = Service(ruta_driver)
    driver = webdriver.Chrome(service=service)
    print("✅ ¡ÉXITO! El navegador se abrió.")
    
    driver.get("https://www.google.com")
    print("3. Navegando a Google...")
    time.sleep(5)
    
    driver.quit()
    print("4. Prueba finalizada correctamente.")
    
except Exception as e:
    print(f"❌ FALLÓ al abrir el navegador: {e}")
    print("\nPOSIBLES CAUSAS:")
    print("- No tienes Google Chrome instalado en la carpeta Aplicaciones.")
    print("- Una ventana de seguridad de Mac está bloqueando 'chromedriver'.")
