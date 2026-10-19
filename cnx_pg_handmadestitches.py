import psycopg
from psycopg.rows import dict_row
from psycopg import IntegrityError, ProgrammingError, Error
import json
import os
from dotenv import load_dotenv

#------------- // JAVIER YOGUEZ ALVAREZ N.C: 24420265 // -----------------


import psycopg
from psycopg.rows import dict_row
from psycopg import IntegrityError, ProgrammingError, Error
import os
from dotenv import load_dotenv

#------------- // JAVIER YOGUEZ ALVAREZ N.C: 24420265 // -----------------


class ConexionPostgres():

    def __init__(self):
        load_dotenv()
        self.SERVER = os.environ.get("PG_SERVER_NAME")
        self.DATABASE_NAME = os.environ.get("PG_DATABASE_NAME")
        self.USER = os.environ.get("PG_USER")
        self.PASSWORD = os.environ.get("PG_PASSWORD")

        self.CNX = None # Gestionar la conexion a la base de datos
        self.CURSOR = None # Gestionar las consultas

    def crear_conexion(self):
        # Crear la cadena de conexión
        try:
            # Nos conectamos
            self.CNX = psycopg.connect(
                host=self.SERVER,
                dbname=self.DATABASE_NAME,
                user=self.USER,
                password=self.PASSWORD,
                row_factory=dict_row
            )
            # Creamos cursor
            self.CURSOR = self.CNX.cursor()
            print(f"Conectado al servidor {self.SERVER}")
            return self.CNX
            #Ya estas conectado
            
        except Error as e:
            print(f"Error al conectarse al servidor {self.SERVER} de Base de Datos")
            print(e)
            self.CNX = None
            self.CURSOR = None
            return None
            # Si falla te manda el error y pone la conexión y el cursor en None
    
    # Metodo para realizar las consultas sql a la base de datos
    def ejecutar_consulta(self, sql, parametros=None):
        try:
            # Verificar la conexión
            if self.CNX is None:
                # Intento conectarme al servidor
                if self.crear_conexion() is None:
                    return {"estado": False, "mensaje": "No fue posible establecer la conexión"}

            # Ejecutar la consulta
            if parametros:
                self.CURSOR.execute(sql, parametros)
            else:
                self.CURSOR.execute(sql)

            # Identificar la conexion: SELECT, INSERT, UPDATE, DELETE
            tipo = sql.strip().split()[0].upper()
            
            # SELECT
            if tipo == "SELECT":
                # Obtener los registros 
                resultado = self.CURSOR.fetchall()

                return {
                    "estado": True,
                    "tipo": "SELECT",
                    "registros": resultado
                }
                
            elif tipo in ["INSERT", "UPDATE", "DELETE"]:
                filas = self.CURSOR.rowcount
                self.CNX.commit()
                mensajes = {
                    "INSERT": "Registro insertado correctamente",
                    "UPDATE": "Registro actualizado correctamente",
                    "DELETE": "Registro eliminado correctamente"
                }
                return {
                    "estado": True,
                    "tipo": tipo,
                    "mensaje": mensajes[tipo],
                    "filas_afectadas": filas
                }
            else:
                filas = self.CURSOR.rowcount
                self.CNX.commit()
                return {"estado": True, "tipo": tipo, "mensaje": "Consulta ejecutada", "filas_afectadas": filas}
                
        except IntegrityError as e:
            if self.CNX: self.CNX.rollback()
            return {"estado": False, "tipo": "IntegrityError", "mensaje": "Violación de integridad", "error": str(e)}
        except ProgrammingError as e:
            if self.CNX: self.CNX.rollback()
            return {"estado": False, "tipo": "ProgrammingError", "mensaje": "Error SQL", "error": str(e)}
        except Error as e:
            if self.CNX: self.CNX.rollback()
            return {"estado": False, "tipo": "DatabaseError", "mensaje": "Error de base de datos", "error": str(e)}
        except Exception as e:
            if self.CNX: self.CNX.rollback()
            return {"estado": False, "tipo": "Error", "mensaje": "Error inesperado", "error": str(e)}

    # Método para cerrar la conexion a la Base de Datos
    def cerrar_conexion(self):
        try:
            if self.CURSOR:
                self.CURSOR.close()
                self.CURSOR = None
            if self.CNX:
                self.CNX.close()
                self.CNX = None
            print(f"Se ha cerrado la conexión al servidor {self.SERVER}")
            return True
        except Error as e:
            print("Error al desconectarse al servidor de la Base de Datos")
            print(e)
            return False

    def __init__(self):
        load_dotenv()
        self.SERVER = os.environ.get("PG_SERVER_NAME")
        self.DATABASE_NAME = os.environ.get("PG_DATABASE_NAME")
        self.USER = os.environ.get("PG_USER")
        self.PASSWORD = os.environ.get("PG_PASSWORD")

        self.CNX = None # Gestionar la conexion a la base de datos
        self.CURSOR = None # Gestionar las consultas

    def crear_conexion(self):
        # Crear la cadena de conexión
        try:
            # Nos conectamos
            self.CNX = psycopg.connect(
                host=self.SERVER,
                dbname=self.DATABASE_NAME,
                user=self.USER,
                password=self.PASSWORD,
                row_factory=dict_row
            )
            # Creamos cursor
            self.CURSOR = self.CNX.cursor()
            print(f"Conectado al servidor {self.SERVER}")
            return self.CNX
            #Ya estas conectado
            
        except Error as e:
            print(f"Error al conectarse al servidor {self.SERVER} de Base de Datos")
            print(e)
            self.CNX = None
            self.CURSOR = None
            return None
            # Si falla te manda el error y pone la conexión y el cursor en None
    
    # Metodo para realizar las consultas sql a la base de datos
    def ejecutar_consulta(self, sql, parametros=None):
        try:
            # Verificar la conexión
            if self.CNX is None:
                # Intento conectarme al servidor
                if self.crear_conexion() is None:
                    return {"estado": False, "mensaje": "No fue posible establecer la conexión"}

            # Ejecutar la consulta
            if parametros:
                self.CURSOR.execute(sql, parametros)
            else:
                self.CURSOR.execute(sql)

            # Identificar la conexion: SELECT, INSERT, UPDATE, DELETE
            tipo = sql.strip().split()[0].upper()
            
            # SELECT
            if tipo == "SELECT":
                # Obtener los registros 
                resultado = self.CURSOR.fetchall()

                return {
                    "estado": True,
                    "tipo": "SELECT",
                    "registros": resultado
                }
                
            elif tipo in ["INSERT", "UPDATE", "DELETE"]:
                filas = self.CURSOR.rowcount
                self.CNX.commit()
                mensajes = {
                    "INSERT": "Registro insertado correctamente",
                    "UPDATE": "Registro actualizado correctamente",
                    "DELETE": "Registro eliminado correctamente"
                }
                return {
                    "estado": True,
                    "tipo": tipo,
                    "mensaje": mensajes[tipo],
                    "filas_afectadas": filas
                }
            else:
                filas = self.CURSOR.rowcount
                self.CNX.commit()
                return {"estado": True, "tipo": tipo, "mensaje": "Consulta ejecutada", "filas_afectadas": filas}
                
        except IntegrityError as e:
            if self.CNX: self.CNX.rollback()
            return {"estado": False, "tipo": "IntegrityError", "mensaje": "Violación de integridad", "error": str(e)}
        except ProgrammingError as e:
            if self.CNX: self.CNX.rollback()
            return {"estado": False, "tipo": "ProgrammingError", "mensaje": "Error SQL", "error": str(e)}
        except Error as e:
            if self.CNX: self.CNX.rollback()
            return {"estado": False, "tipo": "DatabaseError", "mensaje": "Error de base de datos", "error": str(e)}
        except Exception as e:
            if self.CNX: self.CNX.rollback()
            return {"estado": False, "tipo": "Error", "mensaje": "Error inesperado", "error": str(e)}

    # Método para cerrar la conexion a la Base de Datos
    def cerrar_conexion(self):
        try:
            if self.CURSOR:
                self.CURSOR.close()
                self.CURSOR = None
            if self.CNX:
                self.CNX.close()
                self.CNX = None
            print(f"Se ha cerrado la conexión al servidor {self.SERVER}")
            return True
        except Error as e:
            print("Error al desconectarse al servidor de la Base de Datos")
            print(e)
            return False


if __name__ == '__main__':
    cnn = ConexionPostgres()


    # SELECT
    print("\n SELECT")
    sql_select = """
        SELECT C.company_name, O.order_id, P.product_name, 
        OD.quantity, OD.unit_price, OD.discount, 
        ((OD.quantity * OD.unit_price)-(OD.discount * OD.unit_price * OD.quantity)) AS subtotal
        FROM customers C 
        INNER JOIN orders O ON C.customer_id = O.customer_id
        INNER JOIN order_details OD ON O.order_id = OD.order_id
        INNER JOIN products P ON OD.product_id = P.product_id
        WHERE O.order_id = %(order_id)s
    """
    parametros = {"order_id" : 10248}
    result_select = cnn.ejecutar_consulta(sql_select, parametros)
    
    dict_select = result_select
    if dict_select.get("estado"):
        for r in dict_select.get("registros", []):
            print(r)
    else:
        print("Error:", dict_select)

    # INSERT
    print("\n INSERT")
    sql_insert = """
        INSERT INTO Customers (customer_id, company_name) VALUES (%s, %s)
    """
    parametros = ('NUEVO', 'Empresa1')
    result_insert = cnn.ejecutar_consulta(sql_insert, parametros)
    print((result_insert))

    # UPDATE
    print("\n UPDATE")
    sql_update = """
        UPDATE Customers SET company_name = %s WHERE customer_id = %s
    """
    parametros = ('Empresa2', 'NUEVO')
    result_update = cnn.ejecutar_consulta(sql_update, parametros)
    print((result_update))

    # DELETE
    print("\n DELETE")
    sql_delete = """
        DELETE FROM Customers WHERE customer_id = %s
    """
    parametros = ('NUEVO',)
    result_delete = cnn.ejecutar_consulta(sql_delete, parametros)
    print((result_delete))

    cnn.cerrar_conexion()

    