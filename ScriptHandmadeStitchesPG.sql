
-- // Javier Yoguez Alvarez | 24420265 // --

CREATE DATABASE HandmadeStitches;

-- Crear tabla de rol
CREATE TABLE Roles (
	Id_Rol SERIAL NOT NULL,
	Nombre VARCHAR(50),

	CONSTRAINT pk_Roles_Id_Rol PRIMARY KEY (Id_Rol),
	CONSTRAINT chk_Roles_Nombre CHECK(Nombre IN ('ADMINISTRADOR', 'USUARIO'))
);

-- Crear tabla de usuarios
CREATE TABLE Usuarios (
	Id_Usuario SERIAL NOT NULL,
	Id_Rol INTEGER NOT NULL,
	Nombre VARCHAR(100) NOT NULL,
	Ap_Paterno VARCHAR(100) NOT NULL,
	Ap_Materno VARCHAR(100),
	email VARCHAR(150) NOT NULL,
	Contrasena_Hash VARCHAR(255) NOT NULL,
	Telefono VARCHAR(15) NOT NULL,
	Fecha_Registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	Estado BOOLEAN NOT NULL DEFAULT TRUE,
	Email_Verificado BOOLEAN NOT NULL DEFAULT FALSE,
	Intentos_Fallidos INTEGER NOT NULL DEFAULT 0,
	Bloqueado_Hasta TIMESTAMP NULL,
	Ultimo_Acceso TIMESTAMP NULL,

	CONSTRAINT pk_Usuarios_Id_Usuario PRIMARY KEY(Id_Usuario),
	CONSTRAINT uq_Usuarios_email UNIQUE(email),
	CONSTRAINT fk_Usuarios_Id_Rol FOREIGN KEY(Id_Rol) REFERENCES Roles(Id_Rol),
	CONSTRAINT chk_Usuarios_Intentos CHECK(Intentos_Fallidos >= 0)
);

-- Crear tabla PerfilesUsuario (1:1 con Usuarios)
CREATE TABLE PerfilesUsuario (
	Id_Perfil SERIAL NOT NULL,
	Id_Usuario INTEGER NOT NULL,
	Foto_Url VARCHAR(255) NULL,
	Fecha_Nacimiento DATE NULL,
	Biografia VARCHAR(300) NULL,
	Fecha_Actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

	CONSTRAINT pk_PerfilesUsuario_Id_Perfil PRIMARY KEY(Id_Perfil),
	CONSTRAINT uq_PerfilesUsuario_Id_Usuario UNIQUE(Id_Usuario),
	CONSTRAINT fk_PerfilesUsuario_Id_Usuario FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario) ON DELETE CASCADE
);

-- Crear tabla RecuperacionContrasena (flujo "olvidé mi contraseña")
CREATE TABLE RecuperacionContrasena (
	Id_Recuperacion SERIAL NOT NULL,
	Id_Usuario INTEGER NOT NULL,
	Token_Hash VARCHAR(64) NOT NULL,
	Fecha_Solicitud TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	Fecha_Expira TIMESTAMP NOT NULL,
	Usado BOOLEAN NOT NULL DEFAULT FALSE,

	CONSTRAINT pk_RecuperacionContrasena_Id_Recuperacion PRIMARY KEY(Id_Recuperacion),
	CONSTRAINT uq_RecuperacionContrasena_Token UNIQUE(Token_Hash),
	CONSTRAINT fk_RecuperacionContrasena_Id_Usuario FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario) ON DELETE CASCADE,
	CONSTRAINT chk_RecuperacionContrasena_Fechas CHECK(Fecha_Expira > Fecha_Solicitud)
);

-- Crear tabla Direcciones
CREATE TABLE Direcciones (
	Id_Direccion SERIAL NOT NULL,
	Id_Usuario INTEGER NOT NULL,
	Calle VARCHAR(150) NOT NULL,
	Numero VARCHAR(10) NOT NULL,
	Colonia VARCHAR(20) NOT NULL,
	Cuidad VARCHAR(30) NOT NULL,
	Estado VARCHAR(30) NOT NULL,
	Cp VARCHAR(10) NOT NULL,

	CONSTRAINT pk_Direcciones_Id_Direccion PRIMARY KEY(Id_Direccion),
	CONSTRAINT fk_Id_Usuario_Id_Direccion FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario)
);

-- Crear tabla categorias
CREATE TABLE Categorias(
	Id_Categoria SERIAL NOT NULL,
	Nombre VARCHAR(50) NOT NULL,
	Descripcion VARCHAR(255) NULL,

	CONSTRAINT pk_Categorias_Id_Categoria PRIMARY KEY(Id_Categoria)
);

-- Crear tabla ImagenesCategorias (una o varias imágenes por categoría)
CREATE TABLE ImagenesCategorias(
	Id_ImagenCategoria SERIAL NOT NULL,
	Id_Categoria INTEGER NOT NULL,
	Url_Img VARCHAR(255) NOT NULL,
	Principal BOOLEAN NOT NULL DEFAULT FALSE,

	CONSTRAINT pk_ImagenesCategorias_Id_ImagenCategoria PRIMARY KEY(Id_ImagenCategoria),
	CONSTRAINT fk_ImagenesCategorias_Id_Categoria FOREIGN KEY(Id_Categoria) REFERENCES Categorias(Id_Categoria) ON DELETE CASCADE
);
-- Solo una imagen principal por categoría
CREATE UNIQUE INDEX ux_ImagenesCategorias_Principal ON ImagenesCategorias(Id_Categoria) WHERE Principal;

-- Crear tabla Productos (sin Img_Principal: las imágenes están en ImagenesProductos)
CREATE TABLE Productos(
	Id_Producto SERIAL NOT NULL,
	Id_Categoria INTEGER NOT NULL,
	Nombre VARCHAR(100),
	Descripcion VARCHAR(300),
	Precio DECIMAL(8,2),
	Stock INTEGER NOT NULL DEFAULT 0,
	Estado VARCHAR(30) NOT NULL DEFAULT 'DISPONIBLE',
	Fecha_Creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

	CONSTRAINT pk_Productos_Id_Producto PRIMARY KEY(Id_Producto),
	CONSTRAINT fk_Productos_Id_Categoria FOREIGN KEY(Id_Categoria) REFERENCES Categorias(Id_Categoria),
	CONSTRAINT chk_Productos_Precio CHECK(Precio > 0),
	CONSTRAINT chk_Productos_Stock CHECK(Stock >= 0),
	CONSTRAINT chk_Productos_Estado CHECK(Estado in ('DISPONIBLE','AGOTADO'))
);

-- Crear tabla ImagenesProductos
CREATE TABLE ImagenesProductos(
	Id_ImagenProducto SERIAL NOT NULL,
	Id_Producto INTEGER NOT NULL,
	Url_Img VARCHAR(255) NOT NULL,
	Principal BOOLEAN NOT NULL DEFAULT FALSE,

	CONSTRAINT pk_ImagenesProductos_Id_ImagenProducto PRIMARY KEY(Id_ImagenProducto),
	CONSTRAINT fk_ImagenesProductos_Id_Producto FOREIGN KEY(Id_Producto) REFERENCES Productos(Id_Producto)
);
-- Solo una imagen principal por producto
CREATE UNIQUE INDEX ux_ImagenesProductos_Principal ON ImagenesProductos(Id_Producto) WHERE Principal;

-- Crear tabla descuentos (promociones independientes de los productos)
CREATE TABLE Descuentos(
	Id_Descuento SERIAL NOT NULL,
	Nombre VARCHAR(60) NOT NULL,
	Descripcion VARCHAR(255) NULL,
	Porcentaje DECIMAL(5,2) NOT NULL,
	Fecha_Ini DATE NOT NULL,
	Fecha_Fin DATE NOT NULL,
	Activo BOOLEAN NOT NULL DEFAULT FALSE,

	CONSTRAINT pk_Descuentos_Id_Descuento PRIMARY KEY(Id_Descuento),
	CONSTRAINT uq_Descuentos_Nombre UNIQUE(Nombre),
	CONSTRAINT chk_Descuentos_Porcentaje CHECK(Porcentaje > 0 AND Porcentaje <= 100),
	CONSTRAINT chk_Descuentos_Fechas CHECK(Fecha_Ini <= Fecha_Fin)
);

-- Crear tabla intermedia ProductosDescuentos (qué productos participan en qué promoción: N:M)
CREATE TABLE ProductosDescuentos(
	Id_Producto INTEGER NOT NULL,
	Id_Descuento INTEGER NOT NULL,

	CONSTRAINT pk_ProductosDescuentos PRIMARY KEY(Id_Producto, Id_Descuento),
	CONSTRAINT fk_ProductosDescuentos_Id_Producto FOREIGN KEY(Id_Producto) REFERENCES Productos(Id_Producto) ON DELETE CASCADE,
	CONSTRAINT fk_ProductosDescuentos_Id_Descuento FOREIGN KEY(Id_Descuento) REFERENCES Descuentos(Id_Descuento) ON DELETE CASCADE
);

-- Crear tabla Carrito
CREATE TABLE Carrito(
	Id_Carrito SERIAL NOT NULL,
	Id_Usuario INTEGER NOT NULL,
	Fecha_Creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	Estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',

	CONSTRAINT pk_Carrito_Id_Carrito PRIMARY KEY(Id_Carrito),
	CONSTRAINT fk_Carrito_Id_Usuario FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario),
	CONSTRAINT chk_Carrito_Estado CHECK(Estado IN ('ACTIVO','CONVERTIDO'))
);

-- Crear tabla DetalleCarrito
CREATE TABLE DetalleCarrito(
	Id_DetalleCarrito SERIAL NOT NULL,
	Id_Carrito INTEGER NOT NULL,
	Id_Producto INTEGER NOT NULL,
	Cantidad INTEGER NOT NULL,
	PrecioUnitario DECIMAL(10,2),

	CONSTRAINT pk_DetalleCarrito_Id_DetalleCarrito PRIMARY KEY(Id_DetalleCarrito),
	CONSTRAINT fk_DetalleCarrito_Id_Carrito FOREIGN KEY(Id_Carrito) REFERENCES Carrito(Id_Carrito),
	CONSTRAINT fk_DetalleCarrito_Id_Producto FOREIGN KEY(Id_Producto) REFERENCES Productos(Id_Producto),
	CONSTRAINT chk_DetalleCarrito_Cantidad CHECK(Cantidad > 0)
);

-- Crear tabla pedidos
CREATE TABLE Pedidos(
	Id_Pedido SERIAL NOT NULL,
	Id_Usuario INTEGER NOT NULL,
	Id_Direccion INTEGER NOT NULL,
	FechaPedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	Subtotal DECIMAL(10,2) NOT NULL,
	Descuento_Tot DECIMAL(10,2) NOT NULL DEFAULT 0,
	Total DECIMAL (10,2) NOT NULL,
	Estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',

	CONSTRAINT pk_Pedidos_Id_Pedido PRIMARY KEY(Id_Pedido),
	CONSTRAINT fk_Pedidos_Id_Usuario FOREIGN KEY(Id_Usuario) REFERENCES Usuarios(Id_Usuario),
	CONSTRAINT fk_Pedidos_Id_Direccion FOREIGN KEY(Id_Direccion) REFERENCES Direcciones(Id_Direccion),
	CONSTRAINT chk_Pedidos_Estado CHECK(Estado IN ('PENDIENTE','PAGADO','ENVIADO','ENTREGADO','CANCELADO')),
	CONSTRAINT chk_Pedidos_Total CHECK(Total = Subtotal - Descuento_Tot)
);

-- Crear tabla detalle pedido (guarda la promoción aplicada y el importe descontado)
CREATE TABLE DetallesPedidos(
	Id_DetallePedido SERIAL NOT NULL,
	Id_Pedido INTEGER NOT NULL,
	Id_Producto INTEGER NOT NULL,
	Id_Descuento INTEGER NULL,
	Cantidad INTEGER NOT NULL,
	Precio_Uni DECIMAL(10,2) NOT NULL,
	Descuento_Aplicado DECIMAL(10,2) NOT NULL DEFAULT 0,

	CONSTRAINT pk_DetallesPedidos_Id_DetallePedido PRIMARY KEY(Id_DetallePedido),
	CONSTRAINT fk_DetallesPedidos_Id_Pedido FOREIGN KEY(Id_Pedido) REFERENCES Pedidos(Id_Pedido),
	CONSTRAINT fk_DetallesPedidos_Id_Producto FOREIGN KEY(Id_Producto) REFERENCES Productos(Id_Producto),
	CONSTRAINT fk_DetallesPedidos_Id_Descuento FOREIGN KEY(Id_Descuento) REFERENCES Descuentos(Id_Descuento),
	CONSTRAINT chkDetallesPedidos_Cantidad CHECK(Cantidad > 0),
	CONSTRAINT chk_DetallesPedidos_Descuento CHECK(Descuento_Aplicado >= 0)
);

-- Crear tabla pagos
CREATE TABLE Pagos(
	Id_Pago SERIAL NOT NULL,
	Id_Pedido INTEGER NOT NULL,
	Metodo_Pago VARCHAR(50) NOT NULL,
	Fecha_Pago TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	Monto DECIMAL(10,2) NOT NULL,
	Estado VARCHAR(50) NOT NULL DEFAULT 'PENDIENTE',
	Referencia VARCHAR(100) NULL,

	CONSTRAINT pk_Pagos_Id_Pago PRIMARY KEY(Id_Pago),
	CONSTRAINT fk_Pagos_Id_Pedido FOREIGN KEY(Id_Pedido) REFERENCES Pedidos(Id_Pedido),
	CONSTRAINT chk_Pagos_Metodo_Pago CHECK(Metodo_Pago IN ('TARJETA', 'PAYPAL')),
	CONSTRAINT chk_Pagos_Estado CHECK(Estado IN ('APROBADO', 'RECHAZADO', 'PENDIENTE')),
	CONSTRAINT chk_Pagos_Monto CHECK(Monto > 0)
);

-- Vista: precio final de cada producto con UNA sola rebaja vigente (la de mayor porcentaje)
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
    WHERE X.Activo = TRUE AND CURRENT_DATE BETWEEN X.Fecha_Ini AND X.Fecha_Fin
) D ON D.Id_Producto = P.Id_Producto AND D.rn = 1;


-- // INFORMACIÓN EN LAS TABLAS // --
-- Maestras: 5 registros (Roles solo puede tener 2 por su CHECK). Tablas de movimientos: 10 registros.

INSERT INTO Roles (Id_Rol, Nombre) VALUES
(1, 'ADMINISTRADOR'),
(2, 'USUARIO');

INSERT INTO Usuarios (Id_Usuario, Id_Rol, Nombre, Ap_Paterno, Ap_Materno, email, Contrasena_Hash, Telefono, Fecha_Registro, Estado, Email_Verificado, Intentos_Fallidos, Bloqueado_Hasta, Ultimo_Acceso) VALUES
(1, 1, 'Javier',	'Yoguez',		'Alvarez',	'javier.admin@handmadestitches.com',	'pbkdf2_sha256$120000$4ba25989be6f2578a1b2be6cef220188$510f93ba0fc9ca51e31ae182f6c137e022c3fde6eaf1d04eeb2fc2523bbde2e4', '4421234567', '2026-01-10', TRUE,  TRUE,  0, NULL,                  '2026-09-16T08:05:00'),
(2, 2, 'Mariana',	'García',		'López',	'mariana.garcia@gmail.com',				'pbkdf2_sha256$120000$c9709b21fb28388bec9d621e28a0ff7a$3737615e7b39c71ae4007643be0954fb1890b9ad653a86ef40b4d9a287fb9748', '4431122334', '2026-02-15', TRUE,  TRUE,  0, NULL,                  '2026-09-14T19:42:00'),
(3, 2, 'Sofía',		'Ramírez',		'Torres',	'sofia.ramirez@outlook.com',			'pbkdf2_sha256$120000$cfe0c8e0dbb857e4307ed85ec37dddf9$5c48289fa7ab59cba5a12b51dfe3eff4e8ee28fd7220143c15970510699254ae', '4441987654', '2026-03-02', TRUE,  TRUE,  0, NULL,                  '2026-09-15T11:30:00'),
(4, 2, 'Daniela',	'Martínez',		'Cruz',		'dani.martinez@yahoo.com',				'pbkdf2_sha256$120000$006526c33b2295b0cbd4cf9984cf699d$294153bb0761efa239b9257f0ce99cfc7ecd57b15bdd5bd91d2118877d2655e6', '4451456789', '2026-04-20', TRUE,  TRUE,  2, NULL,                  '2026-09-01T14:10:00'),
(5, 2, 'Fernanda',	'López',		'Sánchez',	'fer.lopez@gmail.com',					'pbkdf2_sha256$120000$c6bd1287e0cac77e8131b49a5f5296f6$0d9f2e1b7c3c6fd05f689b8cccac52d23b617fc0202cbb3df6d5207a377c97da', '4461567890', '2026-05-05', FALSE, FALSE, 5, '2026-09-03T19:30:00',  '2026-05-05T10:00:00');

INSERT INTO PerfilesUsuario (Id_Perfil, Id_Usuario, Foto_Url, Fecha_Nacimiento, Biografia, Fecha_Actualizacion) VALUES
(1, 1, 'img/perfiles/javier.jpg',   '1999-03-14', 'Administrador de la tienda y tejedor de tiempo parcial.',  '2026-01-10T12:00:00'),
(2, 2, 'img/perfiles/mariana.jpg',  '1995-07-22', 'Me encantan los amigurumis de animales.',                   '2026-02-20T17:30:00'),
(3, 3, NULL,                        '1997-11-03', 'Busco regalos hechos a mano para mi familia.',              '2026-03-05T09:15:00'),
(4, 4, 'img/perfiles/daniela.jpg',  '2001-05-30', 'Coleccionista de bolsos tejidos.',                          '2026-04-22T20:45:00'),
(5, 5, NULL,                        '1998-02-18', NULL,                                                        '2026-05-05T10:00:00');

INSERT INTO RecuperacionContrasena (Id_Recuperacion, Id_Usuario, Token_Hash, Fecha_Solicitud, Fecha_Expira, Usado) VALUES
(1,  2, '9b0d01289c287b9d04474d67e73fe9f1aaba8fdd34fa793448f10db79ac01b87',  '2026-03-05T18:20:00', '2026-03-05T19:20:00', TRUE),
(2,  3, 'be0ddc4114826052c02a3c852f8c4459b6ba5be4cbe930970a0e1558a9cb1d96',  '2026-04-11T09:05:00', '2026-04-11T10:05:00', TRUE),
(3,  4, 'c5e90fba5d009487e64895defea365ea6e6c1a6a831cd263aa20a3fd571b3c6d',  '2026-05-02T21:40:00', '2026-05-02T22:40:00', TRUE),
(4,  5, '379857ad97895db39b6e749e7cc1a1805aa9315bae1872dfc24def2b221a9912',  '2026-05-20T08:15:00', '2026-05-20T09:15:00', FALSE),
(5,  2, 'af34451cb9402a766706c22cb46c13e23935e1eaed9ef311dc7f1237f4650b18',  '2026-06-14T12:00:00', '2026-06-14T13:00:00', TRUE),
(6,  3, '984ddd2be7d5c8679b2b8a85fda81b2f33fc54f3b4f826773590e92321dd3970',  '2026-07-09T16:30:00', '2026-07-09T17:30:00', FALSE),
(7,  4, 'ed056c18c713327092327b43e6497b39a843e98b88336f73fb18d0a496afd3bb',  '2026-08-18T10:10:00', '2026-08-18T11:10:00', TRUE),
(8,  1, '851d1ccb25246c4d3569122537dd588c4363734b751d623d364f041ce53c340e',  '2026-08-25T07:45:00', '2026-08-25T08:45:00', TRUE),
(9,  5, '1eb3c2023acbfe8738bc35136afce73de36ffdd1277e9be1a5f48e2b4aeb60a2',  '2026-09-03T19:00:00', '2026-09-03T20:00:00', FALSE),
(10, 2, '747cab068f7f9f926c85aa20fda2ec0d08449118b47996e7e0e5cd0c4aa59a40', '2026-09-15T20:30:00', '2026-09-15T21:30:00', FALSE);

INSERT INTO Categorias (Id_Categoria, Nombre, Descripcion) VALUES
(1, 'Amigurumis',				'Muñecos y figuras tejidas a crochet'),
(2, 'Accesorios',				'Bolsos, monederos y accesorios personales'),
(3, 'Ropa tejida',				'Suéteres, chalecos y prendas de vestir en crochet'),
(4, 'Decoración para el hogar', 'Manteles, cojines y tapetes tejidos'),
(5, 'Bebé',						'Ropa y accesorios de crochet para bebé');

INSERT INTO ImagenesCategorias (Id_ImagenCategoria, Id_Categoria, Url_Img, Principal) VALUES
(1,  1, 'img/categorias/amigurumis.jpg',    TRUE),
(2,  1, 'img/categorias/amigurumis2.jpg',   FALSE),
(3,  2, 'img/categorias/accesorios.jpg',    TRUE),
(4,  2, 'img/categorias/accesorios2.jpg',   FALSE),
(5,  3, 'img/categorias/ropa_tejida.jpg',   TRUE),
(6,  3, 'img/categorias/ropa_tejida2.jpg',  FALSE),
(7,  4, 'img/categorias/decoracion.jpg',    TRUE),
(8,  4, 'img/categorias/decoracion2.jpg',   FALSE),
(9,  5, 'img/categorias/bebe.jpg',          TRUE),
(10, 5, 'img/categorias/bebe2.jpg',         FALSE);

INSERT INTO Productos (Id_Producto, Id_Categoria, Nombre, Descripcion, Precio, Stock, Estado, Fecha_Creacion) VALUES
(1, 1, 'Amigurumi Conejo chistoso',		'Conejito chistoso de 10cm',				349.00, 12, 'DISPONIBLE', '2026-01-15'),
(2, 1, 'Amigurumi Gato mochi',			'Un gatito gordito de 15cm',				599.00,  0, 'AGOTADO',    '2026-01-20'),
(3, 2, 'Tote Bag crochet color beige',	'Bolso de mano tejido en hilo de algodón',	450.00,  8, 'DISPONIBLE', '2026-02-01'),
(4, 2, 'Monedero tejido',				'Monedero redondo tejido',					280.00,  5, 'DISPONIBLE', '2026-02-10'),
(5, 1, 'Llavero Amigurumi Abejita',		'Llavero tejido de abeja, 6 cm',			180.00, 20, 'DISPONIBLE', '2026-02-18');

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

INSERT INTO ImagenesProductos (Id_ImagenProducto, Id_Producto, Url_Img, Principal) VALUES
(1,  1, 'img/conejo_nalgon.jpg',       TRUE),
(2,  1, 'img/conejo_nalgon2.jpg',      FALSE),
(3,  2, 'img/gatito_mochi.jpg',        TRUE),
(4,  2, 'img/gatito_mochi2.jpg',       FALSE),
(5,  3, 'img/tote_bag.jpg',            TRUE),
(6,  3, 'img/tote_bag_interior.jpg',   FALSE),
(7,  4, 'img/monedero.jpg',            TRUE),
(8,  4, 'img/monedero2.jpg',           FALSE),
(9,  5, 'img/llavero_abeja.jpg',       TRUE),
(10, 5, 'img/llavero_abeja2.jpg',      FALSE);

-- Promociones (independientes de los productos)
INSERT INTO Descuentos (Id_Descuento, Nombre, Descripcion, Porcentaje, Fecha_Ini, Fecha_Fin, Activo) VALUES
(1, 'Hot Sale de Junio',		'Rebaja de temporada en accesorios',		10.00, '2026-06-01', '2026-06-15', FALSE),
(2, 'Mayo Cariñoso',			'Promoción por el Día de las Madres',		25.00, '2026-05-01', '2026-05-15', FALSE),
(3, 'Rebajas de Julio',			'Rebajas de mitad de año',					20.00, '2026-07-01', '2026-07-31', FALSE),
(4, 'Liquidación de Agosto',	'Liquidación de productos de temporada',	30.00, '2026-08-10', '2026-08-20', FALSE),
(5, 'Septiembre Patrio',		'Promoción de fiestas patrias',				15.00, '2026-09-05', '2026-09-30', TRUE);

-- Tabla intermedia: qué productos participan en cada promoción
INSERT INTO ProductosDescuentos (Id_Producto, Id_Descuento) VALUES
(4, 1), (3, 1),
(5, 2), (1, 2),
(2, 3), (4, 3),
(2, 4), (5, 4),
(1, 5), (3, 5);

INSERT INTO Carrito (Id_Carrito, Id_Usuario, Fecha_Creacion, Estado) VALUES
(1,  2, '2026-08-01', 'CONVERTIDO'),
(2,  2, '2026-09-14', 'ACTIVO'),
(3,  3, '2026-07-20', 'CONVERTIDO'),
(4,  3, '2026-09-15', 'ACTIVO'),
(5,  4, '2026-06-10', 'CONVERTIDO'),
(6,  4, '2026-09-01', 'CONVERTIDO'),
(7,  5, '2026-05-05', 'CONVERTIDO'),
(8,  5, '2026-09-16', 'ACTIVO'),
(9,  1, '2026-09-10', 'ACTIVO'),
(10, 3, '2026-08-28', 'CONVERTIDO');

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

-- Cada descuento del pedido corresponde a la promoción vigente en la fecha del pedido
INSERT INTO Pedidos (Id_Pedido, Id_Usuario, Id_Direccion, FechaPedido, Subtotal, Descuento_Tot, Total, Estado) VALUES
(1,  2, 1, '2026-08-01', 349.00,   0.00, 349.00,  'ENTREGADO'),
(2,  3, 3, '2026-07-20', 599.00, 119.80, 479.20,  'ENTREGADO'),
(3,  4, 5, '2026-06-10', 560.00,  56.00, 504.00,  'ENTREGADO'),
(4,  4, 4, '2026-09-01', 450.00,   0.00, 450.00,  'ENVIADO'),
(5,  5, 6, '2026-05-05', 540.00, 135.00, 405.00,  'ENTREGADO'),
(6,  3, 8, '2026-08-28', 280.00,   0.00, 280.00,  'PAGADO'),
(7,  2, 9, '2026-09-05', 349.00,  52.35, 296.65,  'ENVIADO'),
(8,  5, 10,'2026-09-10', 180.00,   0.00, 180.00,  'PENDIENTE'),
(9,  4, 4, '2026-08-15', 599.00, 179.70, 419.30,  'CANCELADO'),
(10, 1, 7, '2026-09-12', 900.00, 135.00, 765.00,  'PAGADO');

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

INSERT INTO Pagos (Id_Pago, Id_Pedido, Metodo_Pago, Fecha_Pago, Monto, Estado, Referencia) VALUES
(1,  1, 'TARJETA', '2026-08-01', 349.00,  'APROBADO', 'TXN-0001-AB12'),
(2,  2, 'PAYPAL',  '2026-07-20', 479.20,  'APROBADO', 'PAY-0002-CD34'),
(3,  3, 'TARJETA', '2026-06-10', 504.00,  'APROBADO', 'TXN-0003-EF56'),
(4,  4, 'TARJETA', '2026-09-01', 450.00,  'APROBADO', 'TXN-0004-GH78'),
(5,  5, 'PAYPAL',  '2026-05-05', 405.00,  'APROBADO', 'PAY-0005-IJ90'),
(6,  6, 'TARJETA', '2026-08-28', 280.00,  'APROBADO', 'TXN-0006-KL12'),
(7,  7, 'TARJETA', '2026-09-05', 296.65,  'APROBADO', 'TXN-0007-MN34'),
(8,  9, 'PAYPAL',  '2026-08-15', 419.30,  'RECHAZADO','PAY-0008-OP56'),
(9,  10,'TARJETA', '2026-09-12', 765.00,  'APROBADO', 'TXN-0009-QR78'),
(10, 8, 'PAYPAL',  '2026-09-10', 180.00,  'PENDIENTE','PAY-0010-ST90');


-- Sincronizar las secuencias SERIAL con los datos insertados
SELECT setval('roles_id_rol_seq', (SELECT MAX(Id_Rol) FROM Roles));
SELECT setval('usuarios_id_usuario_seq', (SELECT MAX(Id_Usuario) FROM Usuarios));
SELECT setval('perfilesusuario_id_perfil_seq', (SELECT MAX(Id_Perfil) FROM PerfilesUsuario));
SELECT setval('recuperacioncontrasena_id_recuperacion_seq', (SELECT MAX(Id_Recuperacion) FROM RecuperacionContrasena));
SELECT setval('categorias_id_categoria_seq', (SELECT MAX(Id_Categoria) FROM Categorias));
SELECT setval('imagenescategorias_id_imagencategoria_seq', (SELECT MAX(Id_ImagenCategoria) FROM ImagenesCategorias));
SELECT setval('productos_id_producto_seq', (SELECT MAX(Id_Producto) FROM Productos));
SELECT setval('direcciones_id_direccion_seq', (SELECT MAX(Id_Direccion) FROM Direcciones));
SELECT setval('imagenesproductos_id_imagenproducto_seq', (SELECT MAX(Id_ImagenProducto) FROM ImagenesProductos));
SELECT setval('descuentos_id_descuento_seq', (SELECT MAX(Id_Descuento) FROM Descuentos));
SELECT setval('carrito_id_carrito_seq', (SELECT MAX(Id_Carrito) FROM Carrito));
SELECT setval('detallecarrito_id_detallecarrito_seq', (SELECT MAX(Id_DetalleCarrito) FROM DetalleCarrito));
SELECT setval('pedidos_id_pedido_seq', (SELECT MAX(Id_Pedido) FROM Pedidos));
SELECT setval('detallespedidos_id_detallepedido_seq', (SELECT MAX(Id_DetallePedido) FROM DetallesPedidos));
SELECT setval('pagos_id_pago_seq', (SELECT MAX(Id_Pago) FROM Pagos));
