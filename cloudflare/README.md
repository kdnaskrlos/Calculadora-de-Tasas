# Configurar monitor gratuito para la Calculadora de Tasas

El monitor funciona con Cloudflare Workers Free y GitHub Actions. No cambia los cálculos ni la interfaz de la calculadora. Verifica cada 10 minutos si `tasa.json` tiene más de 35 minutos y, de ser así, solicita una actualización a GitHub.

## 1. Integrar el pull request

Primero se debe incorporar esta propuesta a la rama `main`, para que el workflow de GitHub reconozca la entrada `force=false` que envía Cloudflare. El workflow existente seguirá funcionando como respaldo.

## 2. Crear un token limitado en GitHub

1. Abre GitHub > foto de perfil > Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token.
2. Selecciona la cuenta `kdnaskrlos` como propietaria del token.
3. En Repository access, elige **Only select repositories** y selecciona **Calculadora-de-Tasas**.
4. En Repository permissions, agrega **Actions: Read and write**. El permiso Metadata: Read se concede automáticamente.
5. Define la fecha de expiración. Cuando venza el token, habrá que renovarlo en Cloudflare.
6. Copia el token y guárdalo de forma segura. **Nunca lo pegues en GitHub, en el chat, en archivos del proyecto ni en capturas.**

## 3. Crear el Worker en Cloudflare Free

1. Inicia sesión o crea una cuenta gratuita en https://dash.cloudflare.com/.
2. Abre Workers & Pages y crea un Worker llamado `calculadora-tasas-monitor`.
3. En el editor del Worker, reemplaza el ejemplo con el contenido completo de [worker.js](worker.js), guarda y despliega.
4. Abre la sección de Variables and Secrets del Worker. Agrega un secreto llamado exactamente `GITHUB_TOKEN` y pega el token de GitHub. Guarda y despliega la configuración.
5. En los ajustes del Worker, abre **Triggers / Cron Triggers** y agrega la expresión `*/10 * * * *` (cada 10 minutos en UTC). La ubicación exacta de estas opciones puede variar con el panel.

**Alternativa para quien utiliza Wrangler:** [wrangler.toml](wrangler.toml) contiene la programación. No incluyas el token allí. Usa el secreto `GITHUB_TOKEN` del entorno o `wrangler secret put GITHUB_TOKEN`.

## 4. Validar el funcionamiento

- Revisa los logs del Worker en Cloudflare tras un ciclo de programación.
- Si la tasa es reciente, aparecerá `Tasa reciente: ... No se activa GitHub.`.
- Si supera 35 minutos, aparecerá `Tasa antigua ... GitHub Actions activado.`.
- En https://github.com/kdnaskrlos/Calculadora-de-Tasas/actions/workflows/actualizar-tasa.yml debe aparecer una ejecución del evento `workflow_dispatch`.
- En https://github.com/kdnaskrlos/Calculadora-de-Tasas/blob/main/tasa.json comprueba que `updated_at` haya avanzado; verifica también la tasa que ve la calculadora.
- Las activaciones manuales desde GitHub mantienen `force=true` por defecto.

Los Cron Triggers pueden tardar unos minutos en propagarse después del despliegue. Las pruebas locales NO sustituyen a la comprobación del servicio desplegado.

## Errores habituales

- **Falta GITHUB_TOKEN**: configurar y desplegar el secreto en Cloudflare.
- **GitHub HTTP 401/403**: token inválido, expirado, sin permisos Actions: write, o repositorio incorrecto.
- **No se pudo leer tasa.json**: comprobar conectividad y validez de `main/tasa.json`.
- **Tasa reciente**: el Worker no activa GitHub cuando no hace falta actualizar.
- **GitHub Actions activado, pero tasa antigua**: revisar el log del workflow y la consulta a Binance.

## Seguridad y costos

- Las peticiones HTTP al Worker obtienen un error 404; nadie puede usar la URL pública para activar GitHub.
- El token se guarda como secreto, no en el código.
- El Worker usa la cuota gratuita de Cloudflare y GitHub Actions conserva su mecanismo programado como respaldo.
- Ambos programadores pueden retrasarse. No garantizan la ejecución exactamente al minuto.
- No habilites funciones de pago, planes Workers Paid ni facturación adicional para este monitor.

## Pruebas

Con Node.js instalado ejecuta `node --test` desde la carpeta `cloudflare`. Las pruebas usan solicitudes simuladas y no modifican la tasa pública.
