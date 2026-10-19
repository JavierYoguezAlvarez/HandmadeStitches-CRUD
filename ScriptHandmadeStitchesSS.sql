
-- // Javier Yoguez Alvarez | 24420265 // --

CREATE DATABASE HandmadeStitches;
GO

USE HandmadeStitches;
GO

-- Crear tabla de rol
CREATE TABLE Roles (
	Id_Rol integer not null identity(1,1),
	Nombre nvarchar(50),

	CONSTRAINT pk_Roles_Id_Rol PRIMARY KEY (Id_Rol),
	CONSTRAINT chk_Roles_Nombre CHECK(Nombre IN ('ADMINISTRADOR', 'USUARIO'))
);

-- Crear tabla de usuarios
CREATE TABLE Usuarios (
	Id_Usuario integer not null identity(1,1),
	Id_Rol integer NOT NULL,
	Nombre nvarchar(100) NOT NULL,
	Ap_Paterno nvarchar(100) NOT NULL,
	Ap_Materno nvarchar(100),
	email nvarchar(150) NOT NULL,
	Contrasena_Hash nvarchar(255) NOT NULL,
	Telefono nvarchar(15) NOT NULL,
	Fecha_Registro datetime default(getdate()),
	Estado bit not null default 1,
	Email_Verificado bit not null default 0,
	Intentos_Fallidos integer NOT NULL default(0),
	Bloqueado_Hasta datetime null,
	Ultimo_Acceso datetime null,

	CONSTRAINT pk_Usuarios_Id_Usuario PRIMARY KEY(Id_Usuario),
	CONSTRAINT uq_Usuarios_email UNIQUE(email),
	CONSTRAINT fk_Usuarios_Id_Rol FOREIGN KEY(Id_Rol) REFERENCES Roles(Id_Rol),
	CONSTRAINT chk_Usuarios_Intentos CHECK(Intentos_Fallidos >= 0)
);

-- Crear tabla PerfilesUsuario (1:1 con Usuarios)
CREATE TABLE PerfilesUsuario (
	Id_Perfil integer not null identity(1,1),
	Id_Usuario integer NOT NULL,
	Foto_Url nvarchar(255) NULL,
	Fecha_Nacimiento date null,
	Biografia nvarchar(300) NULL,
	Fecha_Actualizacion datetime default(getdate()),

	CONSTRAINT pk_PerfilesUsuario_Id_Perfil PRIMARY KEY(Id_Perfil),
	CONSTRAINT uq_PerfilesUsuario_Id_Usuario UNIQUE(Id_Usuario),
	CONSTRAINT fk_PerfilesUsuario_Id_Usuario FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario) ON DELETE CASCADE
);

-- Crear tabla RecuperacionContrasena (flujo "olvidé mi contraseña")
CREATE TABLE RecuperacionContrasena (
	Id_Recuperacion integer not null identity(1,1),
	Id_Usuario integer NOT NULL,
	Token_Hash nvarchar(64) NOT NULL,
	Fecha_Solicitud datetime not null default(getdate()),
	Fecha_Expira datetime not null,
	Usado bit not null default 0,

	CONSTRAINT pk_RecuperacionContrasena_Id_Recuperacion PRIMARY KEY(Id_Recuperacion),
	CONSTRAINT uq_RecuperacionContrasena_Token UNIQUE(Token_Hash),
	CONSTRAINT fk_RecuperacionContrasena_Id_Usuario FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario) ON DELETE CASCADE,
	CONSTRAINT chk_RecuperacionContrasena_Fechas CHECK(Fecha_Expira > Fecha_Solicitud)
);

-- Crear tabla Direcciones
CREATE TABLE Direcciones (
	Id_Direccion integer not null identity(1,1),
	Id_Usuario integer NOT NULL,
	Calle nvarchar(150) NOT NULL,
	Numero nvarchar(10) NOT NULL,
	Colonia nvarchar(20) NOT NULL,
	Cuidad nvarchar(30) NOT NULL,
	Estado nvarchar(30) NOT NULL,
	Cp nvarchar(10) NOT NULL,

	CONSTRAINT pk_Direcciones_Id_Direccion PRIMARY KEY(Id_Direccion),
	CONSTRAINT fk_Id_Usuario_Id_Direccion FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario)
);

-- Crear tabla categorias
CREATE TABLE Categorias(
	Id_Categoria integer not null identity(1,1),
	Nombre nvarchar(50) NOT NULL,
	Descripcion nvarchar(255) NULL,

	CONSTRAINT pk_Categorias_Id_Categoria PRIMARY KEY(Id_Categoria)
);

-- Crear tabla ImagenesCategorias (una o varias imágenes por categoría)
CREATE TABLE ImagenesCategorias(
	Id_ImagenCategoria integer not null identity(1,1),
	Id_Categoria integer NOT NULL,
	Url_Img nvarchar(255) NOT NULL,
	Principal bit not null default 0,

	CONSTRAINT pk_ImagenesCategorias_Id_ImagenCategoria PRIMARY KEY(Id_ImagenCategoria),
	CONSTRAINT fk_ImagenesCategorias_Id_Categoria FOREIGN KEY(Id_Categoria) REFERENCES Categorias(Id_Categoria) ON DELETE CASCADE
);
-- Solo una imagen principal por categoría
CREATE UNIQUE INDEX ux_ImagenesCategorias_Principal ON ImagenesCategorias(Id_Categoria) WHERE Principal = 1;

-- Crear tabla Productos (sin Img_Principal: las imágenes están en ImagenesProductos)
CREATE TABLE Productos(
	Id_Producto integer not null identity(1,1),
	Id_Categoria integer NOT NULL,
	Nombre nvarchar(100),
	Descripcion nvarchar(300),
	Precio decimal(8,2),
	Stock integer not null default(0),
	Estado nvarchar(30) NOT NULL default('DISPONIBLE'),
	Fecha_Creacion datetime default(getdate()),

	CONSTRAINT pk_Productos_Id_Producto PRIMARY KEY(Id_Producto),
	CONSTRAINT fk_Productos_Id_Categoria FOREIGN KEY(Id_Categoria) REFERENCES Categorias(Id_Categoria),
	CONSTRAINT chk_Productos_Precio CHECK(Precio > 0),
	CONSTRAINT chk_Productos_Stock CHECK(Stock >= 0),
	CONSTRAINT chk_Productos_Estado CHECK(Estado in ('DISPONIBLE','AGOTADO'))
);

-- Crear tabla ImagenesProductos
CREATE TABLE ImagenesProductos(
	Id_ImagenProducto integer not null identity(1,1),
	Id_Producto integer NOT NULL,
	Url_Img nvarchar(255) NOT NULL,
	Principal bit not null default 0,

	CONSTRAINT pk_ImagenesProductos_Id_ImagenProducto PRIMARY KEY(Id_ImagenProducto),
	CONSTRAINT fk_ImagenesProductos_Id_Producto FOREIGN KEY(Id_Producto) REFERENCES Productos(Id_Producto)
);
-- Solo una imagen principal por producto
CREATE UNIQUE INDEX ux_ImagenesProductos_Principal ON ImagenesProductos(Id_Producto) WHERE Principal = 1;

-- Crear tabla descuentos (promociones independientes de los productos)
CREATE TABLE Descuentos(
	Id_Descuento integer not null identity(1,1),
	Nombre nvarchar(60) NOT NULL,
	Descripcion nvarchar(255) NULL,
	Porcentaje decimal(5,2) NOT NULL,
	Fecha_Ini date not null,
	Fecha_Fin date not null,
	Activo bit not null default 0,

	CONSTRAINT pk_Descuentos_Id_Descuento PRIMARY KEY(Id_Descuento),
	CONSTRAINT uq_Descuentos_Nombre UNIQUE(Nombre),
	CONSTRAINT chk_Descuentos_Porcentaje CHECK(Porcentaje > 0 AND Porcentaje <= 100),
	CONSTRAINT chk_Descuentos_Fechas CHECK(Fecha_Ini <= Fecha_Fin)
);

-- Crear tabla intermedia ProductosDescuentos (qué productos participan en qué promoción: N:M)
CREATE TABLE ProductosDescuentos(
	Id_Producto integer NOT NULL,
	Id_Descuento integer NOT NULL,

	CONSTRAINT pk_ProductosDescuentos PRIMARY KEY(Id_Producto, Id_Descuento),
	CONSTRAINT fk_ProductosDescuentos_Id_Producto FOREIGN KEY(Id_Producto) REFERENCES Productos(Id_Producto) ON DELETE CASCADE,
	CONSTRAINT fk_ProductosDescuentos_Id_Descuento FOREIGN KEY(Id_Descuento) REFERENCES Descuentos(Id_Descuento) ON DELETE CASCADE
);

-- Crear tabla Carrito
CREATE TABLE Carrito(
	Id_Carrito integer not null identity(1,1),
	Id_Usuario integer NOT NULL,
	Fecha_Creacion datetime default(getdate()),
	Estado nvarchar(20) NOT NULL default('ACTIVO'),

	CONSTRAINT pk_Carrito_Id_Carrito PRIMARY KEY(Id_Carrito),
	CONSTRAINT fk_Carrito_Id_Usuario FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario),
	CONSTRAINT chk_Carrito_Estado CHECK(Estado IN ('ACTIVO','CONVERTIDO'))
);

-- Crear tabla DetalleCarrito
CREATE TABLE DetalleCarrito(
	Id_DetalleCarrito integer not null identity(1,1),
	Id_Carrito integer NOT NULL,
	Id_Producto integer NOT NULL,
	Cantidad integer NOT NULL,
	PrecioUnitario decimal(10,2),

	CONSTRAINT pk_DetalleCarrito_Id_DetalleCarrito PRIMARY KEY(Id_DetalleCarrito),
	CONSTRAINT fk_DetalleCarrito_Id_Carrito FOREIGN KEY(Id_Carrito) REFERENCES Carrito(Id_Carrito),
	CONSTRAINT fk_DetalleCarrito_Id_Producto FOREIGN KEY(Id_Producto) REFERENCES Productos(Id_Producto),
	CONSTRAINT chk_DetalleCarrito_Cantidad CHECK(Cantidad > 0)
);

-- Crear tabla pedidos
CREATE TABLE Pedidos(
	Id_Pedido integer not null identity(1,1),
	Id_Usuario integer NOT NULL,
	Id_Direccion integer NOT NULL,
	FechaPedido datetime default(getdate()),
	Subtotal decimal(10,2) NOT NULL,
	Descuento_Tot decimal(10,2) NOT NULL default(0),
	Total decimal (10,2) NOT NULL,
	Estado nvarchar(30) NOT NULL default('PENDIENTE'),

	CONSTRAINT pk_Pedidos_Id_Pedido PRIMARY KEY(Id_Pedido),
	CONSTRAINT fk_Pedidos_Id_Usuario FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario),
	CONSTRAINT fk_Pedidos_Id_Direccion FOREIGN KEY(Id_Direccion) REFERENCES Direcciones(Id_Direccion),
	CONSTRAINT chk_Pedidos_Estado CHECK(Estado IN ('PENDIENTE','PAGADO','ENVIADO','ENTREGADO','CANCELADO')),
	CONSTRAINT chk_Pedidos_Total CHECK(Total = Subtotal - Descuento_Tot)
);

-- Crear tabla detalle pedido (guarda la promoción aplicada y el importe descontado)
CREATE TABLE DetallesPedidos(
	Id_DetallePedido integer not null identity(1,1),
	Id_Pedido integer NOT NULL,
	Id_Producto integer NOT NULL,
	Id_Descuento integer NULL,
	Cantidad integer NOT NULL,
	Precio_Uni decimal(10,2) NOT NULL,
	Descuento_Aplicado decimal(10,2) NOT NULL default(0),

	CONSTRAINT pk_DetallesPedidos_Id_DetallePedido PRIMARY KEY(Id_DetallePedido),
	CONSTRAINT fk_DetallesPedidos_Id_Pedido FOREIGN KEY(Id_Pedido) REFERENCES Pedidos(Id_Pedido),
	CONSTRAINT fk_DetallesPedidos_Id_Producto FOREIGN KEY(Id_Producto) REFERENCES Productos(Id_Producto),
	CONSTRAINT fk_DetallesPedidos_Id_Descuento FOREIGN KEY(Id_Descuento) REFERENCES Descuentos(Id_Descuento),
	CONSTRAINT chkDetallesPedidos_Cantidad CHECK(Cantidad > 0),
	CONSTRAINT chk_DetallesPedidos_Descuento CHECK(Descuento_Aplicado >= 0)
);

-- Crear tabla pagos
CREATE TABLE Pagos(
	Id_Pago integer not null identity(1,1),
	Id_Pedido integer NOT NULL,
	Metodo_Pago nvarchar(50) NOT NULL,
	Fecha_Pago datetime not null default(getdate()),
	Monto decimal(10,2) NOT NULL,
	Estado nvarchar(50) NOT NULL default('PENDIENTE'),
	Referencia nvarchar(100) NULL,

	CONSTRAINT pk_Pagos_Id_Pago PRIMARY KEY(Id_Pago),
	CONSTRAINT fk_Pagos_Id_Pedido FOREIGN KEY(Id_Pedido) REFERENCES Pedidos(Id_Pedido),
	CONSTRAINT chk_Pagos_Metodo_Pago CHECK(Metodo_Pago IN ('TARJETA', 'PAYPAL')),
	CONSTRAINT chk_Pagos_Estado CHECK(Estado IN ('APROBADO', 'RECHAZADO', 'PENDIENTE')),
	CONSTRAINT chk_Pagos_Monto CHECK(Monto > 0)
);

-- Vista: precio final de cada producto con UNA sola rebaja vigente (la de mayor porcentaje)
GO
CREATE VIEW Vw_ProductosPrecioFinal AS
SELECT P.Id_Producto,
       P.Nombre,
       P.Precio,
       COALESCE(D.Porcentaje, 0) AS Porcentaje_Descuento,
       D.Nombre AS Promocion,
       ROUND(P.Precio * (1 - COALESCE(D.Porcentaje, 0) / 100), 2) AS Precio_Final
FROM Productos P
LEFT JOIN (
    SELECT PD.Id_Producto, X.Nombre, X.Porcentaje,
           ROW_NUMBER() OVER (PARTITION BY PD.Id_Producto ORDER BY X.Porcentaje DESC) AS rn
    FROM ProductosDescuentos PD
    INNER JOIN Descuentos X ON X.Id_Descuento = PD.Id_Descuento
    WHERE X.Activo = 1 AND CAST(GETDATE() AS DATE) BETWEEN X.Fecha_Ini AND X.Fecha_Fin
) D ON D.Id_Producto = P.Id_Producto AND D.rn = 1;
GO


-- // INFORMACIÓN EN LAS TABLAS // --
-- Maestras: 5 registros (Roles solo puede tener 2 por su CHECK). Tablas de movimientos: 10 registros.

SET IDENTITY_INSERT Roles ON;
INSERT INTO Roles (Id_Rol, Nombre) VALUES
(1, 'ADMINISTRADOR'),
(2, 'USUARIO');
SET IDENTITY_INSERT Roles OFF;

SET IDENTITY_INSERT Usuarios ON;
INSERT INTO Usuarios (Id_Usuario, Id_Rol, Nombre, Ap_Paterno, Ap_Materno, email, Contrasena_Hash, Telefono, Fecha_Registro, Estado, Email_Verificado, Intentos_Fallidos, Bloqueado_Hasta, Ultimo_Acceso) VALUES
(1, 1, 'Javier',	'Yoguez',		'Alvarez',	'javier.admin@handmadestitches.com',	'pbkdf2_sha256$120000$4ba25989be6f2578a1b2be6cef220188$510f93ba0fc9ca51e31ae182f6c137e022c3fde6eaf1d04eeb2fc2523bbde2e4', '4421234567', '20260110', 1,  1,  0, NULL,                  '2026-09-16T08:05:00'),
(2, 2, 'Mariana',	'García',		'López',	'mariana.garcia@gmail.com',				'pbkdf2_sha256$120000$c9709b21fb28388bec9d621e28a0ff7a$3737615e7b39c71ae4007643be0954fb1890b9ad653a86ef40b4d9a287fb9748', '4431122334', '20260215', 1,  1,  0, NULL,                  '2026-09-14T19:42:00'),
(3, 2, 'Sofía',		'Ramírez',		'Torres',	'sofia.ramirez@outlook.com',			'pbkdf2_sha256$120000$cfe0c8e0dbb857e4307ed85ec37dddf9$5c48289fa7ab59cba5a12b51dfe3eff4e8ee28fd7220143c15970510699254ae', '4441987654', '20260302', 1,  1,  0, NULL,                  '2026-09-15T11:30:00'),
(4, 2, 'Daniela',	'Martínez',		'Cruz',		'dani.martinez@yahoo.com',				'pbkdf2_sha256$120000$006526c33b2295b0cbd4cf9984cf699d$294153bb0761efa239b9257f0ce99cfc7ecd57b15bdd5bd91d2118877d2655e6', '4451456789', '20260420', 1,  1,  2, NULL,                  '2026-09-01T14:10:00'),
(5, 2, 'Fernanda',	'López',		'Sánchez',	'fer.lopez@gmail.com',					'pbkdf2_sha256$120000$c6bd1287e0cac77e8131b49a5f5296f6$0d9f2e1b7c3c6fd05f689b8cccac52d23b617fc0202cbb3df6d5207a377c97da', '4461567890', '20260505', 0, 0, 5, '2026-09-03T19:30:00',  '2026-05-05T10:00:00');
SET IDENTITY_INSERT Usuarios OFF;

SET IDENTITY_INSERT PerfilesUsuario ON;
INSERT INTO PerfilesUsuario (Id_Perfil, Id_Usuario, Foto_Url, Fecha_Nacimiento, Biografia, Fecha_Actualizacion) VALUES
(1, 1, 'img/perfiles/javier.jpg',   '19990314', 'Administrador de la tienda y tejedor de tiempo parcial.',  '2026-01-10T12:00:00'),
(2, 2, 'img/perfiles/mariana.jpg',  '19950722', 'Me encantan los amigurumis de animales.',                   '2026-02-20T17:30:00'),
(3, 3, NULL,                        '19971103', 'Busco regalos hechos a mano para mi familia.',              '2026-03-05T09:15:00'),
(4, 4, 'img/perfiles/daniela.jpg',  '20010530', 'Coleccionista de bolsos tejidos.',                          '2026-04-22T20:45:00'),
(5, 5, NULL,                        '19980218', NULL,                                                        '2026-05-05T10:00:00');
SET IDENTITY_INSERT PerfilesUsuario OFF;

SET IDENTITY_INSERT RecuperacionContrasena ON;
INSERT INTO RecuperacionContrasena (Id_Recuperacion, Id_Usuario, Token_Hash, Fecha_Solicitud, Fecha_Expira, Usado) VALUES
(1,  2, '9b0d01289c287b9d04474d67e73fe9f1aaba8fdd34fa793448f10db79ac01b87',  '2026-03-05T18:20:00', '2026-03-05T19:20:00', 1),
(2,  3, 'be0ddc4114826052c02a3c852f8c4459b6ba5be4cbe930970a0e1558a9cb1d96',  '2026-04-11T09:05:00', '2026-04-11T10:05:00', 1),
(3,  4, 'c5e90fba5d009487e64895defea365ea6e6c1a6a831cd263aa20a3fd571b3c6d',  '2026-05-02T21:40:00', '2026-05-02T22:40:00', 1),
(4,  5, '379857ad97895db39b6e749e7cc1a1805aa9315bae1872dfc24def2b221a9912',  '2026-05-20T08:15:00', '2026-05-20T09:15:00', 0),
(5,  2, 'af34451cb9402a766706c22cb46c13e23935e1eaed9ef311dc7f1237f4650b18',  '2026-06-14T12:00:00', '2026-06-14T13:00:00', 1),
(6,  3, '984ddd2be7d5c8679b2b8a85fda81b2f33fc54f3b4f826773590e92321dd3970',  '2026-07-09T16:30:00', '2026-07-09T17:30:00', 0),
(7,  4, 'ed056c18c713327092327b43e6497b39a843e98b88336f73fb18d0a496afd3bb',  '2026-08-18T10:10:00', '2026-08-18T11:10:00', 1),
(8,  1, '851d1ccb25246c4d3569122537dd588c4363734b751d623d364f041ce53c340e',  '2026-08-25T07:45:00', '2026-08-25T08:45:00', 1),
(9,  5, '1eb3c2023acbfe8738bc35136afce73de36ffdd1277e9be1a5f48e2b4aeb60a2',  '2026-09-03T19:00:00', '2026-09-03T20:00:00', 0),
(10, 2, '747cab068f7f9f926c85aa20fda2ec0d08449118b47996e7e0e5cd0c4aa59a40', '2026-09-15T20:30:00', '2026-09-15T21:30:00', 0);
SET IDENTITY_INSERT RecuperacionContrasena OFF;

SET IDENTITY_INSERT Categorias ON;
INSERT INTO Categorias (Id_Categoria, Nombre, Descripcion) VALUES
(1, 'Amigurumis',				'Muñecos y figuras tejidas a crochet'),
(2, 'Accesorios',				'Bolsos, monederos y accesorios personales'),
(3, 'Ropa tejida',				'Suéteres, chalecos y prendas de vestir en crochet'),
(4, 'Decoración para el hogar', 'Manteles, cojines y tapetes tejidos'),
(5, 'Bebé',						'Ropa y accesorios de crochet para bebé');
SET IDENTITY_INSERT Categorias OFF;

SET IDENTITY_INSERT ImagenesCategorias ON;
INSERT INTO ImagenesCategorias (Id_ImagenCategoria, Id_Categoria, Url_Img, Principal) VALUES
(1,  1, 'img/categorias/amigurumis.jpg',    1),
(2,  1, 'img/categorias/amigurumis2.jpg',   0),
(3,  2, 'img/categorias/accesorios.jpg',    1),
(4,  2, 'img/categorias/accesorios2.jpg',   0),
(5,  3, 'img/categorias/ropa_tejida.jpg',   1),
(6,  3, 'img/categorias/ropa_tejida2.jpg',  0),
(7,  4, 'img/categorias/decoracion.jpg',    1),
(8,  4, 'img/categorias/decoracion2.jpg',   0),
(9,  5, 'img/categorias/bebe.jpg',          1),
(10, 5, 'img/categorias/bebe2.jpg',         0);
SET IDENTITY_INSERT ImagenesCategorias OFF;

SET IDENTITY_INSERT Productos ON;
INSERT INTO Productos (Id_Producto, Id_Categoria, Nombre, Descripcion, Precio, Stock, Estado, Fecha_Creacion) VALUES
(1, 1, 'Amigurumi Conejo chistoso',		'Conejito chistoso de 10cm',				349.00, 12, 'DISPONIBLE', '20260115'),
(2, 1, 'Amigurumi Gato mochi',			'Un gatito gordito de 15cm',				599.00,  0, 'AGOTADO',    '20260120'),
(3, 2, 'Tote Bag crochet color beige',	'Bolso de mano tejido en hilo de algodón',	450.00,  8, 'DISPONIBLE', '20260201'),
(4, 2, 'Monedero tejido',				'Monedero redondo tejido',					280.00,  5, 'DISPONIBLE', '20260210'),
(5, 1, 'Llavero Amigurumi Abejita',		'Llavero tejido de abeja, 6 cm',			180.00, 20, 'DISPONIBLE', '20260218');
SET IDENTITY_INSERT Productos OFF;

SET IDENTITY_INSERT Direcciones ON;
INSERT INTO Direcciones (Id_Direccion, Id_Usuario, Calle, Numero, Colonia, Cuidad, Estado, Cp) VALUES
(1,  2, 'Av. Reforma',				'120',  'Centro',			'Zamora',			'Michoacán',        '59600'),
(2,  2, 'Calle Morelos',			'45',   'San José',			'Zamora',			'Michoacán',        '59610'),
(3,  3, 'Privada Las Flores',		'8',    'Jardines del Sur',	'Guadalajara',		'Jalisco',          '44900'),
(4,  4, 'Av. Insurgentes Sur',		'2200', 'Del Valle',		'Ciudad de México',	'Ciudad de México',	'03100'),
(5,  4, 'Calle Hidalgo',			'77',   'Centro',			'Puebla',			'Puebla',           '72000'),
(6,  5, 'Av. Constituyentes',		'310',  'La Loma',			'Querétaro',		'Querétaro',        '76000'),
(7,  1, 'Pablo Galeana',			'43',   'California',		'Jiquilpan',		'Michoacán',        '59510'),
(8,  3, 'Av. Vallarta',				'4560', 'Chapalita',		'Guadalajara',		'Jalisco',          '44500'),
(9,  2, 'Calle 5 de Mayo',			'90',   'Centro',			'Uruapan',			'Michoacán',        '60000'),
(10, 5, 'Blvd. Bernardo Quintana',	'500',	'Centro Sur',		'Querétaro',		'Querétaro',        '76090');
SET IDENTITY_INSERT Direcciones OFF;

SET IDENTITY_INSERT ImagenesProductos ON;
INSERT INTO ImagenesProductos (Id_ImagenProducto, Id_Producto, Url_Img, Principal) VALUES
(1,  1, 'img/conejo_nalgon.jpg',       1),
(2,  1, 'img/conejo_nalgon2.jpg',      0),
(3,  2, 'img/gatito_mochi.jpg',        1),
(4,  2, 'img/gatito_mochi2.jpg',       0),
(5,  3, 'img/tote_bag.jpg',            1),
(6,  3, 'img/tote_bag_interior.jpg',   0),
(7,  4, 'img/monedero.jpg',            1),
(8,  4, 'img/monedero2.jpg',           0),
(9,  5, 'img/llavero_abeja.jpg',       1),
(10, 5, 'img/llavero_abeja2.jpg',      0);
SET IDENTITY_INSERT ImagenesProductos OFF;

-- Promociones (independientes de los productos)
SET IDENTITY_INSERT Descuentos ON;
INSERT INTO Descuentos (Id_Descuento, Nombre, Descripcion, Porcentaje, Fecha_Ini, Fecha_Fin, Activo) VALUES
(1, 'Hot Sale de Junio',		'Rebaja de temporada en accesorios',		10.00, '20260601', '20260615', 0),
(2, 'Mayo Cariñoso',			'Promoción por el Día de las Madres',		25.00, '20260501', '20260515', 0),
(3, 'Rebajas de Julio',			'Rebajas de mitad de año',					20.00, '20260701', '20260731', 0),
(4, 'Liquidación de Agosto',	'Liquidación de productos de temporada',	30.00, '20260810', '20260820', 0),
(5, 'Septiembre Patrio',		'Promoción de fiestas patrias',				15.00, '20260905', '20260930', 1);
SET IDENTITY_INSERT Descuentos OFF;

-- Tabla intermedia: qué productos participan en cada promoción
INSERT INTO ProductosDescuentos (Id_Producto, Id_Descuento) VALUES
(4, 1), (3, 1),
(5, 2), (1, 2),
(2, 3), (4, 3),
(2, 4), (5, 4),
(1, 5), (3, 5);

SET IDENTITY_INSERT Carrito ON;
INSERT INTO Carrito (Id_Carrito, Id_Usuario, Fecha_Creacion, Estado) VALUES
(1,  2, '20260801', 'CONVERTIDO'),
(2,  2, '20260914', 'ACTIVO'),
(3,  3, '20260720', 'CONVERTIDO'),
(4,  3, '20260915', 'ACTIVO'),
(5,  4, '20260610', 'CONVERTIDO'),
(6,  4, '20260901', 'CONVERTIDO'),
(7,  5, '20260505', 'CONVERTIDO'),
(8,  5, '20260916', 'ACTIVO'),
(9,  1, '20260910', 'ACTIVO'),
(10, 3, '20260828', 'CONVERTIDO');
SET IDENTITY_INSERT Carrito OFF;

SET IDENTITY_INSERT DetalleCarrito ON;
INSERT INTO DetalleCarrito (Id_DetalleCarrito, Id_Carrito, Id_Producto, Cantidad, PrecioUnitario) VALUES
(1,  1, 1, 1, 349.00),
(2,  1, 3, 1, 450.00),
(3,  2, 5, 2, 180.00),
(4,  3, 2, 1, 599.00),
(5,  4, 1, 1, 349.00),
(6,  5, 4, 2, 280.00),
(7,  6, 3, 1, 450.00),
(8,  7, 5, 3, 180.00),
(9,  8, 1, 1, 349.00),
(10, 9, 4, 1, 280.00);
SET IDENTITY_INSERT DetalleCarrito OFF;

-- Cada descuento del pedido corresponde a la promoción vigente en la fecha del pedido
SET IDENTITY_INSERT Pedidos ON;
INSERT INTO Pedidos (Id_Pedido, Id_Usuario, Id_Direccion, FechaPedido, Subtotal, Descuento_Tot, Total, Estado) VALUES
(1,  2, 1, '20260801', 349.00,   0.00, 349.00,  'ENTREGADO'),
(2,  3, 3, '20260720', 599.00, 119.80, 479.20,  'ENTREGADO'),
(3,  4, 5, '20260610', 560.00,  56.00, 504.00,  'ENTREGADO'),
(4,  4, 4, '20260901', 450.00,   0.00, 450.00,  'ENVIADO'),
(5,  5, 6, '20260505', 540.00, 135.00, 405.00,  'ENTREGADO'),
(6,  3, 8, '20260828', 280.00,   0.00, 280.00,  'PAGADO'),
(7,  2, 9, '20260905', 349.00,  52.35, 296.65,  'ENVIADO'),
(8,  5, 10,'20260910', 180.00,   0.00, 180.00,  'PENDIENTE'),
(9,  4, 4, '20260815', 599.00, 179.70, 419.30,  'CANCELADO'),
(10, 1, 7, '20260912', 900.00, 135.00, 765.00,  'PAGADO');
SET IDENTITY_INSERT Pedidos OFF;

SET IDENTITY_INSERT DetallesPedidos ON;
INSERT INTO DetallesPedidos (Id_DetallePedido, Id_Pedido, Id_Producto, Id_Descuento, Cantidad, Precio_Uni, Descuento_Aplicado) VALUES
(1,  1, 1, NULL, 1, 349.00,   0.00),
(2, 10, 3, 5,    2, 450.00, 135.00),
(3,  2, 2, 3,    1, 599.00, 119.80),
(4,  3, 4, 1,    2, 280.00,  56.00),
(5,  4, 3, NULL, 1, 450.00,   0.00),
(6,  5, 5, 2,    3, 180.00, 135.00),
(7,  6, 4, NULL, 1, 280.00,   0.00),
(8,  7, 1, 5,    1, 349.00,  52.35),
(9,  8, 5, NULL, 1, 180.00,   0.00),
(10, 9, 2, 4,    1, 599.00, 179.70);
SET IDENTITY_INSERT DetallesPedidos OFF;

SET IDENTITY_INSERT Pagos ON;
INSERT INTO Pagos (Id_Pago, Id_Pedido, Metodo_Pago, Fecha_Pago, Monto, Estado, Referencia) VALUES
(1,  1, 'TARJETA', '20260801', 349.00,  'APROBADO', 'TXN-0001-AB12'),
(2,  2, 'PAYPAL',  '20260720', 479.20,  'APROBADO', 'PAY-0002-CD34'),
(3,  3, 'TARJETA', '20260610', 504.00,  'APROBADO', 'TXN-0003-EF56'),
(4,  4, 'TARJETA', '20260901', 450.00,  'APROBADO', 'TXN-0004-GH78'),
(5,  5, 'PAYPAL',  '20260505', 405.00,  'APROBADO', 'PAY-0005-IJ90'),
(6,  6, 'TARJETA', '20260828', 280.00,  'APROBADO', 'TXN-0006-KL12'),
(7,  7, 'TARJETA', '20260905', 296.65,  'APROBADO', 'TXN-0007-MN34'),
(8,  9, 'PAYPAL',  '20260815', 419.30,  'RECHAZADO','PAY-0008-OP56'),
(9,  10,'TARJETA', '20260912', 765.00,  'APROBADO', 'TXN-0009-QR78'),
(10, 8, 'PAYPAL',  '20260910', 180.00,  'PENDIENTE','PAY-0010-ST90');
SET IDENTITY_INSERT Pagos OFF;


