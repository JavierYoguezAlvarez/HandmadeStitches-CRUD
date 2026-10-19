import calendar
import contextlib
import datetime
import hashlib
import io
import json
import os
import re
import secrets
import tkinter as tk
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from tkinter import ttk

F = "Segoe UI"   # si no existe, Tk usa una fuente similar

# ============================================================
#   TEMAS
# ============================================================
TEMAS = {
    "Rosa Crochet": dict(bg="#14111f", panel="#1d1830", panel2="#2a2245", text="#f4efff", muted="#9d96bd",
                         border="#3d3460", g=("#ff6fb5", "#b57cff", "#6e8bff"), ok="#6ee7a0", warn="#ffd666",
                         err="#ff6b7f", info="#64d2ff", odd="#1d1830", even="#241d3b", sel="#4b3180", btn_text="#14111f"),
    "Océano":       dict(bg="#0c1624", panel="#12233a", panel2="#1b3350", text="#eaf6ff", muted="#8aa6c4",
                         border="#2b4a6e", g=("#00e0ff", "#4a8cff", "#9a5cff"), ok="#5eeaa8", warn="#ffd666",
                         err="#ff6b7f", info="#64d2ff", odd="#12233a", even="#162b46", sel="#245a94", btn_text="#0c1624"),
    "Bosque":       dict(bg="#0e1a16", panel="#14261f", panel2="#1e382e", text="#eafff4", muted="#8fb3a2",
                         border="#2f5546", g=("#a6ff78", "#28dc96", "#1e96dc"), ok="#6ee7a0", warn="#ffd666",
                         err="#ff6b7f", info="#64d2ff", odd="#14261f", even="#183029", sel="#23684f", btn_text="#0e1a16"),
    "Claro":        dict(bg="#f7f3ff", panel="#ffffff", panel2="#efe9ff", text="#2b2540", muted="#7a7396",
                         border="#d9d0f0", g=("#ff5fa8", "#9b6bff", "#4d7cff"), ok="#16a766", warn="#d99a00",
                         err="#e5415a", info="#1a9ad6", odd="#ffffff", even="#f6f1ff", sel="#e0d2ff", btn_text="#ffffff"),
}
P = dict(TEMAS["Rosa Crochet"])
TEMA_ACTUAL = "Rosa Crochet"


def aplicar_tema(nombre):
    global P, TEMA_ACTUAL
    P = dict(TEMAS[nombre])
    TEMA_ACTUAL = nombre


def color(clave):
    return {"g0": P["g"][0], "g1": P["g"][1], "g2": P["g"][2], "ok": P["ok"], "info": P["info"],
            "warn": P["warn"], "err": P["err"]}[clave]


def h2r(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def r2h(t):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in t)


def mezcla(stops, t):
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    a, b = h2r(stops[i]), h2r(stops[i + 1])
    return r2h(tuple(a[k] + (b[k] - a[k]) * f for k in range(3)))


def aclarar(h, f=0.18):
    r = h2r(h)
    return r2h(tuple(v + (255 - v) * f for v in r))


def es_true(v):
    return str(v).strip().lower() in ("true", "1", "t", "yes", "si", "sí")


def a_datetime(v):
    """Convierte datetime / texto de la BD a datetime (o None)."""
    if isinstance(v, datetime.datetime):
        return v
    if isinstance(v, datetime.date):
        return datetime.datetime(v.year, v.month, v.day)
    if not v:
        return None
    try:
        return datetime.datetime.fromisoformat(str(v).replace("T", " ")[:19])
    except ValueError:
        return None


def hash_password(pwd, iteraciones=120000):
    """Mismo formato que los datos de ejemplo del script SQL: pbkdf2_sha256$iter$sal$hash"""
    sal = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), sal, iteraciones)
    return f"pbkdf2_sha256${iteraciones}${sal.hex()}${dk.hex()}"


# ============================================================
#   ACCESO A DATOS
# ============================================================
class ErrorBD(Exception):
    pass


def mensaje_error(res):
    t = str(res.get("error") or "").lower()
    if res.get("tipo") == "IntegrityError":
        if "unique" in t or "duplic" in t:
            return "Ya existe un registro con ese valor (campo único duplicado)."
        if "foreign key" in t or "reference" in t:
            return "El registro está relacionado con otros datos."
        if "check" in t:
            return "Algún valor no cumple las reglas de la tabla."
        if "null" in t:
            return "Falta un dato obligatorio."
    return res.get("mensaje") or "Error en la base de datos."


class BD:
    """Envuelve ConexionPostgres / ConexionSqlServer."""

    def __init__(self, cnn, es_pg):
        self.cnn, self.es_pg = cnn, es_pg
        self.motor = "PostgreSQL" if es_pg else "SQL Server"

    def _run(self, sql, params=None):
        if self.es_pg:
            sql = sql.replace("?", "%s")
        res = self.cnn.ejecutar_consulta(sql, params or None)
        res = json.loads(res) if isinstance(res, str) else res
        if not res.get("estado"):
            raise ErrorBD(mensaje_error(res))
        return res

    def p(self, v):
        """Convierte parámetros: bool -> int en SQL Server (bit)."""
        return int(v) if (isinstance(v, bool) and not self.es_pg) else v

    def consultar(self, sql, params=None):
        res = self._run(sql, tuple(self.p(x) for x in params) if params else None)
        return [{k.lower(): v for k, v in r.items()} for r in res.get("registros", [])]

    def uno(self, sql, params=None):
        filas = self.consultar(sql, params)
        return filas[0] if filas else None

    def modificar(self, sql, params=None):
        res = self._run(sql, tuple(self.p(x) for x in params) if params else None)
        return res.get("filas_afectadas", 0)

    def cerrar(self):
        try:
            self.cnn.cerrar_conexion()
        except Exception:
            pass
        self.cnn.PASSWORD = None      # no dejamos la contraseña en memoria al cerrar sesión


# ============================================================
#   METADATOS DE LAS TABLAS MAESTRAS
# ============================================================
@dataclass
class Campo:
    col: str
    label: str
    tipo: str = "text"      # text, longtext, password, int, decimal, bool, choice, fk, date, datetime
    req: bool = True
    max: int = 0
    minlen: int = 0
    opciones: tuple = ()
    fk: tuple = ()          # (tabla, columna_id, expresión_etiqueta)
    unico: bool = False     # fk: al agregar, ofrece solo los valores que aún no se usan en esta tabla (1:1)
    default: object = None
    min: float = None
    maxv: float = None
    min_excl: bool = False
    patron: str = ""
    msg_patron: str = ""
    ayuda: str = ""


@dataclass
class Meta:
    key: str
    titulo: str
    singular: str
    icono: str
    color: str
    tabla: str
    pk: object               # "Id_X" o ("Id_A", "Id_B") para llaves compuestas
    descripcion: str
    lista_sql: str
    columnas: list           # (llave, encabezado, ancho, ancla, tipo)
    campos: list
    grupo: str = ""
    iid_keys: tuple = ("id",)                      # llaves de la fila que identifican el registro
    stats: list = field(default_factory=list)      # (etiqueta, sql, tipo, color, params[False|True|callable])
    bloqueos: list = field(default_factory=list)   # (tabla, columna, texto) impiden eliminar
    cascada: list = field(default_factory=list)    # (tabla, columna) se eliminan junto con el registro
    acciones: list = field(default_factory=list)   # (texto, color, función(página, iid)) acciones rápidas
    tag_fila: object = None
    proceso: object = None   # función(fila) para agregar columnas calculadas
    antes: object = None     # función(vals, ctx) antes de guardar
    despues: object = None   # función(ctx) después de guardar
    validar: object = None   # función(vals, ctx) -> {col: error}
    msg_unico: str = ""      # mensaje amigable cuando se viola un UNIQUE
    fem: bool = False        # género gramatical (para los mensajes)


def pk_cols(m):
    return list(m.pk) if isinstance(m.pk, (tuple, list)) else [m.pk]


def where_pk(m):
    return " AND ".join(f"{c} = ?" for c in pk_cols(m))


def iid_de(m, fila):
    return "|".join(str(fila.get(k)) for k in m.iid_keys)


def pk_params(m, iid):
    return [int(x) for x in str(iid).split("|")]


EMAIL = r"[^@\s]+@[^@\s]+\.[^@\s]+"
TEL = r"[0-9+\- ]{7,15}"
NOMBRE_U = "RTRIM(CONCAT(U.Nombre, ' ', U.Ap_Paterno, ' ', COALESCE(U.Ap_Materno, '')))"


# ---------- hooks de validación / preparación ----------
def _estado_producto(v, ctx):
    v["Estado"] = "DISPONIBLE" if int(v["Stock"]) > 0 else "AGOTADO"


def _validar_descuento(v, ctx):
    if v.get("Fecha_Ini") and v.get("Fecha_Fin") and v["Fecha_Fin"] < v["Fecha_Ini"]:
        return {"Fecha_Fin": "Debe ser igual o posterior a la fecha de inicio"}
    return {}


def _principal(tabla, padre, pk):
    """Garantiza una sola imagen principal por producto/categoría (índice único parcial en la BD)."""
    def antes(vals, ctx):
        db, actual = ctx["db"], ctx["pk"] if ctx["pk"] is not None else -1
        otros = db.uno(f"SELECT COUNT(*) AS v FROM {tabla} WHERE {padre} = ? AND {pk} <> ?", (vals[padre], actual))
        if int(otros["v"]) == 0:
            vals["Principal"] = True            # la primera imagen siempre es la principal
        elif vals["Principal"]:
            db.modificar(f"UPDATE {tabla} SET Principal = ? WHERE {padre} = ? AND {pk} <> ?", (False, vals[padre], actual))
    return antes


def _fecha_perfil(v, ctx):
    v["Fecha_Actualizacion"] = datetime.datetime.now().replace(microsecond=0)


def _nuevo_token(v, ctx):
    if ctx["nuevo"]:
        token = secrets.token_hex(16).upper()
        ctx["token"] = token
        v["Token_Hash"] = hashlib.sha256(token.encode()).hexdigest()   # solo se guarda el hash


def _mostrar_token(ctx):
    if ctx.get("token"):
        Dialogo(ctx["app"], "Código de recuperación",
                "Entrega este código al usuario. Solo se muestra ahora: en la base de datos únicamente se guarda su hash.",
                [ctx["token"]], solo_info=True, clave_color="ok", icono="✔", copiar=ctx["token"])


def _validar_token(v, ctx):
    if ctx["nuevo"] and v.get("Fecha_Expira") and v["Fecha_Expira"] <= datetime.datetime.now():
        return {"Fecha_Expira": "Debe ser una fecha y hora futura"}
    return {}


def _proceso_token(r):
    exp = a_datetime(r.get("expira"))
    if es_true(r.get("usado")):
        r["estado"] = "Usado"
    elif exp and exp < datetime.datetime.now():
        r["estado"] = "Vencido"
    else:
        r["estado"] = "Vigente"


# ---------- colores de fila ----------
def _tag_producto(r):
    try:
        s = int(float(r.get("stock") or 0))
    except ValueError:
        return ""
    return "bad" if s == 0 else ("warn" if s <= 5 else "")


def _tag_inactivo(clave):
    return lambda r: "" if es_true(r.get(clave)) else "muted"


def _tag_usuario(r):
    if not es_true(r.get("estado")):
        return "muted"
    b = a_datetime(r.get("bloqueado"))
    try:
        fallos = int(float(r.get("intentos") or 0))
    except ValueError:
        fallos = 0
    return "bad" if (b and b > datetime.datetime.now()) or fallos >= 5 else ""


def _tag_token(r):
    return "warn" if r.get("estado") == "Vigente" else "muted"


# ---------- acciones rápidas ----------
def _acc_desbloquear(p, iid):
    p.accion("UPDATE Usuarios SET Intentos_Fallidos = 0, Bloqueado_Hasta = NULL WHERE Id_Usuario = ?",
             (int(iid),), "Cuenta desbloqueada", iid)


def _acc_toggle(tabla, col, pk, clave_fila, msg_on, msg_off):
    def fn(p, iid):
        nuevo = not es_true((p.fila(iid) or {}).get(clave_fila))
        p.accion(f"UPDATE {tabla} SET {col} = ? WHERE {pk} = ?", (nuevo, int(iid)), msg_on if nuevo else msg_off, iid)
    return fn


def _acc_invalidar(p, iid):
    p.accion("UPDATE RecuperacionContrasena SET Usado = ? WHERE Id_Recuperacion = ?", (True, int(iid)),
             "Token invalidado", iid)


# ---------- definición de las tablas ----------
METAS = [
    # ===================== CATÁLOGO =====================
    Meta("categorias", "Categorías", "categoría", "❖", "g0", "Categorias", "Id_Categoria",
         "Agrupa los productos de la tienda (amigurumis, accesorios, ropa…)",
         """SELECT C.Id_Categoria AS id, C.Nombre AS nombre, C.Descripcion AS descripcion,
                   (SELECT COUNT(*) FROM Productos P WHERE P.Id_Categoria = C.Id_Categoria) AS productos,
                   (SELECT COUNT(*) FROM ImagenesCategorias I WHERE I.Id_Categoria = C.Id_Categoria) AS imagenes
            FROM Categorias C ORDER BY C.Id_Categoria""",
         [("id", "ID", 70, "center", "int"), ("nombre", "Nombre", 220, "w", "txt"),
          ("descripcion", "Descripción", 400, "w", "txt"), ("productos", "Productos", 100, "center", "int"),
          ("imagenes", "Imágenes", 100, "center", "int")],
         [Campo("Nombre", "Nombre", max=50), Campo("Descripcion", "Descripción", "longtext", req=False, max=255)],
         grupo="CATÁLOGO",
         stats=[("Categorías", "SELECT COUNT(*) AS v FROM Categorias", "int", "g0", False),
                ("Con productos", "SELECT COUNT(DISTINCT Id_Categoria) AS v FROM Productos", "int", "ok", False)],
         bloqueos=[("Productos", "Id_Categoria", "producto(s) pertenecen a esta categoría")],
         cascada=[("ImagenesCategorias", "Id_Categoria")], fem=True),

    Meta("img_categorias", "Imágenes de categorías", "imagen de categoría", "▤", "g1", "ImagenesCategorias",
         "Id_ImagenCategoria", "Una o varias fotografías por categoría; una es la principal",
         """SELECT I.Id_ImagenCategoria AS id, C.Nombre AS categoria, I.Url_Img AS url, I.Principal AS principal
            FROM ImagenesCategorias I INNER JOIN Categorias C ON C.Id_Categoria = I.Id_Categoria
            ORDER BY I.Id_ImagenCategoria""",
         [("id", "ID", 70, "center", "int"), ("categoria", "Categoría", 260, "w", "txt"),
          ("url", "Ruta de la imagen", 380, "w", "txt"), ("principal", "Principal", 110, "center", "sino")],
         [Campo("Id_Categoria", "Categoría", "fk", fk=("Categorias", "Id_Categoria", "Nombre")),
          Campo("Url_Img", "Ruta de la imagen", max=255, ayuda="Ej. img/categorias/amigurumis.jpg"),
          Campo("Principal", "Imagen principal", "bool", req=False, default=False,
                ayuda="Es la imagen principal (solo una por categoría)")],
         grupo="CATÁLOGO",
         stats=[("Imágenes", "SELECT COUNT(*) AS v FROM ImagenesCategorias", "int", "g1", False),
                ("Categorías con imagen", "SELECT COUNT(DISTINCT Id_Categoria) AS v FROM ImagenesCategorias", "int", "ok", False)],
         antes=_principal("ImagenesCategorias", "Id_Categoria", "Id_ImagenCategoria"), fem=True),

    Meta("productos", "Productos", "producto", "✂", "g2", "Productos", "Id_Producto",
         "Catálogo de artículos tejidos: precio, existencias y estado",
         """SELECT P.Id_Producto AS id, P.Nombre AS nombre, C.Nombre AS categoria, P.Precio AS precio,
                   P.Stock AS stock, P.Estado AS estado
            FROM Productos P INNER JOIN Categorias C ON C.Id_Categoria = P.Id_Categoria
            ORDER BY P.Id_Producto""",
         [("id", "ID", 70, "center", "int"), ("nombre", "Producto", 300, "w", "txt"),
          ("categoria", "Categoría", 190, "w", "txt"), ("precio", "Precio", 120, "e", "money"),
          ("stock", "Stock", 90, "center", "int"), ("estado", "Estado", 130, "center", "txt")],
         [Campo("Id_Categoria", "Categoría", "fk", fk=("Categorias", "Id_Categoria", "Nombre")),
          Campo("Nombre", "Nombre del producto", max=100),
          Campo("Precio", "Precio ($)", "decimal", min=0, min_excl=True, maxv=999999.99),
          Campo("Stock", "Existencias", "int", min=0, maxv=1000000, default="0",
                ayuda="Con 0 existencias el producto queda como AGOTADO"),
          Campo("Descripcion", "Descripción", "longtext", req=False, max=300)],
         grupo="CATÁLOGO",
         stats=[("Productos", "SELECT COUNT(*) AS v FROM Productos", "int", "g2", False),
                ("Agotados", "SELECT COUNT(*) AS v FROM Productos WHERE Stock = 0", "int", "err", False),
                ("Valor del inventario", "SELECT COALESCE(SUM(Precio * Stock), 0) AS v FROM Productos", "money", "ok", False)],
         bloqueos=[("DetallesPedidos", "Id_Producto", "pedido(s) incluyen este producto"),
                   ("DetalleCarrito", "Id_Producto", "carrito(s) contienen este producto")],
         cascada=[("ImagenesProductos", "Id_Producto"), ("ProductosDescuentos", "Id_Producto")],
         tag_fila=_tag_producto, antes=_estado_producto),

    Meta("imagenes", "Imágenes de productos", "imagen de producto", "▣", "info", "ImagenesProductos", "Id_ImagenProducto",
         "Fotografías de cada producto; la imagen principal ya no vive en la tabla Productos",
         """SELECT I.Id_ImagenProducto AS id, P.Nombre AS producto, I.Url_Img AS url, I.Principal AS principal
            FROM ImagenesProductos I INNER JOIN Productos P ON P.Id_Producto = I.Id_Producto
            ORDER BY I.Id_ImagenProducto""",
         [("id", "ID", 70, "center", "int"), ("producto", "Producto", 300, "w", "txt"),
          ("url", "Ruta de la imagen", 360, "w", "txt"), ("principal", "Principal", 110, "center", "sino")],
         [Campo("Id_Producto", "Producto", "fk", fk=("Productos", "Id_Producto", "Nombre")),
          Campo("Url_Img", "Ruta de la imagen", max=255, ayuda="Ej. img/tote_bag.jpg"),
          Campo("Principal", "Imagen principal", "bool", req=False, default=False,
                ayuda="Es la imagen principal (solo una por producto)")],
         grupo="CATÁLOGO",
         stats=[("Imágenes", "SELECT COUNT(*) AS v FROM ImagenesProductos", "int", "info", False),
                ("Productos con imagen", "SELECT COUNT(DISTINCT Id_Producto) AS v FROM ImagenesProductos", "int", "ok", False)],
         antes=_principal("ImagenesProductos", "Id_Producto", "Id_ImagenProducto"), fem=True),

    # ===================== PROMOCIONES =====================
    Meta("descuentos", "Descuentos", "descuento", "✪", "warn", "Descuentos", "Id_Descuento",
         "Promociones independientes con porcentaje y vigencia; se asignan a productos aparte",
         """SELECT D.Id_Descuento AS id, D.Nombre AS nombre, D.Porcentaje AS porcentaje, D.Fecha_Ini AS inicio,
                   D.Fecha_Fin AS fin, D.Activo AS activo,
                   (SELECT COUNT(*) FROM ProductosDescuentos PD WHERE PD.Id_Descuento = D.Id_Descuento) AS productos
            FROM Descuentos D ORDER BY D.Id_Descuento""",
         [("id", "ID", 60, "center", "int"), ("nombre", "Promoción", 260, "w", "txt"),
          ("porcentaje", "Descuento", 100, "center", "pct"), ("inicio", "Inicio", 110, "center", "date"),
          ("fin", "Fin", 110, "center", "date"), ("activo", "Estado", 110, "center", "activo"),
          ("productos", "Productos", 100, "center", "int")],
         [Campo("Nombre", "Nombre de la promoción", max=60),
          Campo("Porcentaje", "Porcentaje (%)", "decimal", min=0, min_excl=True, maxv=100),
          Campo("Fecha_Ini", "Fecha de inicio", "date", default="hoy"),
          Campo("Fecha_Fin", "Fecha de fin", "date", default="hoy+30"),
          Campo("Activo", "Estado", "bool", req=False, default=True, ayuda="Promoción activa"),
          Campo("Descripcion", "Descripción", "longtext", req=False, max=255)],
         grupo="PROMOCIONES",
         stats=[("Promociones", "SELECT COUNT(*) AS v FROM Descuentos", "int", "warn", False),
                ("Activas", "SELECT COUNT(*) AS v FROM Descuentos WHERE Activo = ?", "int", "ok", True),
                ("Descuento promedio", "SELECT COALESCE(AVG(Porcentaje), 0) AS v FROM Descuentos", "pct", "g0", False)],
         bloqueos=[("DetallesPedidos", "Id_Descuento", "línea(s) de pedidos aplicaron esta promoción")],
         cascada=[("ProductosDescuentos", "Id_Descuento")],
         acciones=[("⇅  Activar / desactivar", "warn",
                    _acc_toggle("Descuentos", "Activo", "Id_Descuento", "activo", "Promoción activada", "Promoción desactivada"))],
         tag_fila=_tag_inactivo("activo"), validar=_validar_descuento,
         msg_unico="Ya existe una promoción con ese nombre."),

    Meta("prod_desc", "Productos en descuento", "asignación", "⇄", "ok", "ProductosDescuentos",
         ("Id_Producto", "Id_Descuento"),
         "Tabla intermedia: qué productos participan en cada promoción (relación N:M)",
         """SELECT PD.Id_Producto AS id_producto, PD.Id_Descuento AS id_descuento, P.Nombre AS producto,
                   D.Nombre AS promocion, D.Porcentaje AS porcentaje, P.Precio AS precio,
                   ROUND(P.Precio * (1 - D.Porcentaje / 100), 2) AS precio_final,
                   D.Fecha_Ini AS inicio, D.Fecha_Fin AS fin, D.Activo AS activo
            FROM ProductosDescuentos PD
            INNER JOIN Productos P ON P.Id_Producto = PD.Id_Producto
            INNER JOIN Descuentos D ON D.Id_Descuento = PD.Id_Descuento
            ORDER BY PD.Id_Descuento, PD.Id_Producto""",
         [("producto", "Producto", 250, "w", "txt"), ("promocion", "Promoción", 190, "w", "txt"),
          ("porcentaje", "Desc.", 80, "center", "pct"), ("precio", "Precio", 100, "e", "money"),
          ("precio_final", "Precio final", 110, "e", "money"), ("inicio", "Inicio", 100, "center", "date"),
          ("fin", "Fin", 100, "center", "date"), ("activo", "Estado", 100, "center", "activo")],
         [Campo("Id_Descuento", "Promoción", "fk", fk=("Descuentos", "Id_Descuento", "Nombre")),
          Campo("Id_Producto", "Producto", "fk", fk=("Productos", "Id_Producto", "Nombre"))],
         grupo="PROMOCIONES", iid_keys=("id_producto", "id_descuento"),
         stats=[("Asignaciones", "SELECT COUNT(*) AS v FROM ProductosDescuentos", "int", "ok", False),
                ("Productos con rebaja", "SELECT COUNT(DISTINCT Id_Producto) AS v FROM ProductosDescuentos", "int", "g1", False),
                ("Promociones en uso", "SELECT COUNT(DISTINCT Id_Descuento) AS v FROM ProductosDescuentos", "int", "warn", False)],
         tag_fila=_tag_inactivo("activo"), fem=True,
         msg_unico="Ese producto ya participa en esa promoción."),

    # ===================== CUENTAS =====================
    Meta("usuarios", "Usuarios", "usuario", "☺", "info", "Usuarios", "Id_Usuario",
         "Cuentas de clientes y administradores, con control de acceso",
         f"""SELECT U.Id_Usuario AS id, {NOMBRE_U} AS nombre, U.email AS email, R.Nombre AS rol, U.Estado AS estado,
                    U.Email_Verificado AS verificado, U.Intentos_Fallidos AS intentos,
                    U.Bloqueado_Hasta AS bloqueado, U.Ultimo_Acceso AS acceso
             FROM Usuarios U INNER JOIN Roles R ON R.Id_Rol = U.Id_Rol ORDER BY U.Id_Usuario""",
         [("id", "ID", 50, "center", "int"), ("nombre", "Nombre", 190, "w", "txt"), ("email", "Correo", 210, "w", "txt"),
          ("rol", "Rol", 110, "center", "txt"), ("estado", "Estado", 100, "center", "activo"),
          ("verificado", "Verificado", 85, "center", "sino"), ("intentos", "Fallos", 60, "center", "int"),
          ("bloqueado", "Bloqueado hasta", 130, "center", "dt"), ("acceso", "Último acceso", 130, "center", "dt")],
         [Campo("Nombre", "Nombre(s)", max=100), Campo("Ap_Paterno", "Apellido paterno", max=100),
          Campo("Ap_Materno", "Apellido materno", req=False, max=100),
          Campo("email", "Correo electrónico", max=150, patron=EMAIL, msg_patron="Correo no válido (ej. nombre@correo.com)"),
          Campo("Telefono", "Teléfono", max=15, patron=TEL, msg_patron="Entre 7 y 15 dígitos"),
          Campo("Id_Rol", "Rol", "fk", fk=("Roles", "Id_Rol", "Nombre")),
          Campo("Contrasena_Hash", "Contraseña", "password", max=50, minlen=6,
                ayuda="Se guarda cifrada (PBKDF2). Al editar, déjala vacía para conservar la actual"),
          Campo("Email_Verificado", "Correo", "bool", req=False, default=False, ayuda="Correo verificado"),
          Campo("Estado", "Cuenta", "bool", req=False, default=True, ayuda="Cuenta activa")],
         grupo="CUENTAS",
         stats=[("Usuarios", "SELECT COUNT(*) AS v FROM Usuarios", "int", "info", False),
                ("Activos", "SELECT COUNT(*) AS v FROM Usuarios WHERE Estado = ?", "int", "ok", True),
                ("Sin verificar", "SELECT COUNT(*) AS v FROM Usuarios WHERE Email_Verificado = ?", "int", "warn",
                 lambda: (False,)),
                ("Con intentos fallidos", "SELECT COUNT(*) AS v FROM Usuarios WHERE Intentos_Fallidos > 0", "int", "err", False)],
         bloqueos=[("Pedidos", "Id_Usuario", "pedido(s) realizados por este usuario"),
                   ("Carrito", "Id_Usuario", "carrito(s) de este usuario")],
         cascada=[("Direcciones", "Id_Usuario"), ("PerfilesUsuario", "Id_Usuario"),
                  ("RecuperacionContrasena", "Id_Usuario")],
         acciones=[("🔓  Desbloquear cuenta", "ok", _acc_desbloquear),
                   ("⇅  Activar / desactivar", "warn",
                    _acc_toggle("Usuarios", "Estado", "Id_Usuario", "estado", "Cuenta activada", "Cuenta desactivada"))],
         tag_fila=_tag_usuario, msg_unico="Ya existe un usuario con ese correo."),

    Meta("perfiles", "Perfiles", "perfil", "☻", "g1", "PerfilesUsuario", "Id_Perfil",
         "Datos personales de cada usuario (relación 1:1 con Usuarios)",
         """SELECT PF.Id_Perfil AS id, RTRIM(CONCAT(U.Nombre, ' ', U.Ap_Paterno)) AS usuario,
                   PF.Fecha_Nacimiento AS nacimiento, PF.Foto_Url AS foto, PF.Biografia AS biografia,
                   PF.Fecha_Actualizacion AS actualizado
            FROM PerfilesUsuario PF INNER JOIN Usuarios U ON U.Id_Usuario = PF.Id_Usuario
            ORDER BY PF.Id_Perfil""",
         [("id", "ID", 60, "center", "int"), ("usuario", "Usuario", 180, "w", "txt"),
          ("nacimiento", "Nacimiento", 110, "center", "date"), ("foto", "Foto", 200, "w", "txt"),
          ("biografia", "Biografía", 300, "w", "txt"), ("actualizado", "Actualizado", 130, "center", "dt")],
         [Campo("Id_Usuario", "Usuario", "fk", unico=True,
                fk=("Usuarios", "Id_Usuario", "RTRIM(CONCAT(Nombre, ' ', Ap_Paterno))"),
                ayuda="Cada usuario tiene como máximo un perfil"),
          Campo("Fecha_Nacimiento", "Fecha de nacimiento", "date", req=False),
          Campo("Foto_Url", "Foto de perfil", req=False, max=255, ayuda="Ej. img/perfiles/ana.jpg"),
          Campo("Biografia", "Biografía", "longtext", req=False, max=300)],
         grupo="CUENTAS",
         stats=[("Perfiles", "SELECT COUNT(*) AS v FROM PerfilesUsuario", "int", "g1", False),
                ("Con foto", "SELECT COUNT(*) AS v FROM PerfilesUsuario WHERE Foto_Url IS NOT NULL", "int", "ok", False),
                ("Usuarios sin perfil",
                 "SELECT COUNT(*) AS v FROM Usuarios WHERE Id_Usuario NOT IN (SELECT Id_Usuario FROM PerfilesUsuario)",
                 "int", "warn", False)],
         antes=_fecha_perfil, msg_unico="Ese usuario ya tiene un perfil."),

    Meta("recuperacion", "Recuperación de contraseña", "token", "✉", "err", "RecuperacionContrasena", "Id_Recuperacion",
         "Solicitudes de «olvidé mi contraseña»: token de un solo uso con vigencia",
         """SELECT R.Id_Recuperacion AS id, RTRIM(CONCAT(U.Nombre, ' ', U.Ap_Paterno)) AS usuario,
                   R.Fecha_Solicitud AS solicitud, R.Fecha_Expira AS expira, R.Usado AS usado
            FROM RecuperacionContrasena R INNER JOIN Usuarios U ON U.Id_Usuario = R.Id_Usuario
            ORDER BY R.Id_Recuperacion""",
         [("id", "ID", 60, "center", "int"), ("usuario", "Usuario", 220, "w", "txt"),
          ("solicitud", "Solicitado", 140, "center", "dt"), ("expira", "Vence", 140, "center", "dt"),
          ("usado", "Usado", 80, "center", "sino"), ("estado", "Estado", 110, "center", "txt")],
         [Campo("Id_Usuario", "Usuario", "fk", fk=("Usuarios", "Id_Usuario", "RTRIM(CONCAT(Nombre, ' ', Ap_Paterno))")),
          Campo("Fecha_Expira", "Vence", "datetime", default="ahora+60", ayuda="AAAA-MM-DD HH:MM (por defecto, en 1 hora)"),
          Campo("Usado", "Token", "bool", req=False, default=False, ayuda="Token ya utilizado")],
         grupo="CUENTAS",
         stats=[("Solicitudes", "SELECT COUNT(*) AS v FROM RecuperacionContrasena", "int", "err", False),
                ("Vigentes", "SELECT COUNT(*) AS v FROM RecuperacionContrasena WHERE Usado = ? AND Fecha_Expira > ?", "int", "warn",
                 lambda: (False, datetime.datetime.now())),
                ("Usados", "SELECT COUNT(*) AS v FROM RecuperacionContrasena WHERE Usado = ?", "int", "ok", True)],
         acciones=[("⊘  Invalidar token", "err", _acc_invalidar)],
         tag_fila=_tag_token, proceso=_proceso_token, antes=_nuevo_token, despues=_mostrar_token,
         validar=_validar_token),

    Meta("direcciones", "Direcciones", "dirección", "⌂", "ok", "Direcciones", "Id_Direccion",
         "Domicilios de envío registrados por los usuarios",
         """SELECT D.Id_Direccion AS id, RTRIM(CONCAT(U.Nombre, ' ', U.Ap_Paterno)) AS usuario, D.Calle AS calle,
                   D.Numero AS numero, D.Colonia AS colonia, D.Cuidad AS ciudad, D.Estado AS estado, D.Cp AS cp
            FROM Direcciones D INNER JOIN Usuarios U ON U.Id_Usuario = D.Id_Usuario ORDER BY D.Id_Direccion""",
         [("id", "ID", 60, "center", "int"), ("usuario", "Usuario", 190, "w", "txt"), ("calle", "Calle", 220, "w", "txt"),
          ("numero", "Núm.", 70, "center", "txt"), ("colonia", "Colonia", 150, "w", "txt"),
          ("ciudad", "Ciudad", 140, "w", "txt"), ("estado", "Estado", 130, "w", "txt"), ("cp", "C.P.", 80, "center", "txt")],
         [Campo("Id_Usuario", "Usuario", "fk", fk=("Usuarios", "Id_Usuario", "RTRIM(CONCAT(Nombre, ' ', Ap_Paterno))")),
          Campo("Calle", "Calle", max=150), Campo("Numero", "Número", max=10),
          Campo("Colonia", "Colonia", max=20), Campo("Cuidad", "Ciudad", max=30),
          Campo("Estado", "Estado", max=30),
          Campo("Cp", "Código postal", max=10, patron=r"[0-9]{4,10}", msg_patron="Solo dígitos (4 a 10)")],
         grupo="CUENTAS",
         stats=[("Direcciones", "SELECT COUNT(*) AS v FROM Direcciones", "int", "ok", False),
                ("Ciudades distintas", "SELECT COUNT(DISTINCT Cuidad) AS v FROM Direcciones", "int", "info", False)],
         bloqueos=[("Pedidos", "Id_Direccion", "pedido(s) se enviaron a esta dirección")], fem=True),

    Meta("roles", "Roles", "rol", "♛", "err", "Roles", "Id_Rol",
         "Perfiles de acceso del sistema",
         """SELECT R.Id_Rol AS id, R.Nombre AS nombre,
                   (SELECT COUNT(*) FROM Usuarios U WHERE U.Id_Rol = R.Id_Rol) AS usuarios
            FROM Roles R ORDER BY R.Id_Rol""",
         [("id", "ID", 70, "center", "int"), ("nombre", "Rol", 320, "w", "txt"), ("usuarios", "Usuarios", 140, "center", "int")],
         [Campo("Nombre", "Nombre del rol", "choice", opciones=("ADMINISTRADOR", "USUARIO"),
                ayuda="La base de datos solo permite estos dos nombres")],
         grupo="CUENTAS",
         stats=[("Roles", "SELECT COUNT(*) AS v FROM Roles", "int", "err", False)],
         bloqueos=[("Usuarios", "Id_Rol", "usuario(s) tienen este rol")]),
]
META_POR_KEY = {m.key: m for m in METAS}


# ============================================================
#   FORMATO
# ============================================================
def fmt(v, kind):
    if v is None or v == "":
        return "—"
    try:
        if kind == "int":
            return f"{int(float(v)):,}"
        if kind == "money":
            return f"${float(v):,.2f}"
        if kind == "pct":
            return f"{float(v):g}%"
    except (ValueError, TypeError):
        return str(v)
    if kind == "date":
        return str(v)[:10]
    if kind == "dt":
        return str(v)[:16]
    if kind == "activo":
        return "● Activo" if es_true(v) else "○ Inactivo"
    if kind == "sino":
        return "Sí" if es_true(v) else "No"
    return str(v)


# ============================================================
#   WIDGETS PERSONALIZADOS
# ============================================================
class Degradado(tk.Canvas):
    def __init__(self, master, colores, alto=70, texto="", sub="", tam=20):
        super().__init__(master, height=alto, highlightthickness=0, bd=0, bg=colores[0])
        self.colores, self.texto, self.sub, self.tam = colores, texto, sub, tam
        self.bind("<Configure>", self._dibujar)

    def _dibujar(self, _=None):
        self.delete("all")
        w, h = max(self.winfo_width(), 2), self.winfo_height()
        for x in range(0, w, 3):
            self.create_rectangle(x, 0, x + 3, h, fill=mezcla(self.colores, x / w), outline="")
        self.create_oval(w - 160, -60, w + 40, 120, fill=aclarar(mezcla(self.colores, .95), .18), outline="")
        self.create_oval(w - 280, h - 40, w - 190, h + 50, fill=aclarar(mezcla(self.colores, .75), .15), outline="")
        if self.texto:
            y = h / 2 - (11 if self.sub else 0)
            self.create_text(26, y, anchor="w", text=self.texto, fill="#ffffff", font=(F, self.tam, "bold"))
            if self.sub:
                self.create_text(28, y + self.tam + 8, anchor="w", text=self.sub, fill="#fff1fb", font=(F, 10))


class Boton(tk.Label):
    def __init__(self, master, texto, comando, bg=None, fg=None, hover=None, tam=10, padx=18, pady=8):
        bg, fg = bg or P["g"][0], fg or P["btn_text"]
        super().__init__(master, text=texto, bg=bg, fg=fg, font=(F, tam, "bold"), padx=padx, pady=pady, cursor="hand2")
        self._bg, self._fg, self._hv, self.cmd, self._on = bg, fg, hover or aclarar(bg, .2), comando, True
        self.bind("<Enter>", lambda e: self._on and self.config(bg=self._hv))
        self.bind("<Leave>", lambda e: self._on and self.config(bg=self._bg))
        self.bind("<Button-1>", lambda e: self._on and self.cmd and self.cmd())

    def habilitar(self, on):
        self._on = on
        if on:
            self.config(bg=self._bg, fg=self._fg, cursor="hand2")
        else:
            self.config(bg=P["panel2"], fg=P["muted"], cursor="arrow")


def entrada(master, show=""):
    return tk.Entry(master, bg=P["panel2"], fg=P["text"], insertbackground=P["g"][0], relief="flat", font=(F, 11),
                    highlightthickness=2, highlightbackground=P["border"], highlightcolor=P["g"][0], show=show,
                    disabledbackground=P["panel2"], selectbackground=P["g"][1], selectforeground="#ffffff")


def centrar(win, parent, ancho=None, alto=None):
    win.update_idletasks()
    ancho = ancho or win.winfo_reqwidth()
    alto = alto or win.winfo_reqheight()
    x = parent.winfo_rootx() + (parent.winfo_width() - ancho) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - alto) // 2
    win.geometry(f"{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")


def configurar_estilos(root):
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure("H.Treeview", background=P["odd"], fieldbackground=P["odd"], foreground=P["text"], rowheight=34,
                borderwidth=0, font=(F, 10))
    s.configure("H.Treeview.Heading", background=P["panel2"], foreground=P["g"][0], relief="flat",
                font=(F, 10, "bold"), padding=(10, 9), borderwidth=0)
    s.map("H.Treeview.Heading", background=[("active", P["border"])])
    s.map("H.Treeview", background=[("selected", P["sel"])], foreground=[("selected", P["text"])])
    s.layout("H.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    for o in ("Vertical", "Horizontal"):
        s.configure(f"H.{o}.TScrollbar", background=P["g"][1], troughcolor=P["panel"], bordercolor=P["panel"],
                    lightcolor=P["g"][1], darkcolor=P["g"][1], arrowcolor=P["text"], gripcount=0, relief="flat")
    s.configure("H.TCombobox", fieldbackground=P["panel2"], background=P["panel2"], foreground=P["text"],
                arrowcolor=P["g"][0], bordercolor=P["border"], lightcolor=P["border"], darkcolor=P["border"],
                padding=7, selectbackground=P["panel2"], selectforeground=P["text"])
    s.map("H.TCombobox", fieldbackground=[("readonly", P["panel2"])], foreground=[("readonly", P["text"])],
          selectbackground=[("readonly", P["panel2"])], selectforeground=[("readonly", P["text"])])
    root.option_add("*TCombobox*Listbox.background", P["panel2"])
    root.option_add("*TCombobox*Listbox.foreground", P["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", P["g"][1])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", (F, 10))


MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
         "Octubre", "Noviembre", "Diciembre"]


class Calendario(tk.Toplevel):
    """Selector de fecha emergente."""

    def __init__(self, app, ancla, texto, al_elegir):
        super().__init__(app.root)
        self.overrideredirect(True)
        self.configure(bg=P["g"][0])
        try:
            d = datetime.datetime.strptime(texto.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            d = datetime.date.today()
        self.sel, self.anio, self.mes, self.al_elegir = d, d.year, d.month, al_elegir
        self.cuerpo = tk.Frame(self, bg=P["panel"])
        self.cuerpo.pack(padx=2, pady=2)
        self._dibujar()
        self.geometry(f"+{ancla.winfo_rootx()}+{ancla.winfo_rooty() + ancla.winfo_height() + 6}")
        self.bind("<Escape>", lambda e: self.destroy())
        self.lift()

    def _mover(self, delta):
        m = self.mes + delta
        self.anio += (m - 1) // 12
        self.mes = (m - 1) % 12 + 1
        self._dibujar()

    def _elegir(self, d):
        self.al_elegir(d)
        self.destroy()

    def _dibujar(self):
        for w in self.cuerpo.winfo_children():
            w.destroy()
        enc = tk.Frame(self.cuerpo, bg=P["panel2"])
        enc.pack(fill="x")
        for txt, cmd, side in (("‹", lambda: self._mover(-1), "left"), ("›", lambda: self._mover(1), "right")):
            b = tk.Label(enc, text=txt, bg=P["panel2"], fg=P["g"][0], font=(F, 14, "bold"), cursor="hand2", padx=12)
            b.pack(side=side)
            b.bind("<Button-1>", lambda e, c=cmd: c())
        tk.Label(enc, text=f"{MESES[self.mes - 1]} {self.anio}", bg=P["panel2"], fg=P["text"],
                 font=(F, 11, "bold")).pack(side="left", expand=True, pady=8)
        cuad = tk.Frame(self.cuerpo, bg=P["panel"], padx=8, pady=6)
        cuad.pack()
        for i, d in enumerate("DLMMJVS"):
            tk.Label(cuad, text=d, bg=P["panel"], fg=P["muted"], font=(F, 9, "bold"), width=4).grid(row=0, column=i)
        hoy = datetime.date.today()
        for r, semana in enumerate(calendar.Calendar(firstweekday=6).monthdayscalendar(self.anio, self.mes), 1):
            for i, dia in enumerate(semana):
                if not dia:
                    continue
                f = datetime.date(self.anio, self.mes, dia)
                es_sel, es_hoy = f == self.sel, f == hoy
                lb = tk.Label(cuad, text=str(dia), width=4, pady=4, cursor="hand2", font=(F, 10, "bold" if es_sel else "normal"),
                              bg=P["g"][0] if es_sel else P["panel"],
                              fg=P["btn_text"] if es_sel else (P["g"][0] if es_hoy else P["text"]))
                lb.grid(row=r, column=i, padx=1, pady=1)
                lb.bind("<Button-1>", lambda e, f=f: self._elegir(f))
                if not es_sel:
                    lb.bind("<Enter>", lambda e, w=lb: w.config(bg=P["panel2"]))
                    lb.bind("<Leave>", lambda e, w=lb: w.config(bg=P["panel"]))
        pie = tk.Frame(self.cuerpo, bg=P["panel"])
        pie.pack(fill="x", pady=(0, 8), padx=8)
        Boton(pie, "Hoy", lambda: self._elegir(hoy), P["g"][1], padx=12, pady=4, tam=9).pack(side="left")
        Boton(pie, "Cerrar", self.destroy, P["panel2"], P["text"], padx=12, pady=4, tam=9).pack(side="right")


class Dialogo(tk.Toplevel):
    """Mensaje o confirmación con estilo."""

    def __init__(self, app, titulo, mensaje, lineas=(), boton="Aceptar", clave_color="err", al_aceptar=None,
                 solo_info=False, icono="▲", copiar=None):
        super().__init__(app.root)
        self.configure(bg=P["panel"])
        self.title(titulo)
        self.transient(app.root)
        self.resizable(False, False)
        col = color(clave_color)
        Degradado(self, [col, aclarar(col, .35)], 64, texto=f"{icono}  {titulo}", tam=16).pack(fill="x")
        cuerpo = tk.Frame(self, bg=P["panel"], padx=26, pady=18)
        cuerpo.pack(fill="both", expand=True)
        tk.Label(cuerpo, text=mensaje, bg=P["panel"], fg=P["text"], font=(F, 11), wraplength=440, justify="left",
                 anchor="w").pack(fill="x")
        for ln in lineas:
            if copiar:   # código destacado
                tk.Label(cuerpo, text=ln, bg=P["panel2"], fg=P["g"][0], font=("Consolas", 14, "bold"), pady=10,
                         ).pack(fill="x", pady=(12, 0))
            else:
                tk.Label(cuerpo, text="•  " + ln, bg=P["panel"], fg=P["muted"], font=(F, 10), wraplength=440,
                         justify="left", anchor="w").pack(fill="x", pady=(6, 0))
        pie = tk.Frame(self, bg=P["panel"], padx=26)
        pie.pack(fill="x", pady=(0, 20))
        if solo_info:
            Boton(pie, "Entendido", self.destroy, P["g"][1]).pack(side="right")
            if copiar:
                def copia():
                    self.clipboard_clear()
                    self.clipboard_append(copiar)
                Boton(pie, "Copiar código", copia, P["panel2"], P["text"]).pack(side="right", padx=10)
        else:
            def ok():
                self.destroy()
                al_aceptar and al_aceptar()
            Boton(pie, boton, ok, col).pack(side="right")
            Boton(pie, "Cancelar", self.destroy, P["panel2"], P["text"]).pack(side="right", padx=10)
        self.bind("<Escape>", lambda e: self.destroy())
        centrar(self, app.root, 520)
        self.after(20, self._tomar)

    def _tomar(self):
        try:
            self.grab_set()
        except tk.TclError:
            pass


# ============================================================
#   FORMULARIO (AGREGAR / MODIFICAR)
# ============================================================
def _valor_por_defecto(d):
    """'hoy', 'hoy+30' -> fecha ISO ;  'ahora+60' -> fecha y hora."""
    if d.startswith("ahora"):
        mins = int(d.split("+")[1]) if "+" in d else 0
        return (datetime.datetime.now() + datetime.timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M")
    dias = int(d.split("+")[1]) if "+" in d else 0
    return (datetime.date.today() + datetime.timedelta(days=dias)).isoformat()


class Formulario(tk.Toplevel):
    def __init__(self, app, meta, registro=None, al_guardar=None):
        super().__init__(app.root)
        self.app, self.meta, self.registro, self.al_guardar = app, meta, registro, al_guardar
        self.getters, self.err_lbl, self.mapas = {}, {}, {}
        nuevo = registro is None
        self.configure(bg=P["panel"])
        self.title(("Nuevo " if nuevo else "Editar ") + meta.singular)
        self.transient(app.root)
        self.resizable(False, False)

        sub = "Completa los datos y presiona Insertar" if nuevo else \
            "Registro " + " · ".join(f"#{registro[c.lower()]}" for c in pk_cols(meta))
        Degradado(self, P["g"], 80, texto=f"{meta.icono}  {'Nuevo ' if nuevo else 'Editar '}{meta.singular}",
                  sub=sub, tam=18).pack(fill="x")

        cuerpo = tk.Frame(self, bg=P["panel"], padx=28, pady=18)
        cuerpo.pack(fill="both", expand=True)
        dos = len(meta.campos) > 4
        ncol = 2 if dos else 1
        for i in range(ncol):
            cuerpo.columnconfigure(i, weight=1, uniform="c")
        fila, col = 0, 0
        for c in meta.campos:
            completo = c.tipo == "longtext"
            if completo and col != 0:
                fila, col = fila + 1, 0
            cont = self._campo(cuerpo, c)
            if completo:
                cont.grid(row=fila, column=0, columnspan=ncol, sticky="ew", pady=(0, 6))
                fila, col = fila + 1, 0
            else:
                cont.grid(row=fila, column=col, sticky="ew", padx=(0, 14 if col < ncol - 1 else 0), pady=(0, 6))
                col += 1
                if col == ncol:
                    fila, col = fila + 1, 0

        self.err_global = tk.Label(self, text="", bg=P["panel"], fg=P["err"], font=(F, 10, "bold"), wraplength=560,
                                   justify="left")
        self.err_global.pack(fill="x", padx=28)
        pie = tk.Frame(self, bg=P["panel"], padx=28)
        pie.pack(fill="x", pady=(8, 22))
        Boton(pie, "✔  Actualizar" if not nuevo else "✚  Insertar", self.guardar, P["ok"]).pack(side="right")
        Boton(pie, "Cancelar", self.destroy, P["panel2"], P["text"]).pack(side="right", padx=10)

        self.bind("<Escape>", lambda e: self.destroy())
        centrar(self, app.root, 780 if dos else 520)
        self.after(20, self._tomar)
        self.after(60, lambda: self.foco.focus_set() if getattr(self, "foco", None) else None)

    def _tomar(self):
        try:
            self.grab_set()
        except tk.TclError:
            pass

    # ---------- creación de campos ----------
    def _campo(self, padre, c):
        cont = tk.Frame(padre, bg=P["panel"])
        tk.Label(cont, text=c.label + (" *" if c.req else ""), bg=P["panel"], fg=P["muted"], font=(F, 9, "bold"),
                 anchor="w").pack(fill="x")
        actual = self.registro.get(c.col.lower()) if self.registro else None
        nuevo = self.registro is None
        sin_opciones = False

        if c.tipo in ("text", "password", "int", "decimal"):
            e = entrada(cont, "•" if c.tipo == "password" else "")
            if c.tipo == "password":
                fila = tk.Frame(cont, bg=P["panel"])
                fila.pack(fill="x")
                e.pack(in_=fila, side="left", fill="x", expand=True, ipady=6)
                ver = tk.Label(fila, text="ver", bg=P["panel"], fg=P["g"][0], font=(F, 9, "bold"), cursor="hand2", padx=8)
                ver.pack(side="left")
                ver.bind("<Button-1>", lambda ev, e=e, v=ver: (e.config(show="" if e.cget("show") else "•"),
                                                                  v.config(text="ocultar" if not e.cget("show") else "ver")))
            else:
                e.pack(fill="x", ipady=6)
            if actual is not None and c.tipo != "password":
                e.insert(0, str(actual))
            elif nuevo and c.default is not None:
                e.insert(0, str(c.default))
            self.getters[c.col] = e.get
            self.foco = getattr(self, "foco", None) or e
            e.bind("<Return>", lambda ev: self.guardar())

        elif c.tipo == "longtext":
            t = tk.Text(cont, height=3, bg=P["panel2"], fg=P["text"], insertbackground=P["g"][0], relief="flat",
                        font=(F, 11), highlightthickness=2, highlightbackground=P["border"], highlightcolor=P["g"][0],
                        wrap="word", selectbackground=P["g"][1])
            t.pack(fill="x")
            if actual is not None:
                t.insert("1.0", str(actual))
            self.getters[c.col] = lambda t=t: t.get("1.0", "end").strip()

        elif c.tipo == "bool":
            var = tk.BooleanVar(value=es_true(actual) if not nuevo else bool(c.default))
            tk.Checkbutton(cont, text=c.ayuda or "Sí", variable=var, bg=P["panel"], fg=P["text"], selectcolor=P["panel2"],
                           activebackground=P["panel"], activeforeground=P["text"], font=(F, 11), cursor="hand2",
                           highlightthickness=0, bd=0).pack(anchor="w", pady=(6, 0))
            self.getters[c.col] = var.get

        elif c.tipo in ("choice", "fk"):
            if c.tipo == "choice":
                valores = list(c.opciones)
                sel = next((o for o in valores if actual is not None and o.upper() == str(actual).upper()), "")
                mapa = {}
            else:
                tabla, idc, etq = c.fk
                filtro = f"WHERE {idc} NOT IN (SELECT {c.col} FROM {self.meta.tabla}) " if (c.unico and nuevo) else ""
                try:
                    filas = self.app.db.consultar(f"SELECT {idc} AS id, {etq} AS etiqueta FROM {tabla} {filtro}ORDER BY etiqueta")
                except ErrorBD as ex:
                    filas = []
                    self.app.toast(str(ex), "error")
                mapa = {f"{f['etiqueta']}  (#{f['id']})": f["id"] for f in filas}
                valores = list(mapa)
                sel = next((k for k, v in mapa.items() if actual is not None and str(v) == str(actual)), "")
                sin_opciones = not valores
            self.mapas[c.col] = mapa
            cb = ttk.Combobox(cont, values=valores, state="readonly", style="H.TCombobox", font=(F, 11))
            cb.pack(fill="x")
            if sel:
                cb.set(sel)
            self.getters[c.col] = cb.get
            self.foco = getattr(self, "foco", None) or cb

        elif c.tipo in ("date", "datetime"):
            es_dt = c.tipo == "datetime"
            fila = tk.Frame(cont, bg=P["panel"])
            fila.pack(fill="x")
            e = entrada(fila)
            e.pack(side="left", fill="x", expand=True, ipady=6)
            if actual:
                e.insert(0, str(actual)[:16 if es_dt else 10])
            elif nuevo and c.default:
                e.insert(0, _valor_por_defecto(c.default))
            b = Boton(fila, "▦", None, P["g"][1], padx=12, pady=5, tam=11)
            b.pack(side="left", padx=(8, 0))

            def poner(d, e=e, es_dt=es_dt):
                hora = e.get().strip()[10:].strip() if es_dt else ""
                e.delete(0, "end")
                e.insert(0, d.isoformat() + ((" " + (hora or "00:00")) if es_dt else ""))
            b.cmd = lambda e=e, b=b, poner=poner: Calendario(self.app, b, e.get(), poner)
            self.getters[c.col] = e.get

        if c.ayuda and c.tipo != "bool":
            tk.Label(cont, text=c.ayuda, bg=P["panel"], fg=P["muted"], font=(F, 8), anchor="w", wraplength=330,
                     justify="left").pack(fill="x")
        err = tk.Label(cont, text="No hay opciones disponibles (todas están en uso)." if sin_opciones else "",
                       bg=P["panel"], fg=P["err"], font=(F, 9), anchor="w")
        err.pack(fill="x")
        self.err_lbl[c.col] = err
        return cont

    # ---------- lectura y validación ----------
    OMITIR = object()

    def _leer(self, c):
        raw = self.getters[c.col]()
        t = c.tipo
        if t == "bool":
            return bool(raw), None
        if t in ("choice", "fk"):
            if not raw:
                return None, "Selecciona una opción"
            return (self.mapas[c.col][raw] if t == "fk" else raw), None
        s = (raw or "").strip()
        if not s:
            if t == "password" and self.registro:
                return self.OMITIR, None
            return (None, "Este campo es obligatorio") if c.req else (None, None)
        if c.max and len(s) > c.max:
            return None, f"Máximo {c.max} caracteres"
        if c.minlen and len(s) < c.minlen:
            return None, f"Mínimo {c.minlen} caracteres"
        if c.patron and not re.fullmatch(c.patron, s):
            return None, c.msg_patron or "Formato no válido"
        if t == "int":
            try:
                n = int(s)
            except ValueError:
                return None, "Debe ser un número entero"
            if c.min is not None and n < c.min:
                return None, f"Debe ser mayor o igual a {int(c.min)}"
            if c.maxv is not None and n > c.maxv:
                return None, f"Debe ser menor o igual a {int(c.maxv)}"
            return n, None
        if t == "decimal":
            try:
                d = Decimal(s.replace(",", "")).quantize(Decimal("0.01"))
            except InvalidOperation:
                return None, "Debe ser un número (ej. 349.00)"
            if c.min is not None and (d <= Decimal(str(c.min)) if c.min_excl else d < Decimal(str(c.min))):
                return None, f"Debe ser mayor a {c.min:g}" if c.min_excl else f"Debe ser al menos {c.min:g}"
            if c.maxv is not None and d > Decimal(str(c.maxv)):
                return None, f"Debe ser como máximo {c.maxv:g}"
            return d, None
        if t == "date":
            try:
                return datetime.datetime.strptime(s, "%Y-%m-%d").date(), None
            except ValueError:
                return None, "Usa el formato AAAA-MM-DD"
        if t == "datetime":
            s2 = s.replace("T", " ")
            for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    return datetime.datetime.strptime(s2, f), None
                except ValueError:
                    pass
            return None, "Usa el formato AAAA-MM-DD HH:MM"
        return s, None

    def guardar(self):
        m = self.meta
        errores, vals = {}, {}
        for c in m.campos:
            v, err = self._leer(c)
            if err:
                errores[c.col] = err
            elif v is not self.OMITIR:
                vals[c.col] = v
        nuevo = self.registro is None
        simple = len(pk_cols(m)) == 1
        ctx = {"app": self.app, "db": self.app.db, "nuevo": nuevo, "registro": self.registro,
               "pk": None if (nuevo or not simple) else self.registro[pk_cols(m)[0].lower()]}
        if not errores and m.validar:
            errores.update(m.validar(vals, ctx))
        for col, lbl in self.err_lbl.items():
            if col in errores:
                lbl.config(text="✖ " + errores[col])
            elif lbl.cget("text").startswith("✖"):
                lbl.config(text="")
        if errores:
            self.err_global.config(text="Revisa los campos marcados en rojo.")
            return
        self.err_global.config(text="")
        db = self.app.db
        try:
            if m.antes:
                m.antes(vals, ctx)
            for c in m.campos:                       # las contraseñas se guardan cifradas
                if c.tipo == "password" and vals.get(c.col):
                    vals[c.col] = hash_password(vals[c.col])
            cols = list(vals)
            params = [vals[c] for c in cols]
            if nuevo:
                db.modificar(f"INSERT INTO {m.tabla} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})", params)
                self.app.toast(f"{m.singular.capitalize()} insertad{'a' if m.fem else 'o'} correctamente", "ok")
            else:
                viejos = [self.registro[c.lower()] for c in pk_cols(m)]
                db.modificar(f"UPDATE {m.tabla} SET {', '.join(c + ' = ?' for c in cols)} WHERE {where_pk(m)}",
                             params + viejos)
                self.app.toast(f"{m.singular.capitalize()} actualizad{'a' if m.fem else 'o'} correctamente", "ok")
        except ErrorBD as ex:
            txt = str(ex)
            if "campo único duplicado" in txt and m.msg_unico:
                txt = m.msg_unico
            self.err_global.config(text=f"✖ {txt}")
            return
        iid = None
        if not simple:
            iid = "|".join(str(vals[c]) for c in pk_cols(m))
        elif not nuevo:
            iid = str(ctx["pk"])
        self.destroy()
        if m.despues:
            m.despues(ctx)
        if self.al_guardar:
            self.al_guardar(iid)


# ============================================================
#   PÁGINA CRUD GENÉRICA
# ============================================================
class PaginaCrud(tk.Frame):
    def __init__(self, master, app, meta):
        super().__init__(master, bg=P["bg"])
        self.app, self.meta = app, meta
        self.filas, self.orden, self.b_acc = [], (None, False), []

        Degradado(self, P["g"], 96, texto=f"{meta.icono}   {meta.titulo}", sub=meta.descripcion, tam=22).pack(fill="x")
        self.stats = tk.Frame(self, bg=P["bg"])
        self.stats.pack(fill="x", padx=24, pady=(16, 4))

        barra = tk.Frame(self, bg=P["bg"])
        barra.pack(fill="x", padx=24, pady=(10, 8))
        caja = tk.Frame(barra, bg=P["panel2"], highlightthickness=2, highlightbackground=P["border"],
                        highlightcolor=P["g"][0])
        caja.pack(side="left")
        tk.Label(caja, text="⌕", bg=P["panel2"], fg=P["g"][0], font=(F, 14, "bold")).pack(side="left", padx=(10, 0))
        self.var = tk.StringVar()
        self.var.trace_add("write", lambda *a: self.pintar())
        self.buscador = tk.Entry(caja, textvariable=self.var, bg=P["panel2"], fg=P["text"], relief="flat", width=28,
                                 font=(F, 11), insertbackground=P["g"][0])
        self.buscador.pack(side="left", ipady=7, padx=8)
        self.buscador.bind("<Escape>", lambda e: self.var.set(""))

        Boton(barra, "✚  Insertar", self.agregar, P["ok"]).pack(side="right")
        self.b_elim = Boton(barra, "✖  Eliminar", self.eliminar, P["err"])
        self.b_elim.pack(side="right", padx=10)
        self.b_edit = Boton(barra, "✎  Actualizar", self.modificar, P["g"][1])
        self.b_edit.pack(side="right")
        Boton(barra, "⌕  Consultar", self.consultar, P["panel2"], P["text"]).pack(side="right", padx=10)

        if meta.acciones:
            fila = tk.Frame(self, bg=P["bg"])
            fila.pack(fill="x", padx=24, pady=(0, 8))
            tk.Label(fila, text="ACCIONES RÁPIDAS", bg=P["bg"], fg=P["muted"], font=(F, 8, "bold")).pack(side="left", padx=(0, 12))
            for texto, col, fn in meta.acciones:
                b = Boton(fila, texto, lambda fn=fn: self._rapida(fn), color(col), padx=14, pady=5, tam=9)
                b.pack(side="left", padx=(0, 8))
                self.b_acc.append(b)

        marco = tk.Frame(self, bg=P["panel"], highlightthickness=1, highlightbackground=P["border"])
        marco.pack(fill="both", expand=True, padx=24, pady=(0, 6))
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)
        cols = [c[0] for c in meta.columnas]
        self.tree = ttk.Treeview(marco, columns=cols, show="headings", style="H.Treeview", selectmode="browse")
        for llave, enc, ancho, ancla, _ in meta.columnas:
            self.tree.heading(llave, text=enc, command=lambda k=llave: self.ordenar(k))
            self.tree.column(llave, width=ancho, anchor=ancla, minwidth=50)
        vs = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview, style="H.Vertical.TScrollbar")
        hs = ttk.Scrollbar(marco, orient="horizontal", command=self.tree.xview, style="H.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        self.tree.tag_configure("odd", background=P["odd"])
        self.tree.tag_configure("even", background=P["even"])
        self.tree.tag_configure("bad", foreground=P["err"])
        self.tree.tag_configure("warn", foreground=P["warn"])
        self.tree.tag_configure("muted", foreground=P["muted"])
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._sel())
        self.tree.bind("<Double-1>", lambda e: self.modificar())
        self.tree.bind("<Return>", lambda e: self.modificar())
        self.tree.bind("<Delete>", lambda e: self.eliminar())
        self.vacio = tk.Label(marco, text="", bg=P["panel"], fg=P["muted"], font=(F, 12), justify="center")
        self.pie = tk.Label(self, text="", bg=P["bg"], fg=P["muted"], font=(F, 9), anchor="w")
        self.pie.pack(fill="x", padx=26, pady=(0, 8))
        self._sel()
        self.cargar()

    # ---------- datos ----------
    def cargar(self, seleccionar=None):
        try:
            self.filas = self.app.db.consultar(self.meta.lista_sql)
            if self.meta.proceso:
                for r in self.filas:
                    self.meta.proceso(r)
        except ErrorBD as e:
            self.filas = []
            self.app.toast(str(e), "error")
        self.pintar(seleccionar)
        self._stats()

    def fila(self, iid):
        return next((r for r in self.filas if iid_de(self.meta, r) == str(iid)), None)

    def _stats(self):
        for w in self.stats.winfo_children():
            w.destroy()
        for etq, sql, kind, col, prm in self.meta.stats:
            params = (True,) if prm is True else (prm() if callable(prm) else None)
            try:
                r = self.app.db.uno(sql, params)
                valor = fmt(r["v"], kind) if r else "—"
            except ErrorBD:
                valor = "—"
            tarjeta = tk.Frame(self.stats, bg=P["panel"], highlightthickness=1, highlightbackground=P["border"])
            tarjeta.pack(side="left", padx=(0, 14))
            tk.Frame(tarjeta, bg=color(col), width=5).pack(side="left", fill="y")
            interior = tk.Frame(tarjeta, bg=P["panel"], padx=16, pady=8)
            interior.pack(side="left")
            tk.Label(interior, text=etq.upper(), bg=P["panel"], fg=P["muted"], font=(F, 8, "bold")).pack(anchor="w")
            tk.Label(interior, text=valor, bg=P["panel"], fg=color(col), font=(F, 18, "bold")).pack(anchor="w")

    @staticmethod
    def _clave(v):
        try:
            return (0, float(v))
        except (TypeError, ValueError):
            return (1, str(v).lower())

    def ordenar(self, llave):
        previo, desc = self.orden
        self.orden = (llave, (not desc) if previo == llave else False)
        self.pintar()

    def pintar(self, seleccionar=None):
        q = self.var.get().strip().lower()
        filas = self.filas
        if q:
            filas = [r for r in filas if any(q in fmt(r.get(k), kd).lower() for k, _, _, _, kd in self.meta.columnas)]
        llave, desc = self.orden
        if llave:
            filas = sorted(filas, key=lambda r: self._clave(r.get(llave)), reverse=desc)
        for k, enc, *_ in self.meta.columnas:
            flecha = (" ▼" if desc else " ▲") if k == llave else ""
            self.tree.heading(k, text=enc + flecha)
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(filas):
            tag = self.meta.tag_fila(r) if self.meta.tag_fila else ""
            zebra = "odd" if i % 2 == 0 else "even"
            self.tree.insert("", "end", iid=iid_de(self.meta, r),
                             values=[fmt(r.get(k), kd) for k, _, _, _, kd in self.meta.columnas],
                             tags=(tag, zebra) if tag else (zebra,))
        if not filas:
            self.vacio.config(text="No hay registros que coincidan." if q else
                              f"Aún no hay registros en «{self.meta.titulo}».\nPresiona «Insertar» para crear el primero.")
            self.vacio.place(relx=.5, rely=.5, anchor="center")
        else:
            self.vacio.place_forget()
        self.pie.config(text=f"Mostrando {len(filas)} de {len(self.filas)} registro(s)   ·   "
                             "Doble clic = actualizar   ·   Supr = eliminar   ·   Clic en el encabezado = ordenar")
        if seleccionar is not None and str(seleccionar) in self.tree.get_children():
            self.tree.selection_set(str(seleccionar))
            self.tree.see(str(seleccionar))
        self._sel()

    def _sel(self):
        on = bool(self.tree.selection())
        self.b_edit.habilitar(on)
        self.b_elim.habilitar(on)
        for b in self.b_acc:
            b.habilitar(on)

    def _id_sel(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    # ---------- acciones ----------
    def agregar(self):
        def listo(iid):
            if iid:
                return self.cargar(iid)
            self.cargar()
            ids = [int(r["id"]) for r in self.filas if "id" in r]
            if ids:
                self.cargar(max(ids))
        Formulario(self.app, self.meta, None, listo)

    def consultar(self):
        """CONSULTAR: vuelve a ejecutar el SELECT de la tabla y deja el cursor en el buscador."""
        self.cargar()
        self.buscador.focus_set()

    def modificar(self):
        iid = self._id_sel()
        if not iid:
            return
        m = self.meta
        cols = []
        for c in pk_cols(m) + [c.col for c in m.campos if c.tipo != "password"]:
            if c not in cols:
                cols.append(c)
        try:
            reg = self.app.db.uno(f"SELECT {', '.join(cols)} FROM {m.tabla} WHERE {where_pk(m)}", tuple(pk_params(m, iid)))
        except ErrorBD as e:
            return self.app.toast(str(e), "error")
        if not reg:
            self.app.toast("El registro ya no existe.", "warn")
            return self.cargar()
        Formulario(self.app, m, reg, lambda nuevo_iid: self.cargar(nuevo_iid or iid))

    def accion(self, sql, params, mensaje, iid):
        try:
            self.app.db.modificar(sql, params)
        except ErrorBD as e:
            return self.app.toast(str(e), "error")
        self.app.toast(mensaje, "ok")
        self.cargar(iid)

    def _rapida(self, fn):
        iid = self._id_sel()
        if iid:
            fn(self, iid)

    def eliminar(self):
        iid = self._id_sel()
        if not iid:
            return
        m, db = self.meta, self.app.db
        resumen = "  ·  ".join(str(v) for v in self.tree.item(iid)["values"][:3])
        simple = len(pk_cols(m)) == 1
        try:
            bloqueos, cascada = [], []
            if simple:
                for tabla, col, texto in m.bloqueos:
                    n = int(db.uno(f"SELECT COUNT(*) AS v FROM {tabla} WHERE {col} = ?", (int(iid),))["v"])
                    if n:
                        bloqueos.append(f"{n} {texto}")
                for tabla, col in m.cascada:
                    n = int(db.uno(f"SELECT COUNT(*) AS v FROM {tabla} WHERE {col} = ?", (int(iid),))["v"])
                    if n:
                        cascada.append(f"{n} registro(s) de {tabla}")
        except ErrorBD as e:
            return self.app.toast(str(e), "error")
        if bloqueos:
            Dialogo(self.app, "No se puede eliminar",
                    f"«{resumen}» está en uso, así que no puede eliminarse:", bloqueos, solo_info=True, icono="✖")
            return
        msg = f"¿Seguro que deseas eliminar {'esta' if m.fem else 'este'} {m.singular}?\n\n{resumen}"
        lineas = [f"También se eliminarán: {', '.join(cascada)}"] if cascada else []
        Dialogo(self.app, f"Eliminar {m.singular}", msg, lineas, boton="Sí, eliminar", al_aceptar=lambda: self._borrar(iid))

    def _borrar(self, iid):
        m, db = self.meta, self.app.db
        try:
            if len(pk_cols(m)) == 1:
                for tabla, col in m.cascada:
                    db.modificar(f"DELETE FROM {tabla} WHERE {col} = ?", (int(iid),))
            db.modificar(f"DELETE FROM {m.tabla} WHERE {where_pk(m)}", tuple(pk_params(m, iid)))
        except ErrorBD as e:
            return self.app.toast(str(e), "error")
        self.app.toast(f"{m.singular.capitalize()} eliminad{'a' if m.fem else 'o'} correctamente", "ok")
        self.cargar()


# ============================================================
#   PÁGINA DE INICIO
# ============================================================
class PaginaInicio(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=P["bg"])
        Degradado(self, P["g"], 130, texto="Handmade Stitches", sub=f"Panel de administración  ·  {app.db.motor}",
                  tam=30).pack(fill="x")
        tk.Label(self, text="Tablas maestras", bg=P["bg"], fg=P["text"], font=(F, 15, "bold")).pack(anchor="w", padx=28, pady=(20, 2))
        tk.Label(self, text="Elige una tabla para insertar, consultar, actualizar o eliminar registros.",
                 bg=P["bg"], fg=P["muted"], font=(F, 10)).pack(anchor="w", padx=28, pady=(0, 10))
        grid = tk.Frame(self, bg=P["bg"])
        grid.pack(fill="x", padx=22)
        for i in range(4):
            grid.columnconfigure(i, weight=1, uniform="k")
        for i, m in enumerate(METAS):
            try:
                n = fmt(app.db.uno(f"SELECT COUNT(*) AS v FROM {m.tabla}")["v"], "int")
            except ErrorBD:
                n = "—"
            col = color(m.color)
            card = tk.Frame(grid, bg=P["panel"], highlightthickness=1, highlightbackground=P["border"], cursor="hand2")
            card.grid(row=i // 4, column=i % 4, padx=6, pady=6, sticky="nsew")
            tk.Frame(card, bg=col, height=5).pack(fill="x")
            cuerpo = tk.Frame(card, bg=P["panel"], padx=16, pady=10)
            cuerpo.pack(fill="both", expand=True)
            fila = tk.Frame(cuerpo, bg=P["panel"])
            fila.pack(fill="x")
            tk.Label(fila, text=m.icono, bg=P["panel"], fg=col, font=(F, 22, "bold")).pack(side="left")
            tk.Label(fila, text=n, bg=P["panel"], fg=P["text"], font=(F, 22, "bold")).pack(side="right")
            tk.Label(cuerpo, text=m.titulo, bg=P["panel"], fg=P["text"], font=(F, 11, "bold"), anchor="w",
                     wraplength=190, justify="left").pack(fill="x")
            tk.Label(cuerpo, text=f"{m.grupo.capitalize()}  ·  Administrar ›", bg=P["panel"], fg=P["muted"],
                     font=(F, 8), anchor="w").pack(fill="x")
            self._enlazar(card, app, m.key, col)
        tip = tk.Frame(self, bg=P["panel"], highlightthickness=1, highlightbackground=P["border"])
        tip.pack(fill="x", padx=28, pady=(16, 0))
        tk.Label(tip, text="✦  Doble clic en una fila = actualizar  ·  Supr = eliminar  ·  el buscador filtra mientras "
                           "escribes  ·  usa las acciones rápidas para desbloquear cuentas, activar promociones, etc.",
                 bg=P["panel"], fg=P["muted"], font=(F, 10), padx=16, pady=12, anchor="w", wraplength=980,
                 justify="left").pack(fill="x")

    def _enlazar(self, card, app, key, col):
        def pintar(bg, borde):
            for w in self._todos(card):
                if (isinstance(w, tk.Frame) and w.cget("height") != 5) or isinstance(w, tk.Label):
                    w.config(bg=bg)
            card.config(highlightbackground=borde)
        for w in [card] + self._todos(card):
            w.bind("<Enter>", lambda e: pintar(P["panel2"], col))
            w.bind("<Leave>", lambda e: pintar(P["panel"], P["border"]))
            w.bind("<Button-1>", lambda e: app.mostrar(key))

    def _todos(self, w):
        out = []
        for h in w.winfo_children():
            out.append(h)
            out += self._todos(h)
        return out


# ============================================================
#   APLICACIÓN
# ============================================================
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Handmade Stitches · Administrador")
        self.root.geometry("1340x820")
        self.root.minsize(1120, 680)
        self.db = None
        self.usuario = ""
        self.pagina = "inicio"
        self._toasts = []
        self._reloj = None
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self._preparar_tema()
        self.pantalla_conexion()

    def _preparar_tema(self):
        self.root.configure(bg=P["bg"])
        configurar_estilos(self.root)

    def _menubar(self):
        """Menú principal: Sistema | Catálogos > [tabla maestra] > Consultar / Insertar / Actualizar / Eliminar"""
        est = dict(bg=P["panel"], fg=P["text"], activebackground=P["g"][1], activeforeground="#ffffff", bd=0)
        barra = tk.Menu(self.root, **est)
        sistema = tk.Menu(barra, tearoff=0, **est)
        sistema.add_command(label="Inicio", command=lambda: self.mostrar("inicio"))
        sistema.add_separator()
        sistema.add_command(label="Cerrar sesión", command=self.cambiar_bd)
        sistema.add_command(label="Salir", command=self.cerrar)
        barra.add_cascade(label="Sistema", menu=sistema)
        catalogos = tk.Menu(barra, tearoff=0, **est)
        previo = None
        for m in METAS:
            if previo is not None and m.grupo != previo:
                catalogos.add_separator()
            previo = m.grupo
            sub = tk.Menu(catalogos, tearoff=0, **est)
            for texto, acc in (("Consultar", "consultar"), ("Insertar", "insertar"),
                               ("Actualizar", "actualizar"), ("Eliminar", "eliminar")):
                sub.add_command(label=texto, command=lambda k=m.key, a=acc: self._accion_menu(k, a))
            catalogos.add_cascade(label=f"{m.icono}  {m.titulo}", menu=sub)
        barra.add_cascade(label="Catálogos", menu=catalogos)
        self.root.config(menu=barra)

    def _accion_menu(self, key, accion):
        pagina = self.mostrar(key)
        if accion == "consultar":
            pagina.consultar()
        elif accion == "insertar":
            pagina.agregar()
        else:
            self.toast(f"Selecciona un registro de la lista y presiona «{accion.capitalize()}»", "info")

    def _limpiar(self):
        if self._reloj:
            self.root.after_cancel(self._reloj)
            self._reloj = None
        for w in self.root.winfo_children():
            w.destroy()

    # ---------- conexión ----------
    def pantalla_conexion(self):
        self._limpiar()
        self.root.config(menu="")      # sin menú hasta conectarse
        self.root.configure(bg=P["bg"])
        Degradado(self.root, P["g"], 190, texto="Handmade Stitches",
                  sub="Administrador de tienda  ·  elige tu base de datos para comenzar", tam=34).pack(fill="x")
        centro = tk.Frame(self.root, bg=P["bg"])
        centro.pack(expand=True)
        tk.Label(centro, text="¿A qué base de datos quieres conectarte?", bg=P["bg"], fg=P["text"],
                 font=(F, 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 22))
        opciones = [(True, "PostgreSQL", "Motor relacional de código abierto", P["info"], "◆"),
                    (False, "SQL Server", "Motor de Microsoft", P["warn"], "◇")]
        for i, (es_pg, nombre, desc, col, ico) in enumerate(opciones):
            card = tk.Frame(centro, bg=P["panel"], highlightthickness=2, highlightbackground=P["border"], padx=34, pady=26)
            card.grid(row=1, column=i, padx=14)
            tk.Label(card, text=ico, bg=P["panel"], fg=col, font=(F, 40, "bold")).pack()
            tk.Label(card, text=nombre, bg=P["panel"], fg=P["text"], font=(F, 18, "bold")).pack(pady=(4, 0))
            tk.Label(card, text=desc, bg=P["panel"], fg=P["muted"], font=(F, 10)).pack(pady=(2, 16))
            Boton(card, "Continuar  ›", lambda e=es_pg: self.pantalla_login(e), col, padx=34, pady=10, tam=11).pack()
        self.lbl_estado = tk.Label(centro, text="El servidor y la base de datos se leen del archivo .env. En el siguiente paso escribes tu usuario y contraseña.", bg=P["bg"], fg=P["muted"],
                                   font=(F, 10), wraplength=700, justify="center")
        self.lbl_estado.grid(row=2, column=0, columnspan=2, pady=(22, 0))

    # ---------- inicio de sesión ----------
    def _crear_cnn(self, es_pg):
        """Importa y crea tu clase de conexión (todavía sin conectar). Devuelve (cnn, error)."""
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                if es_pg:
                    try:
                        from cnx_pg_handmadestitches import ConexionPostgres as Cls
                    except ImportError:
                        from conexion_posgres import ConexionPostgres as Cls
                else:
                    try:
                        from cnx_ss_handmadestitches import ConexionSqlServer as Cls
                    except ImportError:
                        from conexion_sqlserver import ConexionSqlServer as Cls
                return Cls(), None
        except ImportError as e:
            return None, f"Falta instalar una librería: {e}\nEjecuta: pip install -r requirements.txt"
        except Exception as e:
            return None, f"Error inesperado: {e}"

    @staticmethod
    def _pwd_sql(pwd):
        """SQL Server: la cadena de conexión separa con ';'. Si la contraseña trae ; { } se encierra entre llaves."""
        if any(ch in pwd for ch in ";{}"):
            return "{" + pwd.replace("}", "}}") + "}"
        return pwd

    @staticmethod
    def _mensaje_login(detalle):
        t = " ".join(str(detalle).split())
        b = t.lower()
        if any(x in b for x in ("password authentication failed", "authentication failed", "login failed",
                                "18456", "28p01")) or ("role" in b and "does not exist" in b):
            return "Usuario o contraseña incorrectos."
        if ("database" in b and "does not exist" in b) or "cannot open database" in b:
            return "La base de datos indicada en el archivo .env no existe."
        if any(x in b for x in ("could not connect", "connection refused", "timeout", "timed out", "not found",
                                "network-related", "could not translate host")):
            return "No se pudo llegar al servidor. Revisa que esté encendido y que el servidor del archivo .env sea correcto."
        return "No se pudo conectar. " + t[:200]

    def pantalla_login(self, es_pg):
        cnn, error = self._crear_cnn(es_pg)
        if error:
            self.lbl_estado.config(text=error, fg=P["err"])
            return
        motor = "PostgreSQL" if es_pg else "SQL Server"
        col = P["info"] if es_pg else P["warn"]
        self._limpiar()
        self.root.config(menu="")
        self.root.configure(bg=P["bg"])
        Degradado(self.root, P["g"], 170, texto="Iniciar sesión",
                  sub=f"{motor}  ·  escribe el usuario y la contraseña de tu servidor", tam=34).pack(fill="x")
        centro = tk.Frame(self.root, bg=P["bg"])
        centro.pack(expand=True)
        card = tk.Frame(centro, bg=P["panel"], highlightthickness=2, highlightbackground=col, padx=44, pady=30)
        card.pack()
        cab = tk.Frame(card, bg=P["panel"])
        cab.pack(fill="x", pady=(0, 14))
        tk.Label(cab, text="◆" if es_pg else "◇", bg=P["panel"], fg=col, font=(F, 26, "bold")).pack(side="left")
        tk.Label(cab, text=motor, bg=P["panel"], fg=P["text"], font=(F, 18, "bold")).pack(side="left", padx=12)

        falta = not cnn.SERVER or not cnn.DATABASE_NAME
        tk.Label(card, text=f"Servidor: {cnn.SERVER or '— (falta en .env)'}   ·   Base de datos: {cnn.DATABASE_NAME or '— (falta en .env)'}",
                 bg=P["panel"], fg=P["warn"] if falta else P["muted"], font=(F, 9), anchor="w").pack(fill="x", pady=(0, 14))

        tk.Label(card, text="USUARIO", bg=P["panel"], fg=P["muted"], font=(F, 9, "bold"), anchor="w").pack(fill="x")
        e_user = entrada(card)
        e_user.config(width=36)
        e_user.pack(fill="x", ipady=7, pady=(2, 12))
        tk.Label(card, text="CONTRASEÑA", bg=P["panel"], fg=P["muted"], font=(F, 9, "bold"), anchor="w").pack(fill="x")
        fila = tk.Frame(card, bg=P["panel"])
        fila.pack(fill="x", pady=(2, 0))
        e_pass = entrada(fila, "•")
        e_pass.pack(side="left", fill="x", expand=True, ipady=7)
        ver = tk.Label(fila, text="ver", bg=P["panel"], fg=P["g"][0], font=(F, 9, "bold"), cursor="hand2", padx=10)
        ver.pack(side="left")
        ver.bind("<Button-1>", lambda ev: (e_pass.config(show="" if e_pass.cget("show") else "•"),
                                           ver.config(text="ocultar" if not e_pass.cget("show") else "ver")))
        lbl_err = tk.Label(card, text="", bg=P["panel"], fg=P["err"], font=(F, 10, "bold"), wraplength=400,
                           justify="left", anchor="w")
        lbl_err.pack(fill="x", pady=(10, 6))

        def entrar(_=None):
            usuario, pwd = e_user.get().strip(), e_pass.get()
            if not usuario or not pwd:
                lbl_err.config(text="Escribe tu usuario y tu contraseña.", fg=P["err"])
                return
            if falta:
                lbl_err.config(text="Falta el servidor o la base de datos en el archivo .env.", fg=P["err"])
                return
            lbl_err.config(text="Conectando…", fg=P["info"])
            self.root.update_idletasks()
            self.iniciar_sesion(es_pg, cnn, usuario, pwd, lbl_err, e_pass)

        botones = tk.Frame(card, bg=P["panel"])
        botones.pack(fill="x", pady=(6, 0))
        Boton(botones, "Iniciar sesión", entrar, col, padx=30, pady=10, tam=11).pack(side="right")
        Boton(botones, "‹  Cambiar motor", self.pantalla_conexion, P["panel2"], P["text"], pady=10).pack(side="right", padx=10)
        for w in (e_user, e_pass):
            w.bind("<Return>", entrar)
        self.root.bind("<Escape>", lambda ev: self.pantalla_conexion())
        e_user.focus_set()

    def iniciar_sesion(self, es_pg, cnn, usuario, pwd, lbl_err, e_pass):
        """Usa tu clase de conexión tal cual: solo se le asignan el usuario y la contraseña escritos."""
        cnn.USER = usuario
        cnn.PASSWORD = pwd if es_pg else self._pwd_sql(pwd)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                ok = cnn.crear_conexion()
        except Exception as e:
            ok = None
            buf.write(str(e))
        if ok is None:
            cnn.PASSWORD = None
            lbl_err.config(text=self._mensaje_login(buf.getvalue()), fg=P["err"])
            e_pass.delete(0, "end")
            e_pass.focus_set()
            return
        self.root.unbind("<Escape>")
        self.db = BD(cnn, es_pg)
        self.usuario = usuario
        self.pagina = "inicio"
        self.construir_shell()
        self.toast(f"Sesión iniciada como {usuario}", "ok")

    def cerrar(self):
        if self.db:
            self.db.cerrar()
        self.root.destroy()

    # ---------- estructura principal ----------
    def construir_shell(self):
        self._limpiar()
        self._menubar()
        self.root.configure(bg=P["bg"])
        sb = tk.Frame(self.root, bg=P["panel"], width=250)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        Degradado(sb, P["g"], 100, texto="Handmade", sub="Stitches  ·  Admin", tam=20).pack(fill="x")

        # pie de la barra lateral (se empaqueta primero para quedar abajo)
        pie = tk.Frame(sb, bg=P["panel"], padx=16, pady=12)
        pie.pack(side="bottom", fill="x")
        tk.Label(pie, text="TEMA", bg=P["panel"], fg=P["muted"], font=(F, 8, "bold")).pack(anchor="w")
        cb = ttk.Combobox(pie, values=list(TEMAS), state="readonly", style="H.TCombobox", font=(F, 10))
        cb.set(TEMA_ACTUAL)
        cb.pack(fill="x", pady=(2, 8))
        cb.bind("<<ComboboxSelected>>", lambda e: self.cambiar_tema(cb.get()))
        Boton(pie, "⇄  Cerrar sesión", self.cambiar_bd, P["panel2"], P["text"], pady=6, tam=9).pack(fill="x")
        Boton(pie, "⏻  Salir", self.cerrar, P["err"], pady=6, tam=9).pack(fill="x", pady=(6, 0))

        # menú desplazable (hay 11 tablas)
        zona = tk.Frame(sb, bg=P["panel"])
        zona.pack(fill="both", expand=True)
        lienzo = tk.Canvas(zona, bg=P["panel"], highlightthickness=0, bd=0, yscrollincrement=24)
        lienzo.pack(fill="both", expand=True)
        interior = tk.Frame(lienzo, bg=P["panel"])
        ventana = lienzo.create_window((0, 0), window=interior, anchor="nw")
        interior.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.bind("<Configure>", lambda e: lienzo.itemconfigure(ventana, width=e.width))

        def rueda(e):
            if interior.winfo_height() > lienzo.winfo_height():
                arriba = getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0
                lienzo.yview_scroll(-2 if arriba else 2, "units")
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            lienzo.bind(ev, rueda)

        self.nav = {}
        items = [("inicio", "Inicio", "⌂", "g0", "")] + [(m.key, m.titulo, m.icono, m.color, m.grupo) for m in METAS]
        grupo_previo = None
        for key, titulo, icono, col, grupo in items:
            if grupo and grupo != grupo_previo:
                lbl = tk.Label(interior, text=grupo, bg=P["panel"], fg=P["muted"], font=(F, 8, "bold"), anchor="w")
                lbl.pack(fill="x", padx=20, pady=(12, 2))
                lbl.bind("<MouseWheel>", rueda)
            grupo_previo = grupo or grupo_previo
            fila = tk.Frame(interior, bg=P["panel"], cursor="hand2")
            fila.pack(fill="x", pady=1)
            barra = tk.Frame(fila, bg=P["panel"], width=4)
            barra.pack(side="left", fill="y")
            ic = tk.Label(fila, text=icono, bg=P["panel"], fg=color(col), font=(F, 13, "bold"), width=3, pady=5)
            ic.pack(side="left")
            tx = tk.Label(fila, text=titulo, bg=P["panel"], fg=P["text"], font=(F, 10), anchor="w")
            tx.pack(side="left", fill="x", expand=True)
            self.nav[key] = (fila, barra, ic, tx, col)
            for w in (fila, barra, ic, tx):
                w.bind("<Button-1>", lambda e, k=key: self.mostrar(k))
                w.bind("<Enter>", lambda e, k=key: self._pintar_nav(k))
                w.bind("<Leave>", lambda e: self._pintar_nav())
                for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                    w.bind(ev, rueda)

        # contenido + barra de estado
        derecha = tk.Frame(self.root, bg=P["bg"])
        derecha.pack(side="left", fill="both", expand=True)
        estado = tk.Frame(derecha, bg=P["panel"])
        estado.pack(side="bottom", fill="x")
        db = getattr(self.db.cnn, "DATABASE_NAME", "") or ""
        srv = getattr(self.db.cnn, "SERVER", "") or ""
        tk.Label(estado, text="●", bg=P["panel"], fg=P["ok"], font=(F, 10)).pack(side="left", padx=(16, 4), pady=6)
        tk.Label(estado, text=f"Conectado · {self.db.motor}" + (f" · {db}@{srv}" if db else "") + f"  ·  Usuario: {self.usuario}",
                 bg=P["panel"], fg=P["muted"], font=(F, 9)).pack(side="left")
        self.lbl_reloj = tk.Label(estado, text="", bg=P["panel"], fg=P["muted"], font=(F, 9))
        self.lbl_reloj.pack(side="right", padx=16)
        self.contenido = tk.Frame(derecha, bg=P["bg"])
        self.contenido.pack(fill="both", expand=True)
        self._tic()
        self.mostrar(self.pagina)

    def _tic(self):
        self.lbl_reloj.config(text=datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self._reloj = self.root.after(1000, self._tic)

    def _pintar_nav(self, hover=None):
        for key, (fila, barra, ic, tx, col) in self.nav.items():
            activo = key == self.pagina
            bg = P["panel2"] if (activo or key == hover) else P["panel"]
            for w in (fila, ic, tx):
                w.config(bg=bg)
            barra.config(bg=color(col) if activo else bg)
            tx.config(font=(F, 10, "bold" if activo else "normal"))

    def mostrar(self, key):
        self.pagina = key
        for w in self.contenido.winfo_children():
            w.destroy()
        self._pintar_nav()
        pagina = PaginaInicio(self.contenido, self) if key == "inicio" else PaginaCrud(self.contenido, self, META_POR_KEY[key])
        pagina.pack(fill="both", expand=True)
        return pagina

    def cambiar_tema(self, nombre):
        aplicar_tema(nombre)
        self._preparar_tema()
        self.construir_shell()

    def cambiar_bd(self):
        """Cerrar sesión: cierra la conexión, borra la contraseña de memoria y vuelve a elegir motor."""
        if self.db:
            self.db.cerrar()
            self.db = None
        self.usuario = ""
        self.pantalla_conexion()

    # ---------- notificaciones ----------
    def toast(self, msg, tipo="ok"):
        col = {"ok": P["ok"], "error": P["err"], "warn": P["warn"], "info": P["info"]}[tipo]
        ico = {"ok": "✔", "error": "✖", "warn": "▲", "info": "●"}[tipo]
        t = tk.Toplevel(self.root)
        t.overrideredirect(True)
        t.configure(bg=col)
        try:
            t.attributes("-topmost", True)
        except tk.TclError:
            pass
        cuerpo = tk.Frame(t, bg=P["panel2"])
        cuerpo.pack(padx=(6, 0), fill="both", expand=True)
        tk.Label(cuerpo, text=f" {ico} ", bg=P["panel2"], fg=col, font=(F, 15, "bold")).pack(side="left", padx=(10, 0), pady=12)
        tk.Label(cuerpo, text=msg, bg=P["panel2"], fg=P["text"], font=(F, 11), wraplength=420, justify="left").pack(
            side="left", padx=(0, 20), pady=12)
        t.update_idletasks()
        w, h = t.winfo_reqwidth(), t.winfo_reqheight()
        desplazo = sum(x.winfo_reqheight() + 10 for x in self._toasts if x.winfo_exists())
        x = self.root.winfo_rootx() + self.root.winfo_width() - w - 30
        y = self.root.winfo_rooty() + self.root.winfo_height() - h - 56 - desplazo
        t.geometry(f"+{x}+{y}")
        self._toasts.append(t)

        def quitar():
            if t in self._toasts:
                self._toasts.remove(t)
            if t.winfo_exists():
                t.destroy()
        t.after(3200 if tipo != "error" else 5200, quitar)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()