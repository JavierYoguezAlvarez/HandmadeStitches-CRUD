import mssql_python
import json
import os
from dotenv import load_dotenv

class ConexionSqlServer():

    def __init__(self):
        load_dotenv()
        self.SERVER = os.environ.get("SERVER_NAME")
        self.DATABASE_NAME = os.environ.get("DATABASE_NAME")
        self.USER = os.environ.get("USER")
        self.PASSWORD = os.environ.get("PASSWORD")

        self.CNX = None # Gestionar la conexion a la base de datos
        self.CURSOR = None # Gestionar las consultas

    def crear_conexion(self):
        # Crear la cadena de conexión
        try:
            cadena_conexion = (
                f"Server={self.SERVER};"
                f"Database={self.DATABASE_NAME};"
                f"UID={self.USER};"
                f"PWD={self.PASSWORD};"
                "Encrypt=yes;"
                "TrustServerCertificate=yes;"
            )
            # Nos conectamos
            self.CNX = mssql_python.connect(cadena_conexion)
            # Creamos CURSOR (en minúsculas)
            self.CURSOR = self.CNX.cursor()
            print(f"Conectado al servidor {self.SERVER}")
            return self.CNX
            
        except mssql_python.Error as e:
            print(f"Error al conectarse al servidor {self.SERVER} de Base de Datos")
            print(e)
            self.CNX = None
            self.CURSOR = None
            return None

    def ejecutar_consulta(self, sql, parametros = None):
        try:
            # Verificar conexión
            if self.CNX is None:
                if self.crear_conexion() is None:
                    return json.dumps(
                        {
                            "estado": False,
                            "mensaje": "No fue posible establecer la conexión"
                        },
                        ensure_ascii=False
                    )

            # Ejecutar consulta
            if parametros:
                self.CURSOR.execute(sql, parametros)
            else:
                self.CURSOR.execute(sql)

            # Identificar operación
            tipo = sql.strip().split()[0].upper()
            
            # SELECT
            if tipo == "SELECT":
                columnas = [columna[0] for columna in self.CURSOR.description]

                # Obtener registros
                registros = self.CURSOR.fetchall()

                resultado = []
                for registro in registros:
                    fila = {}
                    for i, valor in enumerate(registro):
                        fila[columnas[i]] = valor
                    resultado.append(fila)

                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "SELECT",
                        "registros": resultado
                    },
                    default=str,
                    ensure_ascii=False
                )
            # INSERT
            elif tipo == "INSERT":
                filas = self.CURSOR.rowcount
                self.CNX.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "INSERT",
                        "mensaje": "Registro insertado correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
            # UPDATE
            elif tipo == "UPDATE":
                filas = self.CURSOR.rowcount
                self.CNX.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "UPDATE",
                        "mensaje": "Registro actualizado correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
            # DELETE
            elif tipo == "DELETE":
                filas = self.CURSOR.rowcount
                self.CNX.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "DELETE",
                        "mensaje": "Registro eliminado correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
            # OTRAS OPERACIONES
            else:
                filas = self.CURSOR.rowcount
                self.CNX.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": tipo,
                        "mensaje": "Consulta ejecutada correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
        # ERROR DE INTEGRIDAD
        except mssql_python.IntegrityError as e:
            if self.CNX:
                self.CNX.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "IntegrityError",
                    "mensaje": "Violación de integridad en la base de datos",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR DE PROGRAMACIÓN SQL
        except mssql_python.ProgrammingError as e:
            if self.CNX:
                self.CNX.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "ProgrammingError",
                    "mensaje": "Error en la consulta SQL",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR GENERAL
        except mssql_python.Error as e:
            if self.CNX:
                self.CNX.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "DatabaseError",
                    "mensaje": "Error en la base de datos",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR DE PYTHON
        except Exception as e:
            if self.CNX:
                self.CNX.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "Error",
                    "mensaje": "Error inesperado",
                    "error": str(e)
                },
                ensure_ascii=False
            )

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
        
        except mssql_python.Error as e: # Sin paréntesis en la excepción
            print(f"Error al desconectarse al servidor de la Base de Datos")
            print(e)
            return False


if __name__ == '__main__':
    cnn = ConexionSqlServer()
    sql_select = """
                SELECT CustomerID, CompanyName FROM Customers
                """
    result = cnn.ejecutar_consulta(sql_select)
    cnn.cerrar_conexion()

    # Convertir el resultado a diccionario
    result = json.loads(result)
    
    # Validar si fue exitoso antes de buscar registros
    if result.get("estado"):
        for r in result.get("registros", []):
            if r.get("CustomerID") == 'ANATR':
                print(r)
                break
    else:
        print("Error en la consulta:", result)