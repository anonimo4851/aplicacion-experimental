# api_rest.py - API REST integrada con el sistema de pedidos
import json
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from datetime import datetime
import traceback
import os


class ManejadorAPI(BaseHTTPRequestHandler):
    """Manejador HTTP para la API REST con CORS correcto"""
    
    inventario = None
    registro = None
    app_principal = None
    pedidos_web = None
    
    def do_OPTIONS(self):
        """Manejar preflight CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_GET(self):
        """Manejar peticiones GET"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        print(f"📥 GET {path}")
        
        try:
            # ========== ENDPOINTS DE LA API (DEBEN IR PRIMERO) ==========
            if path == "/api/productos":
                print("✅ Redirigiendo a _obtener_productos")
                self._obtener_productos()
            elif path == "/api/categorias":
                self._obtener_categorias()
            elif path.startswith("/api/producto/"):
                self._obtener_producto_individual(path)
            elif path == "/api/estadisticas":
                self._obtener_estadisticas()
            elif path == "/api/pedidos/pendientes":
                self._obtener_pedidos_pendientes()
            elif path == "/api" or path == "/api/":
                self._enviar_respuesta(200, {
                    "mensaje": "API de Comidas Rápidas",
                    "version": "1.0",
                    "endpoints": [
                        "GET /api/productos",
                        "GET /api/categorias",
                        "GET /api/estadisticas",
                        "GET /api/pedidos/pendientes",
                        "POST /api/pedido",
                        "POST /api/validar-stock"
                    ]
                })
            
            # ========== SERVIR PÁGINA WEB ==========
            elif path == '/' or path == '/index.html':
                print("🌐 Sirviendo página web")
                self._servir_pagina_web()
            elif path == '/style.css':
                self._servir_archivo('style.css', 'text/css')
            elif path == '/script.js':
                self._servir_archivo('script.js', 'application/javascript')
            elif path == '/favicon.ico':
                self._servir_favicon()
            elif path.endswith('.html'):
                self._servir_archivo(path[1:], 'text/html')
            elif path.endswith('.css'):
                self._servir_archivo(path[1:], 'text/css')
            elif path.endswith('.js'):
                self._servir_archivo(path[1:], 'application/javascript')
            
            # ========== CUALQUIER OTRA COSA = 404 ==========
            else:
                print(f"❌ Ruta no encontrada: {path}")
                self._enviar_error(404, f"Endpoint no encontrado: {path}")
                
        except Exception as e:
            print(f"❌ Error en GET: {e}")
            traceback.print_exc()
            self._enviar_error(500, str(e))
    
    def do_POST(self):
        """Manejar peticiones POST"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        print(f"📮 POST {path}")
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
            datos = json.loads(body) if body else {}
            
            if path == "/api/pedido":
                self._crear_pedido(datos)
            elif path == "/api/validar-stock":
                self._validar_stock(datos)
            else:
                self._enviar_error(404, f"Endpoint no encontrado: {path}")
        except Exception as e:
            print(f"❌ Error en POST: {e}")
            traceback.print_exc()
            self._enviar_error(500, str(e))

    def _servir_pagina_web(self):
        """Servir la página web principal"""
        try:
            # Intentar diferentes ubicaciones del archivo
            rutas_posibles = [
                "index.html",
                "web/index.html",
                "pagina_web/index.html",
                "../index.html"
            ]
            
            html = None
            for ruta in rutas_posibles:
                if os.path.exists(ruta):
                    with open(ruta, 'r', encoding='utf-8') as f:
                        html = f.read()
                    print(f"✅ Sirviendo página web desde: {ruta}")
                    break
            
            if html is None:
                # Si no se encuentra, servir una página por defecto
                html = self._generar_pagina_default()
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self._enviar_headers_cors()
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ Error sirviendo página web: {e}")
            self._enviar_error(500, f"Error sirviendo página web: {str(e)}")

    def _servir_archivo(self, nombre_archivo, content_type):
        """Servir archivos estáticos (CSS, JS)"""
        try:
            rutas_posibles = [
                nombre_archivo,
                f"web/{nombre_archivo}",
                f"pagina_web/{nombre_archivo}",
                f"../{nombre_archivo}"
            ]
            
            contenido = None
            for ruta in rutas_posibles:
                if os.path.exists(ruta):
                    with open(ruta, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                    print(f"✅ Sirviendo {nombre_archivo} desde: {ruta}")
                    break
            
            if contenido is None:
                self._enviar_error(404, f"Archivo {nombre_archivo} no encontrado")
                return
            
            self.send_response(200)
            self.send_header('Content-Type', f'{content_type}; charset=utf-8')
            self._enviar_headers_cors()
            self.end_headers()
            self.wfile.write(contenido.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ Error sirviendo {nombre_archivo}: {e}")
            self._enviar_error(500, str(e))

    def _servir_favicon(self):
        """Servir favicon (evitar errores 404)"""
        self.send_response(204)  # No content
        self._enviar_headers_cors()
        self.end_headers()

    def _generar_pagina_default(self):
        """Generar una página HTML por defecto si no se encuentra index.html"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Comidas Rápidas</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; }
                h1 { color: #ff6b6b; }
                .info { background: #f0f0f0; padding: 20px; border-radius: 10px; }
            </style>
        </head>
        <body>
            <h1>🍔 API Comidas Rápidas</h1>
            <div class="info">
                <p>La API REST está funcionando correctamente.</p>
                <p>Endpoints disponibles:</p>
                <code>
                    GET /api/productos<br>
                    GET /api/categorias<br>
                    POST /api/pedido<br>
                    POST /api/validar-stock
                </code>
                <p><br>Coloca tu archivo index.html en la misma carpeta para ver la página web.</p>
            </div>
        </body>
        </html>
        """

    def _enviar_headers_cors(self):
        """Enviar headers CORS"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
    
    def _enviar_respuesta(self, codigo, datos):
        """Enviar respuesta JSON con CORS"""
        self.send_response(codigo)
        self._enviar_headers_cors()
        self.end_headers()
        respuesta = json.dumps(datos, ensure_ascii=False, indent=2)
        self.wfile.write(respuesta.encode('utf-8'))
        print(f"✅ Respuesta {codigo} enviada")
    
    def _enviar_error(self, codigo, mensaje):
        """Enviar respuesta de error con CORS"""
        self._enviar_respuesta(codigo, {"error": True, "mensaje": mensaje})
    
    def _obtener_productos(self):
        """GET /api/productos"""
        if not self.inventario:
            # Devolver datos de ejemplo si no hay inventario
            productos_ejemplo = [
                {"nombre": "Hamburguesa Clásica", "categoria": "Hamburguesas", "precio": 1500, "cantidad": 10},
                {"nombre": "Pizza Margarita", "categoria": "Pizzas", "precio": 2500, "cantidad": 5},
                {"nombre": "Coca-Cola", "categoria": "Bebidas", "precio": 500, "cantidad": 20},
                {"nombre": "Papas Fritas", "categoria": "Acompañantes", "precio": 800, "cantidad": 15},
            ]
            self._enviar_respuesta(200, {
                "productos": productos_ejemplo,
                "total": len(productos_ejemplo),
                "categorias": ["Hamburguesas", "Pizzas", "Bebidas", "Acompañantes"]
            })
            return
        
        try:
            productos_raw = self.inventario.obtener_todos_productos()
            productos_formateados = []
            
            # Verificar el tipo de datos recibido
            if productos_raw is None:
                productos_raw = {}
            
            # Procesar según el tipo de dato
            if isinstance(productos_raw, dict):
                # Es un diccionario: {"nombre": {...}, ...}
                for nombre, datos in productos_raw.items():
                    if isinstance(datos, dict):
                        productos_formateados.append({
                            "nombre": nombre,
                            "categoria": datos.get("categoria", "Sin categoría"),
                            "precio": datos.get("precio", 0),
                            "cantidad": datos.get("cantidad", 0)
                        })
                    elif isinstance(datos, (int, float)):
                        # Si el valor es un número, asumimos que es la cantidad
                        productos_formateados.append({
                            "nombre": nombre,
                            "categoria": "General",
                            "precio": 0,
                            "cantidad": datos
                        })
                    else:
                        print(f"⚠️ Tipo de datos no esperado para {nombre}: {type(datos)}")
                        
            elif isinstance(productos_raw, list):
                # Es una lista: [{"nombre": "...", ...}, ...]
                for item in productos_raw:
                    if isinstance(item, dict):
                        nombre = item.get("nombre") or item.get("name") or "N/A"
                        productos_formateados.append({
                            "nombre": nombre,
                            "categoria": item.get("categoria") or item.get("category") or "Sin categoría",
                            "precio": item.get("precio") or item.get("price") or 0,
                            "cantidad": item.get("cantidad") or item.get("quantity") or 0
                        })
                    elif isinstance(item, str):
                        # Si es una lista de strings
                        productos_formateados.append({
                            "nombre": item,
                            "categoria": "General",
                            "precio": 0,
                            "cantidad": 0
                        })
            else:
                print(f"❌ Tipo de datos no soportado: {type(productos_raw)}")
                productos_formateados = []
            
            # Si no hay productos, usar ejemplos
            if not productos_formateados:
                productos_formateados = [
                    {"nombre": "Hamburguesa", "categoria": "Hamburguesas", "precio": 1500, "cantidad": 10},
                    {"nombre": "Pizza", "categoria": "Pizzas", "precio": 2500, "cantidad": 5},
                ]
            
            # Extraer categorías únicas
            categorias = []
            for p in productos_formateados:
                cat = p.get("categoria", "Sin categoría")
                if cat not in categorias:
                    categorias.append(cat)
            
            self._enviar_respuesta(200, {
                "productos": productos_formateados,
                "total": len(productos_formateados),
                "categorias": categorias
            })
            
        except Exception as e:
            print(f"❌ Error en _obtener_productos: {e}")
            traceback.print_exc()
            # Devolver array vacío en caso de error
            self._enviar_respuesta(200, {
                "productos": [],
                "total": 0,
                "categorias": [],
                "error": str(e)
            })
        
            
    def _obtener_categorias(self):
        """GET /api/categorias"""
        try:
            try:
                with open("categorias.json", "r", encoding="utf-8") as f:
                    categorias = json.load(f)
            except:
                categorias = ["Hamburguesas", "Pizzas", "Bebidas", "Postres", "Acompañantes"]
            self._enviar_respuesta(200, {"categorias": categorias})
        except Exception as e:
            self._enviar_error(500, str(e))
    
    def _obtener_producto_individual(self, path):
        """GET /api/producto/{nombre}"""
        try:
            nombre = urllib.parse.unquote(path.split("/")[-1])
            if self.inventario:
                producto = self.inventario.obtener_producto(nombre)
                if producto:
                    self._enviar_respuesta(200, {"producto": producto})
                else:
                    self._enviar_error(404, "Producto no encontrado")
            else:
                self._enviar_error(500, "Inventario no disponible")
        except Exception as e:
            self._enviar_error(500, str(e))
    
    def _obtener_estadisticas(self):
        """GET /api/estadisticas"""
        try:
            if not self.inventario:
                self._enviar_respuesta(200, {
                    "total_productos": 0, "total_unidades": 0,
                    "valor_inventario": 0, "productos_bajo_stock": 0, "productos_agotados": 0
                })
                return
            
            productos_raw = self.inventario.obtener_todos_productos()
            
            if isinstance(productos_raw, dict):
                productos = list(productos_raw.values())
            elif isinstance(productos_raw, list):
                productos = productos_raw
            else:
                productos = []
            
            total_unidades = 0
            valor_total = 0
            bajo_stock = 0
            agotados = 0
            
            for p in productos:
                if isinstance(p, dict):
                    cantidad = p.get("cantidad", 0)
                    precio = p.get("precio", 0)
                    total_unidades += cantidad
                    valor_total += cantidad * precio
                    
                    if cantidad == 0:
                        agotados += 1
                    elif cantidad < 10:
                        bajo_stock += 1
            
            self._enviar_respuesta(200, {
                "total_productos": len(productos),
                "total_unidades": total_unidades,
                "valor_inventario": valor_total,
                "productos_bajo_stock": bajo_stock,
                "productos_agotados": agotados
            })
        except Exception as e:
            self._enviar_error(500, str(e))
    
    def _obtener_pedidos_pendientes(self):
        """GET /api/pedidos/pendientes"""
        if self.pedidos_web:
            pedidos = self.pedidos_web.obtener_pedidos_pendientes()
            self._enviar_respuesta(200, {"pedidos": pedidos, "total": len(pedidos)})
        else:
            self._enviar_respuesta(200, {"pedidos": [], "total": 0})
    
    def _validar_stock(self, datos):
        """POST /api/validar-stock"""
        try:
            items = datos.get("items", [])
            resultado = {"valido": True, "items_validados": [], "items_invalidos": []}
            
            if not self.inventario:
                for item in items:
                    resultado["items_validados"].append({
                        "nombre": item.get("nombre", "N/A"),
                        "cantidad": item.get("cantidad", 1),
                        "precio": 0,
                        "subtotal": 0
                    })
                self._enviar_respuesta(200, resultado)
                return
            
            for item in items:
                nombre = item.get("nombre")
                cantidad = item.get("cantidad", 0)
                producto = self.inventario.obtener_producto(nombre)
                
                if not producto:
                    resultado["valido"] = False
                    resultado["items_invalidos"].append({"nombre": nombre, "razon": "No encontrado"})
                elif producto.get("cantidad", 0) < cantidad:
                    resultado["valido"] = False
                    resultado["items_invalidos"].append({
                        "nombre": nombre,
                        "razon": f"Stock insuficiente (disponible: {producto['cantidad']})"
                    })
                else:
                    precio = producto.get("precio", 0)
                    resultado["items_validados"].append({
                        "nombre": nombre,
                        "cantidad": cantidad,
                        "precio": precio,
                        "subtotal": precio * cantidad
                    })
            
            if resultado["valido"]:
                resultado["total"] = sum(i["subtotal"] for i in resultado["items_validados"])
            
            self._enviar_respuesta(200, resultado)
        except Exception as e:
            self._enviar_error(500, str(e))
    
    def _crear_pedido(self, datos):
        """POST /api/pedido - Crea un pedido y lo envía al sistema"""
        try:
            items = datos.get("items", [])
            
            if not items:
                self._enviar_error(400, "El pedido debe tener items")
                return
            
            # Validar campos requeridos
            campos_requeridos = ["cliente", "telefono", "direccion"]
            for campo in campos_requeridos:
                if campo not in datos:
                    self._enviar_error(400, f"Campo requerido: {campo}")
                    return
            
            # Si hay sistema de pedidos_web, usarlo
            if self.pedidos_web:
                # Validar stock primero
                for item in items:
                    nombre = item.get("nombre")
                    cantidad = item.get("cantidad", 0)
                    
                    if self.inventario:
                        if not self.inventario.verificar_disponibilidad(nombre, cantidad):
                            self._enviar_error(400, f"Stock insuficiente para {nombre}")
                            return
                
                # Procesar pedido con el sistema existente
                pedido = self.pedidos_web.procesar_pedido(datos)
                
                # Notificar a la aplicación principal
                if self.app_principal:
                    self.app_principal.actualizar_pedidos_display()
                
                self._enviar_respuesta(201, {
                    "exito": True,
                    "mensaje": "Pedido creado correctamente",
                    "pedido_id": pedido["id"],
                    "total": pedido["total"],
                    "tiempo_estimado": "30-45 minutos"
                })
            else:
                # Si no hay pedidos_web, crear pedido básico y guardar
                pedido_id = str(uuid.uuid4())
                total = 0
                
                for item in items:
                    nombre = item.get("nombre")
                    cantidad = item.get("cantidad", 0)
                    
                    if self.inventario:
                        producto = self.inventario.obtener_producto(nombre)
                        if producto:
                            precio = producto.get("precio", 0)
                            total += precio * cantidad
                            # Restar del inventario
                            self.inventario.quitar_producto(nombre, cantidad)
                            
                            # Registrar consumo
                            if self.registro:
                                self.registro.registrar_consumo(
                                    "web",
                                    nombre,
                                    cantidad,
                                    precio,
                                    "pedido_web"
                                )
                
                # Guardar pedido en archivo
                pedido = {
                    "id": pedido_id,
                    "cliente": datos.get("cliente", "N/A"),
                    "telefono": datos.get("telefono", "N/A"),
                    "direccion": datos.get("direccion", "N/A"),
                    "notas": datos.get("notas", ""),
                    "items": items,
                    "total": total,
                    "estado": "pendiente",
                    "hora": datetime.now().strftime("%H:%M"),
                    "fecha": datetime.now().strftime("%Y-%m-%d")
                }
                
                self._guardar_pedido(pedido)
                
                # Actualizar UI
                if self.app_principal:
                    self.app_principal.actualizar_inventario_display()
                
                self._enviar_respuesta(201, {
                    "exito": True,
                    "mensaje": "Pedido creado correctamente",
                    "pedido_id": pedido_id,
                    "total": total,
                    "tiempo_estimado": "30-45 minutos"
                })
            
        except Exception as e:
            print(f"❌ Error creando pedido: {e}")
            traceback.print_exc()
            self._enviar_error(500, str(e))
    
    def _guardar_pedido(self, pedido):
        """Guardar pedido en archivo JSON"""
        try:
            try:
                with open("pedidos_web.json", "r", encoding="utf-8") as f:
                    pedidos = json.load(f)
            except:
                pedidos = {"pendientes": [], "completados": []}
            
            if "pendientes" not in pedidos:
                pedidos["pendientes"] = []
            
            pedidos["pendientes"].append(pedido)
            
            with open("pedidos_web.json", "w", encoding="utf-8") as f:
                json.dump(pedidos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error guardando pedido: {e}")
    
    def log_message(self, format, *args):
        """Reducir logs en consola"""
        pass


class ServidorAPI:
    """Servidor HTTP para la API REST"""
    
    def __init__(self, puerto=8081, inventario=None, registro=None, app=None, pedidos_web=None):
        self.puerto = puerto
        self.servidor = None
        
        ManejadorAPI.inventario = inventario
        ManejadorAPI.registro = registro
        ManejadorAPI.app_principal = app
        ManejadorAPI.pedidos_web = pedidos_web
    
    def iniciar(self):
        """Iniciar el servidor API"""
        try:
            self.servidor = HTTPServer(('0.0.0.0', self.puerto), ManejadorAPI)
            print(f"""
╔══════════════════════════════════════════════════════════╗
║     🚀 API REST INICIADA CORRECTAMENTE                   ║
╠══════════════════════════════════════════════════════════╣
║  📡 URL: http://localhost:{self.puerto}                          ║
║  ✅ CORS: Habilitado para todos los orígenes             ║
║  📋 Endpoints:                                           ║
║     GET  /api/productos                                  ║
║     GET  /api/categorias                                 ║
║     GET  /api/estadisticas                               ║
║     GET  /api/pedidos/pendientes                         ║
║     POST /api/validar-stock                              ║
║     POST /api/pedido                                     ║
╚══════════════════════════════════════════════════════════╝
            """)
            self.servidor.serve_forever()
        except Exception as e:
            print(f"❌ Error iniciando API: {e}")
    
    def detener(self):
        """Detener el servidor API"""
        if self.servidor:
            self.servidor.shutdown()
            self.servidor.server_close()
            print("🛑 API REST detenida")