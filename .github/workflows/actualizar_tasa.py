#!/usr/bin/env python3
"""Consulta Binance P2P y actualiza tasa.json con el valor del USDT en bolívares.

Solo usa la biblioteca estándar de Python (no hay nada que instalar).

Cómo calcula el valor:
  - Toma los primeros 10 anuncios de COMPRA de USDT por VES y saca la mediana.
  - Toma los primeros 10 anuncios de VENTA de USDT por VES y saca la mediana.
  - El valor de referencia ("rate") es el promedio de esas dos medianas.

Si la consulta falla, el script termina con error y deja tasa.json como estaba.
"""
import http.client
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
# tasa.json se guarda en la carpeta desde donde se ejecuta el script (la raíz del repositorio)
RUTA = os.environ.get("TASA_RUTA", "tasa.json")
ANUNCIOS = 10          # cuántos anuncios se usan para cada lado
MAX_HISTORIAL = 48     # puntos guardados (2 días si corre cada hora)
INTENTOS = 3
MIN_MINUTOS = 25       # el workflow corre cada 10 min, pero solo consulta si el valor tiene más de esto
# Dólar oficial del BCV (DolarAPI, pública y sin clave). Campo "promedio" = tasa oficial.
BCV_URL = "https://ve.dolarapi.com/v1/dolares/oficial"
ERRORES_RED = (OSError, http.client.HTTPException, RuntimeError, ValueError, KeyError, AttributeError)


def consultar(lado):
    """Devuelve la mediana de precios de los primeros anuncios (lado: BUY o SELL)."""
    cuerpo = {
        "fiat": "VES",
        "page": 1,
        "rows": ANUNCIOS,
        "tradeType": lado,
        "asset": "USDT",
        "countries": [],
        "proMerchantAds": False,
        "shieldMerchantAds": False,
        "publisherType": None,
        "payTypes": [],
        "classifies": ["mass", "profession"],
    }
    pedido = urllib.request.Request(
        URL,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; super-calculadora-ve)",
        },
        method="POST",
    )
    ultimo_error = None
    for intento in range(1, INTENTOS + 1):
        try:
            with urllib.request.urlopen(pedido, timeout=30) as respuesta:
                datos = json.load(respuesta)
            if datos.get("code") not in (None, "000000"):
                raise RuntimeError("Binance respondió con código %s" % datos.get("code"))
            precios = [float(a["adv"]["price"]) for a in (datos.get("data") or [])]
            precios = [p for p in precios if p > 0]
            if not precios:
                raise RuntimeError("Binance no devolvió anuncios para %s" % lado)
            return statistics.median(precios)
        except ERRORES_RED as error:
            ultimo_error = error
            print("Intento %d/%d (%s) falló: %s" % (intento, INTENTOS, lado, error), file=sys.stderr)
            if intento < INTENTOS:
                time.sleep(5 * intento)
    raise SystemExit("No se pudo consultar Binance (%s): %s" % (lado, ultimo_error))


def construir(compra, venta, anterior, ahora):
    """Arma el contenido de tasa.json. 'anterior' es el contenido previo (o {})."""
    rate = round((compra + venta) / 2, 2)
    previo = anterior.get("rate")
    if isinstance(previo, (int, float)) and previo > 0:
        cambio = round((rate / previo - 1) * 100, 2)
    else:
        cambio = None
    marca = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")
    historial = list(anterior.get("history") or [])
    historial.append({"t": marca, "rate": rate})
    historial = historial[-MAX_HISTORIAL:]
    return {
        "pair": "USDT/VES",
        "source": "Binance P2P",
        "rate": rate,
        "buy": round(compra, 2),
        "sell": round(venta, 2),
        "previous_rate": previo if isinstance(previo, (int, float)) else None,
        "change_pct": cambio,
        "updated_at": marca,
        "history": historial,
    }


def leer_anterior():
    try:
        with open(RUTA, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def normalizar_fecha(texto, ahora=None):
    """Convierte una fecha ISO a UTC con formato 2026-10-22T14:30:22Z (o usa 'ahora' si no se entiende)."""
    try:
        fecha = datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return (ahora or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def consultar_bcv():
    """Dólar oficial del BCV. Devuelve (valor, fecha ISO UTC) o None si falla (no detiene el proceso)."""
    pedido = urllib.request.Request(
        BCV_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; super-calculadora-ve)",
        },
    )
    for intento in range(1, INTENTOS + 1):
        try:
            with urllib.request.urlopen(pedido, timeout=30) as respuesta:
                datos = json.load(respuesta)
            valor = None
            for campo in ("promedio", "venta", "compra"):
                candidato = datos.get(campo)
                if isinstance(candidato, (int, float)) and candidato > 0:
                    valor = float(candidato)
                    break
            if valor is None:
                raise RuntimeError("DolarAPI no devolvió un valor válido")
            return valor, normalizar_fecha(datos.get("fechaActualizacion"))
        except ERRORES_RED as error:
            print("Intento %d/%d (BCV) falló: %s" % (intento, INTENTOS, error), file=sys.stderr)
            if intento < INTENTOS:
                time.sleep(3 * intento)
    print("Aviso: no se pudo obtener el dólar del BCV; se conserva el último valor guardado.", file=sys.stderr)
    return None


def construir_bcv(valor, fecha_api, anterior_bcv, ahora):
    """Arma el bloque 'bcv' de tasa.json. La variación compara contra el valor anterior distinto
    (el BCV cambia una vez por día hábil, no cada media hora)."""
    anterior_bcv = anterior_bcv or {}
    viejo = anterior_bcv.get("rate")
    if isinstance(viejo, (int, float)) and viejo > 0 and abs(valor - viejo) > 1e-9:
        previo = viejo
        cambio = round((valor / viejo - 1) * 100, 2)
    else:
        previo = anterior_bcv.get("previous_rate")
        cambio = anterior_bcv.get("change_pct")
    return {
        "pair": "USD/VES",
        "source": "BCV (oficial)",
        "rate": round(valor, 4),
        "previous_rate": previo,
        "change_pct": cambio,
        "updated_at": fecha_api,
        "checked_at": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def es_reciente(anterior, ahora):
    """True si el valor guardado se actualizó hace menos de MIN_MINUTOS."""
    try:
        marca = datetime.strptime(anterior.get("updated_at"), "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return False
    edad = (ahora.replace(tzinfo=None) - marca).total_seconds() / 60
    return 0 <= edad < MIN_MINUTOS


def main():
    ahora = datetime.now(timezone.utc)
    anterior = leer_anterior()
    # FORZAR=1 (ejecución manual) siempre consulta; las programadas saltan si el dato es reciente.
    if not os.environ.get("FORZAR") and es_reciente(anterior, ahora):
        print("El valor tiene menos de %d minutos; no se consulta Binance." % MIN_MINUTOS)
        return
    compra = consultar("BUY")
    venta = consultar("SELL")
    nuevo = construir(compra, venta, anterior, datetime.now(timezone.utc))
    # El BCV es secundario: si falla, se conserva el último valor y lo de Binance se guarda igual.
    bcv = consultar_bcv()
    if bcv:
        nuevo["bcv"] = construir_bcv(bcv[0], bcv[1], anterior.get("bcv"), datetime.now(timezone.utc))
    elif anterior.get("bcv"):
        nuevo["bcv"] = anterior["bcv"]
    with open(RUTA, "w", encoding="utf-8") as archivo:
        json.dump(nuevo, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    print("USDT/VES = %s (compra %s, venta %s, cambio %s%%)" % (
        nuevo["rate"], nuevo["buy"], nuevo["sell"], nuevo["change_pct"]))
    if nuevo.get("bcv"):
        print("BCV USD/VES = %s (cambio %s%%, fuente actualizada %s)" % (
            nuevo["bcv"]["rate"], nuevo["bcv"]["change_pct"], nuevo["bcv"]["updated_at"]))


if __name__ == "__main__":
    main()
