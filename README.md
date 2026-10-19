# HandmadeStitches - Aplicación CRUD

Aplicación de escritorio en Python para gestionar información de HandmadeStitches mediante una interfaz gráfica (Tkinter) y un menú de consola, con conexión a **PostgreSQL** o **SQL Server**.

## Archivos principales

- `menu_cmd.py`: aplicación en consola.
- `menu_grafico.py`: interfaz gráfica con Tkinter.
- `cnx_pg_handmadestitches.py`: conexión a PostgreSQL.
- `cnx_ss_handmadestitches.py`: conexión a SQL Server.
- `ScriptHandmadeStitchesPG.sql`: esquema SQL para PostgreSQL.
- `ScriptHandmadeStitchesSS.sql`: esquema SQL para SQL Server.
- `requirements.txt`: dependencias de Python.
- `.env.example`: ejemplo de configuración sin contraseñas reales.

## Requisitos previos

- Python (el entorno de desarrollo original utiliza Python 3.12).
- PostgreSQL o SQL Server instalado o accesible, con sus credenciales.
- Windows recomendado para ejecución gráfica; Tkinter suele venir incluido con Python en Windows.

## Instalación (CMD en Windows)

Abre CMD en la carpeta del proyecto y ejecuta:

```cmd
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Los paquetes declarados son `mssql-python`, `psycopg`, `psycopg-binary` y `python-dotenv`. No se incluye `.venv` porque debe generarse en cada equipo.

## Configurar la base de datos

1. Crea y configura la base de datos con el script correspondiente al gestor elegido.
   - PostgreSQL: `ScriptHandmadeStitchesPG.sql`.
   - SQL Server: `ScriptHandmadeStitchesSS.sql`.
2. Copia `.env.example` como `.env`.
3. Edita las variables del gestor que utilizarás con los datos reales de tu servidor.
4. Guarda `.env` en la misma carpeta donde están los menús.

> **Seguridad:** el archivo `.env` contiene credenciales, por lo que no debe subirse al repositorio. El archivo `.env.example` solo tiene valores de muestra.

## Ejecutar los menús

```cmd
python menu_cmd.py
```

O bien:

```cmd
python menu_grafico.py
```

Las pantallas permiten elegir el motor de base de datos al conectarse.

## Nota para la entrega

Este repositorio contiene el código fuente, los scripts de creación de base de datos y las dependencias necesarias para reproducir el entorno local. No incluye el entorno virtual ni las credenciales privadas. La instalación y disponibilidad del servidor de base de datos son necesarias para probar las operaciones del sistema.
