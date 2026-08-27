import time
import shutil
import os
import json
import sqlite3
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

import database
import gestionDatos

logger = logging.getLogger(__name__)

carpeta_entrada = r"C:\Users\Jorge.Vega\Documents\ENABLON-proj\PROYECTOS\EbD\EventDrivenApplication\datos\entrada"
carpeta_tratados = r"C:\Users\Jorge.Vega\Documents\ENABLON-proj\PROYECTOS\EbD\EventDrivenApplication\datos\tratados"
carpeta_error =r"C:\Users\Jorge.Vega\Documents\ENABLON-proj\PROYECTOS\EbD\EventDrivenApplication\datos\error"

fichero = str

class MiHandler(FileSystemEventHandler):

    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"Nuevo fichero: {event.src_path}")
            print(f"Nuevo fichero: {event.src_path}")
            PDDx = ProcesadoDatosDemonio()
            PDDx.procesar_fichero(event.src_path)

class ProcesadoDatosDemonio():
    aggregate_id = str()
    event_type = str()
    event_data = {}
    account = str()
    amount = float()
    destiny = str()
    owner = str()

    def procesar_fichero(self, ruta):
        print(f"Procesando {ruta}")
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        try:
            for evento in datos:
                print(evento)

                self.procesar_json(evento)
                print("Ruta origen: ", ruta)
                print("Ruta destiy: ", os.path.join(carpeta_tratados, fichero))
                gDd = gestionDatos.gestionDatos()
                gDd.ejecutarAccion(None, self.event_type, self.aggregate_id, self.amount, self.destiny, self.owner)
            shutil.move(ruta, os.path.join(carpeta_tratados, fichero))
        except Exception as e:
            print(f"Error: {e}")
            shutil.move(ruta, os.path.join(carpeta_error, fichero))

        logging.info("Fin Procesado Fichero f{ruta}")

    def procesar_json(self, datos):
        logger.info("procesar_json")
        print("procesar_json")

        self.aggregate_id = datos.get("aggregate_id")
        self.event_type = datos.get("event_type") 

        self.event_data = datos.get("event_data", {})
        self.account = self.event_data.get("account")
        self.amount = float(self.event_data.get("amount", 0))
        self.owner = self.event_data.get("owner")
        self.destiny = self.event_data.get("destiny")

        print("FIN procesar_json")

if __name__ == "__main__":

    for file in os.listdir(carpeta_entrada):
        if file.endswith(".json"):
            fichero = file
            PDD = ProcesadoDatosDemonio()
            PDD.procesar_fichero(os.path.join(carpeta_entrada, fichero))

    observer = Observer()
    observer.schedule(MiHandler(), carpeta_entrada, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()