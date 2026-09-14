import sqlite3
from datetime import datetime
import database


class HipotecaManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.crear_tablas()

    def crear_tablas(self):
        database.create_hipotecasTable()
        database.create_amortizaciones_anticipadasTable()

    def generar_id(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT id
        FROM hipotecas
        ORDER BY id DESC
        LIMIT 1
        """)

        ultimo = cursor.fetchone()

        if not ultimo:
            return "ACC-001"

        numero = int(ultimo[0].split("-")[1]) + 1

        return f"ACC-{numero:03d}"

    def meses_entre_fechas(self, inicio, fin):

        fecha_inicio = datetime.strptime(inicio, "%Y-%m-%d")
        fecha_fin = datetime.strptime(fin, "%Y-%m-%d")

        return (
            (fecha_fin.year - fecha_inicio.year) * 12
            + fecha_fin.month
            - fecha_inicio.month
        )

    def calcular_cuota(self, capital, tasa_anual, meses):

        tasa_mensual = tasa_anual / 100 / 12

        cuota = (
            capital
            * tasa_mensual
            * (1 + tasa_mensual) ** meses
        ) / (
            (1 + tasa_mensual) ** meses - 1
        )

        return round(cuota, 2)

    def crear_hipoteca(self, capital, tasa_anual, fecha_inicio, fecha_fin):
        meses = self.meses_entre_fechas(
            fecha_inicio,
            fecha_fin
        )

        cuota = self.calcular_cuota(
            capital,
            tasa_anual,
            meses
        )

        hipoteca_id = self.generar_id()

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO hipotecas
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            hipoteca_id,
            capital,
            tasa_anual,
            fecha_inicio,
            fecha_fin,
            cuota
        ))

        self.conn.commit()

        return hipoteca_id, cuota

    def generar_cuadro_amortizacion(self, capital, tasa_anual, cuota, meses):

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

    def guardar_amortizacion(self, hipoteca_id, fecha, importe):
        comision = round(importe * 0.005, 2)

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO amortizaciones_anticipadas
        (
            hipoteca_id,
            fecha,
            importe,
            comision
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            hipoteca_id,
            fecha,
            importe,
            comision
        ))

        self.conn.commit()

        return comision

    import math

    def reducir_plazo_manteniendo_cuota(self, saldo_actual, importe_amortizado, cuota_actual, tasa_anual):
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
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT saldo_actual,
                cuota_mensual,
                tasa_anual
            FROM hipotecas
            WHERE id = ?
        """, (hipoteca_id,))

        fila = cursor.fetchone()

        if not fila:
            raise ValueError("Hipoteca no encontrada")

        saldo_actual, cuota, tasa = fila

        resultado = self.reducir_plazo_manteniendo_cuota(
            saldo_actual=saldo_actual,
            importe_amortizado=importe_amortizado,
            cuota_actual=cuota,
            tasa_anual=tasa
        )

        cursor.execute("""
            UPDATE hipotecas
            SET saldo_actual = ?,
                meses_restantes = ?
            WHERE id = ?
        """,
        (
            resultado["nuevo_saldo"],
            resultado["meses_restantes"],
            hipoteca_id
        ))

        cursor.execute("""
            INSERT INTO amortizaciones_anticipadas(
                hipoteca_id,
                fecha,
                importe,
                comision
            )
            VALUES(
                ?, date('now'), ?, ?
            )
        """,
        (
            hipoteca_id,
            importe_amortizado,
            resultado["comision"]
        ))

        self.conn.commit()

        return resultado