import os
import logging

import database
from commands import CreateAccount, DepositMoney, MoneyWithDraw, TransferMoney, CardPayment, Overdraft
from domain import (
    handle_create_account,
    handle_deposit,
    handle_withdraw,
    handle_moneyTransfer,
    handle_CardPayment,
    handle_close_account,
    load_account
)

logger = logging.getLogger(__name__)

class gestionDatos():
    # Variables para communicación con la UI
    boton_execution = bool

    def initBusiness(self):
        database.init_db()
        return f"ACC-{database.loadMaxAccountID()+1:03d}"

    def load_accounts(self):
        return database.load_accounts()   

    def create_account(self, widget, id_input, ow_input):
        logging.info("Dentro de create_account.")
        if isinstance(ow_input, str):
            owner = ow_input
        else:
            if ow_input is not None:
                owner = ow_input.value
            else:
                self.label_info.text = "Error Crear Cuenta, dueño no rellenado." 
                return
        print("Owner: ", owner)
        print("ACC-id: ", id_input)

        if not owner:
            self.label_info.text = "Debe indicar un nombre"
            print("Debe indicar un nombre")
            return
        
        # self.account_id = id_input.value   
        
        if self.boton_execution:
            cmd = CreateAccount(
                id_input,
                owner
            )

            resul = handle_create_account(cmd)

            # self.account_selector.items = database.load_accounts()
        database.crearCuenta(id_input, owner)

        # self.refresh_balance()
        # self.gestion_mensaje_info(resul)

    def create_account_block(self, id_input, ow_input):
        logging.info("Dentro de create_account_block.")
        if isinstance(ow_input, str):
            owner = ow_input
        else:
            if ow_input is not None:
                owner = ow_input.value
            else:
                self.label_info.text = "Error Crear Cuenta, dueño no rellenado." 
                return
        print("Owner: ", owner)
        print("ACC-id: ", id_input)

        if not owner:
            self.label_info.text = "Debe indicar un nombre"
            print("Debe indicar un nombre")
            return

        self.account_id = id_input  

        database.crearCuenta(self.account_id, owner)

        # self.refresh_balance()
        # self.gestion_mensaje_info(resul)    

    def ejecutarAccion(self, widget, accion, origen, cantidad, destino, propietario, tienda):
        logging.info("into de ejecutarAccion.")
        print("into de ejecutarAccion.")
        # print("into de ejecutarAccion.")
        # print("------------------------------")
        # print("Acció: ", accion.value)
        # print("Origen: ", origen.value)
        # print("Cantidad: ", cantidad.value)
        print("Destino: ", destino)

        self.boton_execute = True

        # self.account_id = self.account_selector.value

        if accion == "crear":
            if propietario == "":
                # Cambiarolo xq no podemos lanzar esto directamente a la GUI así
                self.label_info.text("Introducir Nombre Titular.")
            else:
                self.create_account(None, origen, propietario)

        elif accion == "depositar":
            print("Jump-2_handle_deposit")
            cmd = DepositMoney(
                origen,
                cantidad
            )

            handle_deposit(cmd)
        elif accion == "retirar":
            print("Jump-2_handle_withdraw")
            cmd = MoneyWithDraw(
                origen,
                cantidad
            )

            handle_withdraw(cmd)

        elif accion == "transferencia":
            print("Jump-2_handle_MoneyTransfer")
            cmd = TransferMoney(
                origen,
                cantidad,
                destino
            )

            handle_moneyTransfer(cmd)    

        elif accion == "pago_tarjeta":
            print("Jump-2_handle_CardPayment")
            cmd = CardPayment(
                origen,
                cantidad,
                tienda
            )

            handle_CardPayment(cmd)    

        elif accion == "cerrar":
            cmd = CloseAccount(
                origen
            )

            handle_close_account(cmd)

        # self.refresh_balance()
        self.boton_execute = False

        print("FIN de ejecutarAccion.")  
    
    def gestionCuentaAlDia(self, accion, cantidad):
        logging.info("into de gestion Cuenta Al Dia.")
        print("into de gestion Cuenta Al Dia.")

        if accion.value == "crear":
            create_account()

        elif accion.value == "depositar":
            print("Jump-2_handle_deposit")
 
        elif accion.value == "retirar":
            print("Jump-2_handle_withdraw")


        elif accion.value == "transferencia":
            print("Jump-2_handle_Transfer")

        elif accion.value == "cerrar":
            print("Jump-2_handle_Transfer")

    # Método para calcular a partir de los eventos que la tabla ACCOUNTS está al día.
    #--------------------------------------------------------------------------------------
    def calculoEventosACuenta(self, widget):    
        logging.info("Calculo Eventos A Cuenta.")
        print("Calculo Eventos A Cuenta")
        
        # Traer info de la tabla Eventos.
        idsEvents = database.load_diffIDAccountInEvents()
        print(idsEvents)

        for x in idsEvents:
            datos = database.load_accountInfo(x)

            if not datos:      # datos == []
                print("La cuenta no existe")
                x = x[0]
                print("ID no creado:", x)
                duegno = database.load_ownerForAccountInEvent(x)
                print("Dueño: ", duegno)
                self.create_account_block(x, duegno)
            else:
                montante = 0.0
                print("Dentro cálculo montante FINAL.")
                # Cuenta creada, cálculo del montante de la cuenta.
                cargas = database.load_moneyForAccountInEvent(x)
                if cargas is None:
                    logging.info("Es None")
                elif not cargas:
                    logging.info("Está vacío")
                else:
                    for nombre, valor in cargas:
                        if nombre == "MoneyDeposited":
                            montante += float(valor)
                        else:
                            montante -= float(valor)

                resultado = database.store_moneyForAccount(montante, x)
                if resultado == 1:
                    self.label_info = "Montante actualizado !!"
                else:
                    self.label_info = "Error guardado Montante - KO !!"

        
        print("TERMINADO TRATAMIENTO EN BLOQUE !!")
        logging.info("TERMINADO TRATAMIENTO EN BLOQUE !!")
        self.label_info = ("TERMINADO TRATAMIENTO EN BLOQUE !!")

    def gestion_mensaje_info (self, resultado):
        logging.info("gestion_mensaje_info")
        if resultado["ok"]: 
            estadoApp = "ok"
            self.label_info.text = resultado["mensaje"]
            self.label_info.style.color = "green"
        else:
            estadoApp = "error"
            self.label_info.text = "¡ ERROR !" + " " + resultado["mensaje"],
            self.label_info.style.color = "red"