# Súper Calculadora VE

Calculadora de cambio entre USD, COP y VES con tasas ancladas al dólar, modo claro/oscuro y una tarjeta con el valor del **USDT en bolívares (Binance P2P)** que se actualiza sola cada 30 minutos.

## Cómo funciona

1. Una acción de GitHub (`.github/workflows/actualizar-tasa.yml`) corre cada hora.
2. Ejecuta `scripts/actualizar_tasa.py`, que consulta Binance P2P y guarda el resultado en `tasa.json`.
3. La calculadora (`index.html`) lee `tasa.json` y muestra el valor, la variación y la hora. Vuelve a leerlo cada 10 minutos mientras está abierta.

**Cómo se calcula el valor:** mediana de los primeros 10 anuncios de compra de USDT en VES y mediana de los primeros 10 de venta; el valor mostrado es el promedio de las dos. Puedes cambiar `ANUNCIOS` en el script si quieres usar más o menos anuncios.
