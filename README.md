# Súper Calculadora VE

Calculadora de cambio entre USD, COP y VES con tasas ancladas al dólar, modo claro/oscuro y una tarjeta con el valor del **USDT en bolívares (Binance P2P)** que se actualiza sola cada hora.

## Cómo funciona

1. Una acción de GitHub (`.github/workflows/actualizar-tasa.yml`) corre cada hora.
2. Ejecuta `scripts/actualizar_tasa.py`, que consulta Binance P2P y guarda el resultado en `tasa.json`.
3. La calculadora (`index.html`) lee `tasa.json` y muestra el valor, la variación y la hora. Vuelve a leerlo cada 10 minutos mientras está abierta.

**Cómo se calcula el valor:** mediana de los primeros 10 anuncios de compra de USDT en VES y mediana de los primeros 10 de venta; el valor mostrado es el promedio de las dos. Puedes cambiar `ANUNCIOS` en el script si quieres usar más o menos anuncios.

## Instalación (una sola vez)

1. En GitHub crea un repositorio **público** nuevo (por ejemplo `super-calculadora-ve`). Los repositorios públicos pueden usar GitHub Pages gratis.
2. Sube estos archivos al repositorio: botón **Add file → Upload files**, y arrastra `index.html`, `tasa.json`, `README.md` y la carpeta `scripts`.
3. Crea la programación a mano, porque las carpetas que empiezan con punto a veces no se suben bien: **Add file → Create new file**, escribe como nombre `.github/workflows/actualizar-tasa.yml` y pega el contenido de ese archivo del zip. Guarda con **Commit changes**.
4. Ve a **Settings → Actions → General → Workflow permissions**, elige **Read and write permissions** y guarda.
5. Ve a **Settings → Pages**, en *Source* elige **Deploy from a branch**, rama `main`, carpeta `/ (root)` y guarda.
6. Ve a la pestaña **Actions → Actualizar tasa USDT → Run workflow** para hacer la primera ejecución. Al terminar (unos segundos) abre el registro: debe decir algo como `USDT/VES = 1002.45`.
7. Abre tu calculadora en `https://TU-USUARIO.github.io/NOMBRE-DEL-REPO/` (GitHub la publica en uno o dos minutos).

## Si algo falla

- **La ejecución falla con 403 o 451:** Binance puede rechazar los servidores de GitHub. Puedes correr el script desde tu computadora con `python scripts/actualizar_tasa.py` (necesita Python 3) y subir el `tasa.json` resultante, o avisarme y buscamos otra salida.
- **La tarjeta dice "Todavía no hay valor":** falta la primera ejecución del paso 6.
- **La tarjeta dice "No se pudo leer tasa.json":** estás abriendo `index.html` como archivo local. Ábrela desde tu dirección de GitHub Pages.
- **La tarjeta avisa que el valor tiene más de 3 horas:** revisa la pestaña Actions. GitHub puede retrasar las ejecuciones programadas unos minutos, y en repositorios públicos sin actividad por 60 días pausa la programación; se reactiva desde esa misma pestaña.

## Notas

- La hora de la programación está en UTC (`5 * * * *` = minuto 5 de cada hora).
- Se guarda un cambio en el repositorio por hora; es normal que el historial de cambios crezca.
- Tus tasas de la calculadora (COP y VES por dólar), el tema y el último valor visto se guardan en el navegador de cada dispositivo.
