import os
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from email_validator import validate_email, EmailNotValidError

import database
import commands 
import domain
import hypotekas
import daemonInput

logger = logging.getLogger(__name__)

class gestionDatos():
    # Variables para communicación con la UI
    boton_execution = bool

    def __init__(self, app=None):
        self.app = app
        self.manager = hypotekas.HipotecaManager()

    def _actualizar_estado(self, mensaje, tipo):
        if self.app is not None:
            self.app.actualizar_estado(mensaje, tipo)

    def initBusiness(self):
        database.init_db()
        return f"ACC-{database.loadMaxAccountID()+1:03d}"

    def load_accounts(self):
        return database.load_accounts()   

    def load_accountInfo(self, cuentaSelec):
        return database.load_accountInfo(cuentaSelec)    

    def cargaEventosCompletos(self, cuentaSelec):
        return database.load_eventsFull(cuentaSelec)       

    def domainAccount(self, account):
        return domain.load_account(account)  

    def traer_listaNacionalidades(self):
        return database.traer_listaNacionalidades()

    def validar_email(email: str) -> tuple[bool, str]:
        try:
            info = validate_email(email, check_deliverability=False)
            return True, info.normalized
        except EmailNotValidError as e:
            return False, str(e)

    def create_account(self, widget, id_input, ow_input, family=None, idcardnumber=None, email=None, address=None, city=None, nationality=None, desde_eventos=False):
        logging.info("Dentro de create_account.")

        if not desde_eventos:
            campos = {
                "NOMBRE": ow_input,
                "APELLIDOS": family,
                "DNI": idcardnumber,
                "DIRECCIÓN": address,
                "CIUDAD": city,
                "NACIONALIDAD": nationality
                }

            for nombre, valor in campos.items():
                if valor is None or valor == "":
                    self._actualizar_estado(f"Error!!! Cuenta NO creada, {nombre} NO rellenado.", "Error")
                    return False
        elif not ow_input:
            self._actualizar_estado("Error!!! Cuenta NO creada, NOMBRE NO rellenado.", "Error")
            return False

        if self.boton_execution and not desde_eventos:
            cmd = commands.CreateAccount(
                id_input,
                ow_input,
                family or "",
                idcardnumber or "",
            )
            domain.handle_create_account(cmd)

        flag = database.crearCuenta(
            id_input,
            ow_input,
            family or "",
            idcardnumber or "",
            email or "",
            address or "",
            city or "",
            nationality or "",
        )

        if flag:
            self._actualizar_estado("Cuenta creada", "OK")
            logger.info("Cuenta creada")
        else:
            self._actualizar_estado("ERROR ! Cuenta NO CREADA", "Error")
            logger.error("ERROR ! Cuenta NO CREADA")
        return flag

    def create_account_block(self, id_input, ow_input):
        logging.info("Dentro de create_account_block.")

        if isinstance(ow_input, str):
            owner = ow_input
        else:
            if ow_input is not None:
                owner = ow_input.value
            else:
                owner = "Desconocido"

        print("Owner: ", owner)
        print("ACC-id: ", id_input)

        if not owner:
            self.label_info.text = "Debe indicar un nombre"
            print("Debe indicar un nombre")
            return

        self.account_id = id_input  

        flag = database.crearCuenta(self.account_id, owner)

        if flag:
            self._actualizar_estado("Cuenta creada", "OK") 
        else:
            self._actualizar_estado("ERROR ! Cuenta NO CREADA", "Error")   

    def ejecutarAccion(self, widget, accion, origen, cantidad, destino=None, tienda=None, propietario=None, apellidos=None, doc_id=None, email=None, address=None, city=None, nationality=None, mortgage_id = None, credit_id = None, return_period = None, rate=None, dateInicio=None):
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

        if accion == "crear" or accion == "AccountCreated":
            if propietario == "":
                self._actualizar_estado("Introducir Nombre Titular.", "Error")
            else:
                self.create_account(
                    None,
                    origen,
                    propietario,
                    apellidos,
                    doc_id,
                    email,
                    address,
                    city,
                    nationality,
                    desde_eventos=(accion == "AccountCreated"),
                )

        elif accion == "depositar" or accion == "MoneyDeposited":
            print("Jump-2_handle_deposit")
            cmd = commands.DepositMoney(
                origen,
                cantidad
            )

            domain.handle_deposit(cmd)
        elif accion == "retirar" or accion == "Moneywithdraw":
            print("Jump-2_handle_withdraw")
            cmd = commands.MoneyWithDraw(
                origen,
                cantidad
            )

            domain.handle_withdraw(cmd)

        elif accion == "pedir_hipoteca" or accion == "demandMortgage":
            print("Jump-2_handle_DemandMortgage")

            hyp_id = database.generar_id_hypoteka()

            cmd = commands.DemandMortgage(
                origen,
                hyp_id,
                rate,
                cantidad,
                return_period,
                dateInicio if dateInicio is not None else datetime.now().isoformat(timespec='seconds')
            )

            fecha_futura = datetime.now() + relativedelta(years=int(return_period))
            if origen == None: 
                self._actualizar_estado("No hay cuenta asociada", "Error")
            else:
                domain.handle_demandMortgage(cmd)
                self.manager.crear_hipoteca(origen, cantidad, rate, datetime.now(), fecha_futura) 
        
        elif accion == "pago_hipoteca" or accion == "demandMortgage":
            print("Jump-2_handle_MortgagePayment")

            hyp_id = database.buscar_hypoteka_asociadaCuenta(origen)
            print("hyp_id: ", hyp_id)

            cmd = commands.MortgagePayment(
                hyp_id[0],
                cantidad,
                dateInicio if dateInicio is not None else datetime.now().isoformat(timespec='seconds')
            )

            domain.handle_mortgagePayment(cmd)

        elif accion == "pedir_crédito" or accion == "demandCredit":
            print("Jump-2_handle_DemandCredit")

            credit_id = database.generar_id_credito()

            cmd = commands.DemandCredit(
                origen,
                credit_id,
                rate,
                cantidad,
                return_period,
                dateInicio if dateInicio is not None else datetime.now().isoformat(timespec='seconds')
            )
            
            fecha_futura = datetime.now() + relativedelta(years=int(return_period))
            if origen == None: 
                self._actualizar_estado("No hay cuenta asociada", "Error")
            else:
                domain.handle_demandCredit(cmd)
                self.manager.crear_hipoteca(origen, cantidad, rate, datetime.now(), fecha_futura, 1)  # 1 porque es un crédito. 
            
        elif accion == "pago_crédito" or accion == "CreditPayment":
            print("Jump-2_handle_CreditPayment")

            credit_id = database.buscar_credito_asociadaCuenta(origen)
            if not credit_id:
                self._actualizar_estado("No hay crédito asociado", "Error")
            else:
                cmd = commands.CreditPayment(
                    credit_id[0],
                    cantidad,
                    dateInicio if dateInicio is not None else datetime.now().isoformat(timespec='seconds')
                )

                domain.handle_CreditPayment(cmd)

        elif accion == "transferencia" or accion == "MoneyTransfer":
            print("Jump-2_handle_MoneyTransfer")
            cmd = commands.TransferMoney(
                origen,
                cantidad,
                destino
            )

            domain.handle_moneyTransfer(cmd)    

        elif accion == "pago_tarjeta" or accion == "CardPayment":
            print("Jump-2_handle_CardPayment")
            cmd = commands.CardPayment(
                origen,
                cantidad,
                tienda
            )

            domain.handle_CardPayment(cmd)    

        elif accion == "cerrar" or accion == "CloseAccount":
            cmd = commands.CloseAccount(
                origen
            )

            domain.handle_close_account(cmd)

        # self.refresh_balance()
        self.boton_execute = False

        print("FIN de ejecutarAccion.")  
    
    def gestionCuentaAlDia(self, accion, cantidad):
        logging.info("into de gestion Cuenta Al Dia.")
        print("into de gestion Cuenta Al Dia.")

        if accion.value == "crear":
            self.create_account()

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
            account_id = database._as_id(x)
            datos = database.load_accountInfo(account_id)

            if not datos:      # datos == []
                print("La cuenta no existe")
                print("ID no creado:", account_id)
                duegno = database.load_ownerForAccountInEvent(account_id)
                print("Dueño: ", duegno)
                self.create_account_block(account_id, duegno)

            montante = 0.0
            print("Dentro cálculo montante FINAL.")
            cargas = database.load_moneyForAccountInEvent(account_id)
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

            resultado = database.store_moneyForAccount(montante, account_id)
            if resultado == 1:
                self.label_info = "Montante actualizado !!"
            else:
                self.label_info = "Error guardado Montante - KO !!"

        print("TERMINADO TRATAMIENTO EN BLOQUE !!")
        logging.info("TERMINADO TRATAMIENTO EN BLOQUE !!")
        self.label_info = ("TERMINADO TRATAMIENTO EN BLOQUE !!")

    def listar_hypotecasCreditos_asociados(self, origen, tipo):
        if tipo == "hip":
            return database.listar_hypotecasCreditos_asociados(origen, 0)
        else: 
            return database.listar_hypotecasCreditos_asociados(origen, 1)

    def traer_Info_CreditoHypoteka(self, hip_id):
        logging.info("Trer info completa: pagos Hipoteca.")

        info = database.obtenerInfoCreditoHypoteka(hip_id)
        return info

    def traer_EventosPago_CreditoHypoteka(self, hip_id, tipo):
        logging.info("Trer info completa: pagos Hipoteca.")

        info = database.load_eventsOfType(hip_id, tipo)
        processJSON = daemonInput.ProcesadoDatosDemonio()
        resultArray = []
        for inf in info:
            dataJSON = processJSON.leerDatosJSON(inf[2])
            resultArray.append(processJSON.procesar_json_hypCred(dataJSON))
        
        print("resultArray:", resultArray)
        return resultArray

    # Método para lanzar Batch tratamiento Eventos y actualizar DB si necesario.
    #--------------------------------------------------------------------------------------
    def lanzar_BatchTratarEventos(self, widget):
        logger.info("Dentro Batch Tratar Eventos Update DB")

        PdD = daemonInput.ProcesadoDatosDemonio()
        PdD.procesar_EventosDB()

        return True