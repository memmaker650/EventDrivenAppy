# EbD Event Driven

Easy Bank application based in events.
Different bank actions defined, like: 
- Account creation
- MoneyDeposit
- MoneyWithDraw
- Overdraft
- Card Payment
- Money Transfer
- Close Account

In addition of events we have a DB table with actual state of each account.

GUI
2 screens for the moment.
- Screen to generate events
- Screen to see actual state and events of an specific account.


**  Ejemplo uso de Hipoteca : 
-------------------------------
1.- Crear una hipoteca
----
manager = HipotecaManager()

hipoteca_id, cuota = manager.crear_hipoteca(
    capital=200000,
    tasa_anual=3.5,
    fecha_inicio="2025-01-01",
    fecha_fin="2055-01-01"
)

print("Hipoteca:", hipoteca_id)
print("Cuota mensual:", cuota)

==> Salida aproximada:

Hipoteca: ACC-001
Cuota mensual: 898.09


2.- Generar cuadro de amortización
----

meses = manager.meses_entre_fechas(
    "2025-01-01",
    "2055-01-01"
)

cuadro = manager.generar_cuadro_amortizacion(
    capital=200000,
    tasa_anual=3.5,
    cuota=898.09,
    meses=meses
)

for fila in cuadro[:5]:
    print(fila)

3.- Amortización anticipada
---
resultado = manager.amortizacion_anticipada(
    saldo_actual=180000,
    importe_amortizado=10000
)

print(resultado)