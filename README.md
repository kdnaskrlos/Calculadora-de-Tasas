# Súper Calculadora VE

Calculadora de cambio USD, COP y VES, con tasas de Binance P2P y BCV, alojada en GitHub Pages.

## Actualización de tasas

1. El workflow `.github/workflows/actualizar-tasa.yml` utiliza GitHub Actions para consultar y guardar la tasa. Su `schedule` actúa como respaldo y puede retrasarse o perder ejecuciones.
2. El script está en `.github/workflows/actualizar_tasa.py`. Consulta anuncios Binance P2P y la tasa oficial BCV; guarda el resultado en `tasa.json`. Las ejecuciones no forzadas solo consultan si el dato tiene al menos 25 minutos.
3. La calculadora `index.html` lee `tasa.json` aproximadamente cada 10 minutos mientras está abierta. La interfaz avisa cuando Binance lleva más de 90 minutos sin actualizarse.
4. El botón Run workflow de GitHub usa `force=true` por defecto para permitir actualización inmediata.
5. El monitor opcional de Cloudflare Workers, configurado cada 10 minutos, solicita la ejecución de GitHub si Binance lleva **35 minutos o más** sin actualizarse. Envía `force=false` para mantener la protección contra consultas redundantes.

**Instalación del monitor gratuito:** [cloudflare/README.md](cloudflare/README.md).

Ninguno de los servicios garantiza una ejecución exactamente al minuto; utilizar ambos permite una vía de respaldo sin contratar un servidor. Las credenciales se almacenan como secretos en Cloudflare, nunca en este repositorio.
