import sqlite3
from datetime import datetime
import database
import math

import logging

logger = logging.getLogger(__name__)

class HipotecaManager:
    def __init__(self):
        database.init_db()

    def meses_entre_fechas(self, fecha_inicio, fecha_fin):
        logger.info("Método cálculo entre fechas.")

        return (
            (fecha_fin.year - fecha_inicio.year) * 12
            + fecha_fin.month
            - fecha_inicio.month
        )

    def calcular_cuota(self, capital, tasa_anual, meses):
        logger.info("Método cálculo CUOTAS.")

        tasa_anual = float(tasa_anual.replace(',', '.')) # Convierto la coma en . si viene así
        tasa_anual = float(tasa_anual)
        capital = float(capital)
        meses = float(meses)

        tasa_mensual = tasa_anual / 100 / 12

        cuota = (capital * tasa_mensual * (1 + tasa_mensual) ** meses) / ((1 + tasa_mensual) ** meses - 1)

        return round(cuota, 2)

    def crear_hipoteca(self, origen, capital, tasa_anual, fecha_inicio, fecha_fin, credito=0):
        logger.info("Crear Hypoteka")

        meses = self.meses_entre_fechas(
            fecha_inicio,
            fecha_fin
        )

        cuota = self.calcular_cuota(
            capital,
            tasa_anual,
            meses
        )

        print("Cuota: ", cuota)
        

        if credito != 0:
            # Asignar hipoteca a la cuenta asociada.
            hipoteca_id = database.generar_id_credito()
            database.cargar_nuevaHypoteka(origen, hipoteca_id, capital, tasa_anual, fecha_inicio, fecha_fin, cuota, meses, 1)
        else:
            # Asignar hipoteca a la cuenta asociada.
            hipoteca_id = database.generar_id_hypoteka()
            database.cargar_nuevaHypoteka(origen, hipoteca_id, capital, tasa_anual, fecha_inicio, fecha_fin, cuota, meses)

        return hipoteca_id, cuota

    def generar_cuadro_amortizacion(self, capital, tasa_anual, cuota, meses):
        logger.info("Método generar cuadro Amortización")

        tasa_mensual = tasa_anual / 100 / 12

        saldo = capital

        cuadro = []

        for periodo in range(1, meses + 1):

            interes = saldo * tasa_mensual

            amortizacion = cuota - interes

            saldo -= amortizacion

            if saldo < 0:
                saldo = 0

            cuadro.append({
                "cuota": periodo,
                "pago": round(cuota, 2),
                "interes": round(interes, 2),
                "amortizacion": round(amortizacion, 2),
                "pendiente": round(saldo, 2)
            })

        return cuadro

    def amortizacion_anticipada(self, saldo_actual, importe_amortizado):
        logger.info("Método amortización Anticipada.")

        comision = importe_amortizado * 0.005

        nuevo_saldo = saldo_actual - importe_amortizado

        if nuevo_saldo < 0:
            nuevo_saldo = 0

        return {
            "importe_amortizado": round(
                importe_amortizado,
                2
            ),
            "comision": round(
                comision,
                2
            ),
            "saldo_restante": round(
                nuevo_saldo,
                2
            )
        }

    def reducir_plazo_manteniendo_cuota(self, saldo_actual, importe_amortizado, cuota_actual, tasa_anual):
        logger.info("Método reducir plazo manteniendo cuota")

        # Comisión 0,5%
        comision = round(
            importe_amortizado * 0.005,
            2
        )

        nuevo_saldo = saldo_actual - importe_amortizado

        if nuevo_saldo <= 0:
            return {
                "nuevo_saldo": 0,
                "meses_restantes": 0,
                "comision": comision,
                "hipoteca_cancelada": True
            }

        tasa_mensual = tasa_anual / 100 / 12

        meses_restantes = math.ceil(
            math.log(
                cuota_actual /
                (cuota_actual - nuevo_saldo * tasa_mensual)
            ) /
            math.log(1 + tasa_mensual)
        )

        return {
            "nuevo_saldo": round(nuevo_saldo, 2),
            "meses_restantes": meses_restantes,
            "cuota": round(cuota_actual, 2),
            "comision": comision,
            "hipoteca_cancelada": False
        }

    def aplicar_amortizacion_reduciendo_plazo(self, hipoteca_id, importe_amortizado):
        logger.info("Método aplicar amortizacion reduciendo plazo")

        fila = database.buscar_hypoteka(hipoteca_id)

        if not fila:
            raise ValueError("Hipoteca no encontrada")

        saldo_actual, cuota, tasa = fila

        resultado = self.reducir_plazo_manteniendo_cuota(
            saldo_actual=saldo_actual,
            importe_amortizado=importe_amortizado,
            cuota_actual=cuota,
            tasa_anual=tasa
        )

        database.actualizar_hypotekaAmortizacion(resultado, hipoteca_id, importe_amortizado)

        return resultado