import sys
import json
import os
import shutil
from datetime import datetime, timedelta
import threading
from api_rest import ServidorAPI
import webbrowser

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from datetime import datetime
from materia_prima import MateriaPrima
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QComboBox, QCheckBox, QTextEdit, QMessageBox,
    QMenu, QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QListWidget,
    QListWidgetItem, QStatusBar, QFrame, QGroupBox, QHeaderView,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFileDialog, QAbstractItemView
)
from PySide6.QtGui import QAction, QFont, QIcon

from inventario import Inventario
from pedidos_web import ServidorPedidos
from impresora import ImpresoraRecibos
from autenticacion import Autenticacion
from registro_actividades import RegistroActividades


class VentanaLogin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - Sistema de Comidas Rápidas")
        self.setFixedSize(400, 300)
        
        self.auth = Autenticacion()
        self.crear_interfaz()
        
        # Centrar ventana
        self.move(QApplication.primaryScreen().geometry().center() - self.rect().center())
    
    def crear_interfaz(self):
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        widget_central.setLayout(layout)
        
        # Título
        titulo = QLabel("🍔 Comidas Rápidas")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)
        layout.addSpacing(20)

        subtitulo = QLabel("Inicio de Sesión")
        subtitulo.setFont(QFont("Arial", 12))
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitulo)
        layout.addSpacing(20)

        # Formulario login
        form_layout = QFormLayout()

        self.entry_usuario = QLineEdit()
        self.entry_usuario.setMinimumWidth(200)
        form_layout.addRow("Usuario:", self.entry_usuario)

        self.entry_password = QLineEdit()
        self.entry_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry_password.returnPressed.connect(self.login)
        form_layout.addRow("Contraseña:", self.entry_password)

        layout.addLayout(form_layout)
        layout.addSpacing(10)

        # Botón login
        btn_login = QPushButton("Iniciar Sesión")
        btn_login.clicked.connect(self.login)
        layout.addWidget(btn_login)

        # Label error
        self.label_error = QLabel("")
        self.label_error.setStyleSheet("color: red;")
        self.label_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_error)
        
        layout.addSpacing(20)
        
        # Info usuarios
        info_group = QGroupBox("Usuarios por defecto")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel("Admin: admin / admin123"))
        info_layout.addWidget(QLabel("Usuario: usuario / usuario123"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
    def login(self):
        usuario = self.entry_usuario.text()
        password = self.entry_password.text()
        
        if not usuario or not password:
            self.label_error.setText("Complete todos los campos")
            return
            
        if self.auth.login(usuario, password):
            self.app_principal = AplicacionComidasRapidas(self.auth)
            self.app_principal.show()
            self.close()
        else:
            self.label_error.setText("Usuario o contraseña incorrectos")


class AplicacionComidasRapidas(QMainWindow):
    def __init__(self, auth):
        from api_rest import ServidorAPI
        super().__init__()
        self.auth = auth
        self.setWindowTitle(f"Sistema de Gestión - Comidas Rápidas - Usuario: {auth.usuario_actual}")
        self.resize(1400, 900)
        
        self.inventario = Inventario()
        self.impresora = ImpresoraRecibos()
        self.registro = RegistroActividades()
        self.servidor_pedidos = None
        self.servidor_api = None
        self.pedido_actual = None
        self.categorias = self.cargar_categorias()
        self.categorias_materia = self.cargar_categorias_materia_prima()
        self.gestor_pedidos = ServidorPedidos(self.inventario, self)
        
        self.crear_interfaz()
        self.crear_menu_superior()
        self.aplicar_permisos()
        self.iniciar_api()
        
        # Centrar ventana
        self.move(QApplication.primaryScreen().geometry().center() - self.rect().center())
        self.cargar_configuracion_impresora()

    # ========== MÉTODOS DE CATEGORÍAS DE MATERIA PRIMA ==========
    
    def cargar_categorias_materia_prima(self):
        """Cargar categorías de materia prima"""
        try:
            with open("categorias_materia.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return ["Carnes", "Lácteos", "Harinas", "Verduras", "Salsas", "Bebidas", "Especias"]

    def obtener_url_ngrok(self):
        """Obtener la URL pública de ngrok (si está activo)"""
        try:
            import urllib.request
            import json
            
            # ngrok expone una API local en el puerto 4040
            req = urllib.request.Request("http://localhost:4040/api/tunnels")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                tunnels = data.get("tunnels", [])
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        return tunnel.get("public_url", "")
        except:
            return None
        return None

    def actualizar_script_js_automatico(self):
        """Actualizar automáticamente el archivo script.js con la URL de ngrok"""
        url_ngrok = self.obtener_url_ngrok()
        
        if not url_ngrok:
            QMessageBox.warning(self, "⚠️ ngrok no detectado", 
                "No se detectó ngrok ejecutándose.\n\n"
                "Asegúrate de:\n"
                "1. Hacer clic en 'Iniciar ngrok' o ejecutar 'ngrok http 8081'\n"
                "2. Esperar unos segundos\n"
                "3. Intentar de nuevo")
            return
        
        # Buscar el archivo script.js
        archivos_posibles = [
            "script.js",
            "js/script.js",
            "../script.js",
            "web/script.js",
            "pagina_web/script.js"
        ]
        
        archivo_encontrado = None
        for archivo in archivos_posibles:
            if os.path.exists(archivo):
                archivo_encontrado = archivo
                break
        
        # Si no se encuentra, pedir al usuario que lo seleccione
        if not archivo_encontrado:
            QMessageBox.information(self, "Seleccionar archivo", 
                "Selecciona el archivo script.js de tu página web")
            
            archivo_encontrado, _ = QFileDialog.getOpenFileName(
                self, 
                "Seleccionar archivo script.js", 
                "", 
                "JavaScript Files (*.js);;All Files (*.*)"
            )
            
            if not archivo_encontrado:
                return
        
        try:
            # Leer el contenido actual
            with open(archivo_encontrado, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Hacer backup del archivo original
            backup_path = archivo_encontrado + ".backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            # Buscar y reemplazar la línea de API_URL
            import re
            
            # Patrón para encontrar const API_URL = '...';
            patron = r"(const\s+API_URL\s*=\s*['\"])[^'\"]*(['\"])"
            
            nueva_linea = f"const API_URL = '{url_ngrok}/api';"
            
            if re.search(patron, contenido):
                # Reemplazar la URL existente
                nuevo_contenido = re.sub(patron, rf"\1{url_ngrok}/api\2", contenido)
            else:
                # Si no existe API_URL, agregarla al inicio del archivo
                nuevo_contenido = f"// API URL actualizada automáticamente\n{nueva_linea}\n\n{contenido}"
            
            # Guardar el archivo actualizado
            with open(archivo_encontrado, 'w', encoding='utf-8') as f:
                f.write(nuevo_contenido)
            
            # Mostrar mensaje de éxito
            QMessageBox.information(self, "✅ Éxito", 
                f"Archivo script.js actualizado correctamente!\n\n"
                f"📍 Ruta: {archivo_encontrado}\n"
                f"🌐 Nueva URL: {url_ngrok}/api\n\n"
                f"💾 Backup guardado en: {backup_path}\n\n"
                f"🔄 Recarga tu página web para aplicar los cambios.")
            
            # Registrar actividad
            if hasattr(self, 'registro'):
                self.registro.registrar_actividad(
                    self.auth.usuario_actual,
                    "actualizar_script_js",
                    {"url": f"{url_ngrok}/api", "archivo": archivo_encontrado}
                )
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", 
                f"Error al actualizar el archivo:\n\n{str(e)}")


    def actualizar_script_con_confirmacion(self):
        """Actualizar script.js con confirmación previa"""
        url_ngrok = self.obtener_url_ngrok()
        
        if not url_ngrok:
            QMessageBox.warning(self, "⚠️ ngrok no detectado", 
                "No se detectó ngrok ejecutándose.")
            return
        
        reply = QMessageBox.question(self, "Confirmar actualización",
            f"¿Actualizar automáticamente el archivo script.js?\n\n"
            f"🌐 Nueva URL: {url_ngrok}/api\n\n"
            f"Se creará un backup automático del archivo original.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.actualizar_script_js_automatico()


    def restaurar_backup_script(self):
        """Restaurar el backup del archivo script.js"""
        archivos_posibles = [
            "script.js.backup",
            "js/script.js.backup",
            "../script.js.backup",
            "web/script.js.backup"
        ]
        
        archivo_encontrado = None
        for archivo in archivos_posibles:
            if os.path.exists(archivo):
                archivo_encontrado = archivo
                break
        
        if not archivo_encontrado:
            reply = QMessageBox.question(self, "Buscar backup",
                "No se encontró un backup automático.\n\n"
                "¿Deseas seleccionar manualmente un archivo de backup?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                archivo_encontrado, _ = QFileDialog.getOpenFileName(
                    self, 
                    "Seleccionar archivo de backup", 
                    "", 
                    "Backup Files (*.backup);;All Files (*.*)"
                )
            
            if not archivo_encontrado:
                return
        
        try:
            # Determinar el archivo original
            archivo_original = archivo_encontrado.replace(".backup", "")
            
            # Verificar que existe el archivo original
            if not os.path.exists(archivo_original):
                # Preguntar dónde guardar
                archivo_original, _ = QFileDialog.getSaveFileName(
                    self,
                    "Guardar archivo restaurado como",
                    "script.js",
                    "JavaScript Files (*.js)"
                )
                if not archivo_original:
                    return
            
            # Copiar el backup al original
            with open(archivo_encontrado, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            with open(archivo_original, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            QMessageBox.information(self, "✅ Restaurado", 
                f"Archivo restaurado correctamente!\n\n"
                f"📍 Ruta: {archivo_original}")
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", 
                f"Error al restaurar el backup:\n\n{str(e)}")

    def copiar_url_pagina_web(self):
        """Copiar la URL pública de la página web al portapapeles"""
        url_ngrok = self.obtener_url_ngrok()
        
        if url_ngrok:
            QApplication.clipboard().setText(url_ngrok)
            QMessageBox.information(self, "✅ URL Copiada", 
                f"URL de la página web copiada al portapapeles:\n\n"
                f"{url_ngrok}\n\n"
                f"📱 Comparte este enlace con tus clientes para que puedan:\n"
                f"• Ver el menú\n"
                f"• Hacer pedidos en línea\n"
                f"• Consultar precios")
        else:
            QMessageBox.warning(self, "⚠️ ngrok no detectado", 
                "No se detectó ngrok ejecutándose.\n\n"
                "Haz clic en 'Iniciar ngrok' para publicar tu página web.")
        
    def actualizar_info_api(self):
        """Actualizar información de la API y página web en la interfaz"""
        url_ngrok = self.obtener_url_ngrok()
        ngrok_activo = self.verificar_estado_ngrok()

        texto = "📡 ESTADO DEL SERVIDOR\n"
        texto += "=" * 40 + "\n\n"
        texto += "✅ API REST activa en:\n"
        texto += f"   • Local: http://localhost:8081\n"
        texto += f"   • Web local: http://localhost:8081\n"

        if url_ngrok and ngrok_activo:
            texto += f"\n🌐 SERVIDOR PÚBLICO ACTIVO\n"
            texto += f"   • Página web: {url_ngrok}\n"
            texto += f"   • API REST: {url_ngrok}/api\n\n"
            texto += "📱 COMPARTE ESTA URL CON TUS CLIENTES:\n"
            texto += f"   {url_ngrok}\n\n"
            texto += "📡 Endpoints disponibles:\n"
            texto += f"   • GET  {url_ngrok}/api/productos\n"
            texto += f"   • GET  {url_ngrok}/api/categorias\n"
            texto += f"   • POST {url_ngrok}/api/pedido\n"
            texto += f"   • POST {url_ngrok}/api/validar-stock\n\n"
            texto += "🔒 CORS: Habilitado para todos los orígenes\n\n"
            texto += "⚡ Estado ngrok: 🟢 CONECTADO\n"
            texto += "🌍 Tu página web está disponible públicamente"

            self.url_ngrok_actual = url_ngrok
        elif ngrok_activo and not url_ngrok:
            texto += "\n📡 ngrok está iniciando...\n"
            texto += "⚡ Estado ngrok: 🟡 INICIANDO (espera unos segundos)"
        else:
            texto += "\n📡 Endpoints disponibles:\n"
            texto += "   • GET  /api/productos\n"
            texto += "   • GET  /api/categorias\n"
            texto += "   • POST /api/pedido\n"
            texto += "   • POST /api/validar-stock\n\n"
            texto += "🔒 CORS: Habilitado para todos los orígenes\n\n"
            texto += "⚡ Estado ngrok: 🔴 DESCONECTADO\n"
            texto += "💡 Haz clic en 'Iniciar ngrok' para publicar tu página web"

            self.url_ngrok_actual = None

        if hasattr(self, 'text_info_api'):
            self.text_info_api.setText(texto)

        # Actualizar texto del botón toggle
        if hasattr(self, 'btn_toggle_ngrok'):
            if ngrok_activo:
                self.btn_toggle_ngrok.setText("🛑 Detener ngrok")
                self.btn_toggle_ngrok.setStyleSheet("""
                    QPushButton {
                        background-color: #ff4757;
                        color: white;
                        font-weight: bold;
                        padding: 8px;
                    }
                    QPushButton:hover {
                        background-color: #ff2e4c;
                    }
                """)
            else:
                self.btn_toggle_ngrok.setText("🚀 Iniciar ngrok (Publicar página web)")
                self.btn_toggle_ngrok.setStyleSheet("""
                    QPushButton {
                        background-color: #1e90ff;
                        color: white;
                        font-weight: bold;
                        padding: 8px;
                    }
                    QPushButton:hover {
                        background-color: #0066cc;
                    }
                """)

    def copiar_url_ngrok(self):
        """Copiar la URL pública de ngrok al portapapeles"""
        url_ngrok = self.obtener_url_ngrok()
        
        if url_ngrok:
            QApplication.clipboard().setText(url_ngrok)
            QMessageBox.information(self, "✅ URL Copiada", 
                f"URL pública de ngrok copiada al portapapeles:\n\n{url_ngrok}\n\n"
                "Pégala en tu archivo script.js como API_URL")
        else:
            QMessageBox.warning(self, "⚠️ ngrok no detectado", 
                "No se detectó ngrok ejecutándose.\n\n"
                "Asegúrate de:\n"
                "1. Tener ngrok instalado\n"
                "2. Ejecutar en una terminal: ngrok http 8081\n"
                "3. Presionar 'Refrescar' para intentar de nuevo")


    def copiar_url_local(self):
        """Copiar la URL local al portapapeles"""
        QApplication.clipboard().setText("http://localhost:8081/api")
        QMessageBox.information(self, "✅ URL Copiada", 
            "URL local copiada al portapapeles:\n\n"
            "http://localhost:8081/api")


    def copiar_ejemplo_fetch(self):
        """Copiar ejemplo de código fetch para la API"""
        url_ngrok = self.obtener_url_ngrok()
        url_base = url_ngrok if url_ngrok else "http://localhost:8081"
        
        codigo = f'''// API URL - Actualizado automáticamente
    const API_URL = '{url_base}/api';

    // Obtener productos
    async function cargarProductos() {{
        try {{
            const response = await fetch(`${{API_URL}}/productos`);
            const data = await response.json();
            console.log('Productos:', data.productos);
            return data.productos;
        }} catch (error) {{
            console.error('Error:', error);
        }}
    }}

    // Crear pedido
    async function crearPedido(pedido) {{
        try {{
            const response = await fetch(`${{API_URL}}/pedido`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(pedido)
            }});
            const data = await response.json();
            console.log('Pedido creado:', data);
            return data;
        }} catch (error) {{
            console.error('Error:', error);
        }}
    }}

    // Validar stock
    async function validarStock(items) {{
        try {{
            const response = await fetch(`${{API_URL}}/validar-stock`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ items }})
            }});
            const data = await response.json();
            return data;
        }} catch (error) {{
            console.error('Error:', error);
        }}
    }}

    // Ejemplo de uso:
    // cargarProductos().then(p => console.log(p));
    // crearPedido({{
    //     cliente: "Juan Pérez",
    //     telefono: "123456789",
    //     direccion: "Calle 123",
    //     items: [{{ nombre: "Hamburguesa", cantidad: 2 }}]
    // }});'''

        QApplication.clipboard().setText(codigo)
        QMessageBox.information(self, "✅ Código Copiado", 
            "Ejemplo completo de código fetch copiado al portapapeles.\n\n"
            "Pégalo en tu archivo script.js para comenzar.")


    def iniciar_ngrok_automatico(self):
        """Iniciar ngrok y publicar automáticamente la página web"""
        import subprocess
        import threading
        import shutil

        # Verificar si ngrok está instalado
        if shutil.which("ngrok") is None:
            reply = QMessageBox.question(self, "ngrok no encontrado",
                "ngrok no está instalado o no está en el PATH.\n\n"
                "¿Deseas abrir la página de descarga de ngrok?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                import webbrowser
                webbrowser.open("https://ngrok.com/download")
            return

        # Verificar si ya está corriendo
        if self.obtener_url_ngrok():
            url = self.obtener_url_ngrok()
            QMessageBox.information(self, "ngrok ya activo",
                f"ngrok ya está ejecutándose.\n\n"
                f"🌐 URL Pública: {url}\n\n"
                f"📱 Página web: {url}\n"
                f"🔌 API REST: {url}/api\n\n"
                f"¿Deseas abrir la página web en el navegador?")
            
            # Preguntar si quiere abrir la página web
            reply = QMessageBox.question(self, "Abrir página web",
                "¿Deseas abrir la página web pública en tu navegador?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                webbrowser.open(url)
            
            self.actualizar_info_api()
            return

        # Iniciar ngrok en segundo plano
        def run_ngrok():
            try:
                if sys.platform == "win32":
                    subprocess.Popen(["ngrok", "http", "8081"], 
                                creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen(["ngrok", "http", "8081"], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error iniciando ngrok: {e}")

        threading.Thread(target=run_ngrok, daemon=True).start()

        # Mostrar mensaje de inicio
        msg = QMessageBox(self)
        msg.setWindowTitle("🚀 Iniciando ngrok")
        msg.setText("ngrok se está iniciando en segundo plano...\n\n"
                    "⏳ Espera unos segundos mientras se establece la conexión.\n\n"
                    "Cuando esté listo, podrás:\n"
                    "• Compartir la URL pública con tus clientes\n"
                    "• Abrir la página web automáticamente\n"
                    "• Ver el estado en la pestaña Configuración")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.show()

        # Programar verificación después de 5 segundos
        QTimer.singleShot(5000, self.verificar_y_abrir_ngrok)

    def verificar_y_abrir_ngrok(self):
        """Verificar si ngrok ya está listo y abrir la página web"""
        import webbrowser  # Por si acaso no está en los imports globales
        
        url = self.obtener_url_ngrok()
        
        if url:
            # Actualizar info en la interfaz
            self.actualizar_info_api()
            
            # Mostrar mensaje de éxito con opción de abrir página web
            reply = QMessageBox.question(self, "✅ ngrok listo",
                f"¡Conexión establecida exitosamente!\n\n"
                f"🌐 URL Pública: {url}\n\n"
                f"📱 Tus clientes pueden acceder a la página web en:\n"
                f"{url}\n\n"
                f"🔌 API REST disponible en:\n"
                f"{url}/api\n\n"
                f"¿Deseas abrir la página web en tu navegador ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                webbrowser.open(url)  # ← Ahora funcionará correctamente
            
            # Actualizar script.js automáticamente si existe
            self.actualizar_script_js_automatico()
        else:
            # Si aún no está listo, programar otra verificación
            QTimer.singleShot(3000, self.verificar_y_abrir_ngrok)
            
    def guardar_categorias_materia_prima(self, categorias):
        """Guardar categorías de materia prima"""
        with open("categorias_materia.json", "w", encoding="utf-8") as f:
            json.dump(categorias, f, indent=2, ensure_ascii=False)

    def actualizar_lista_categorias_materia(self):
        """Actualizar lista de categorías de materia prima"""
        if not hasattr(self, 'lista_categorias_materia'):
            return
        
        if not hasattr(self, 'categorias_materia'):
            self.categorias_materia = self.cargar_categorias_materia_prima()
        
        self.lista_categorias_materia.clear()
        for categoria in sorted(self.categorias_materia):
            self.lista_categorias_materia.addItem(categoria)
        
        if hasattr(self, 'actualizar_stats_categorias_materia'):
            self.actualizar_stats_categorias_materia()

    def agregar_categoria_materia(self):
        """Agregar nueva categoría de materia prima"""
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para agregar categorías")
            return
        
        if not hasattr(self, 'categorias_materia'):
            self.categorias_materia = self.cargar_categorias_materia_prima()
            
        nueva_categoria = self.entry_nueva_categoria_materia.text().strip()
        
        if not nueva_categoria:
            QMessageBox.critical(self, "Error", "Ingrese un nombre para la categoría")
            return
            
        if nueva_categoria in self.categorias_materia:
            QMessageBox.critical(self, "Error", "Esta categoría ya existe")
            return
            
        self.registro.registrar_actividad(
            self.auth.usuario_actual,
            "agregar_categoria_materia",
            {"categoria": nueva_categoria},
        )
        
        self.categorias_materia.append(nueva_categoria)
        self.guardar_categorias_materia_prima(self.categorias_materia)
        self.actualizar_lista_categorias_materia()
        self.entry_nueva_categoria_materia.clear()
        QMessageBox.information(self, "Éxito", f"Categoría '{nueva_categoria}' agregada a ingredientes")

    def renombrar_categoria_materia(self):
        """Renombrar categoría de materia prima"""
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para modificar categorías")
            return
            
        item = self.lista_categorias_materia.currentItem()
        if not item:
            QMessageBox.warning(self, "Advertencia", "Seleccione una categoría")
            return
            
        categoria_actual = item.text()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Renombrar Categoría de Ingredientes")
        dialog.setFixedSize(350, 120)
        
        layout = QFormLayout(dialog)
        entry_nuevo = QLineEdit()
        entry_nuevo.setPlaceholderText("Nuevo nombre para la categoría")
        layout.addRow(f"Renombrar '{categoria_actual}':", entry_nuevo)
        
        buttons = QHBoxLayout()
        btn_ok = QPushButton("✅ Renombrar")
        btn_cancelar = QPushButton("❌ Cancelar")
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancelar)
        layout.addRow(buttons)
        
        def aceptar():
            nuevo_nombre = entry_nuevo.text().strip()
            if not nuevo_nombre:
                QMessageBox.critical(dialog, "Error", "Ingrese un nombre válido")
                return
                
            if nuevo_nombre in self.categorias_materia:
                QMessageBox.critical(dialog, "Error", "Ya existe una categoría con ese nombre")
                return
                
            self.registro.registrar_actividad(
                self.auth.usuario_actual,
                "renombrar_categoria_materia",
                {"categoria_original": categoria_actual, "categoria_nueva": nuevo_nombre},
            )
            
            # Actualizar ingredientes con esta categoría
            if hasattr(self, 'materia_prima'):
                for nombre, datos in self.materia_prima.materia_prima.items():
                    if datos.get('categoria') == categoria_actual:
                        datos['categoria'] = nuevo_nombre
                self.materia_prima.guardar_datos()
            
            # Actualizar lista
            index = self.categorias_materia.index(categoria_actual)
            self.categorias_materia[index] = nuevo_nombre
            self.guardar_categorias_materia_prima(self.categorias_materia)
            self.actualizar_lista_categorias_materia()
            
            # Actualizar tabla de ingredientes si está visible
            if hasattr(self, 'actualizar_tabla_ingredientes'):
                self.actualizar_tabla_ingredientes()
            
            dialog.accept()
            QMessageBox.information(self, "Éxito", f"Categoría renombrada a '{nuevo_nombre}'")
        
        btn_ok.clicked.connect(aceptar)
        btn_cancelar.clicked.connect(dialog.reject)
        dialog.exec()

    def eliminar_categoria_materia(self):
        """Eliminar categoría de materia prima"""
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para eliminar categorías")
            return
            
        item = self.lista_categorias_materia.currentItem()
        if not item:
            QMessageBox.warning(self, "Advertencia", "Seleccione una categoría")
            return
            
        categoria = item.text()
        
        # Contar ingredientes en esta categoría
        ingredientes_en_categoria = 0
        if hasattr(self, 'materia_prima'):
            for datos in self.materia_prima.materia_prima.values():
                if datos.get('categoria') == categoria:
                    ingredientes_en_categoria += 1
        
        mensaje = f"¿Eliminar categoría '{categoria}'?"
        if ingredientes_en_categoria > 0:
            mensaje += f"\n\n⚠️ Hay {ingredientes_en_categoria} ingredientes en esta categoría."
            
        reply = QMessageBox.question(self, "Confirmar", mensaje,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if reply == QMessageBox.StandardButton.Yes:
            self.registro.registrar_actividad(
                self.auth.usuario_actual, 
                "eliminar_categoria_materia", 
                {"categoria": categoria}
            )
            
            # Eliminar categoría de ingredientes
            if hasattr(self, 'materia_prima'):
                for nombre, datos in self.materia_prima.materia_prima.items():
                    if datos.get('categoria') == categoria:
                        datos['categoria'] = "Sin categoría"
                self.materia_prima.guardar_datos()
            
            self.categorias_materia.remove(categoria)
            self.guardar_categorias_materia_prima(self.categorias_materia)
            self.actualizar_lista_categorias_materia()
            
            if hasattr(self, 'actualizar_tabla_ingredientes'):
                self.actualizar_tabla_ingredientes()
            
            QMessageBox.information(self, "Éxito", "Categoría eliminada")

    def actualizar_stats_categorias_materia(self):
        """Actualizar estadísticas de ingredientes por categoría"""
        if not hasattr(self, 'text_stats_categorias_materia'):
            return
            
        self.text_stats_categorias_materia.clear()
        
        if not hasattr(self, 'materia_prima'):
            self.text_stats_categorias_materia.append("No hay datos de materia prima disponibles")
            return
        
        if not hasattr(self, 'categorias_materia'):
            self.categorias_materia = self.cargar_categorias_materia_prima()
        
        # Agrupar por categoría
        stats = {}
        for nombre, datos in self.materia_prima.materia_prima.items():
            if not isinstance(datos, dict):
                continue
                
            cat = datos.get('categoria', 'Sin categoría')
            if cat not in stats:
                stats[cat] = {'cantidad': 0, 'valor': 0, 'ingredientes': 0}
            
            stock = datos.get('stock', 0)
            costo = datos.get('costo_unitario', 0)
            
            stats[cat]['ingredientes'] += 1
            stats[cat]['cantidad'] += stock
            stats[cat]['valor'] += stock * costo
        
        if not stats:
            self.text_stats_categorias_materia.append("No hay ingredientes registrados")
            return
        
        for categoria in sorted(self.categorias_materia):
            if categoria in stats:
                s = stats[categoria]
                self.text_stats_categorias_materia.append(f"📁 {categoria}:")
                self.text_stats_categorias_materia.append(f"   • Ingredientes: {s['ingredientes']}")
                self.text_stats_categorias_materia.append(f"   • Stock total: {s['cantidad']:,.2f}".replace(",", "."))
                self.text_stats_categorias_materia.append(f"   • Valor: ${s['valor']:,.2f}".replace(",", "."))
                self.text_stats_categorias_materia.append("")

    # ========== MÉTODOS DE API Y CONFIGURACIÓN ==========
    
    def iniciar_api(self):
        """Iniciar servidor API REST"""
        try:
            from api_rest import ServidorAPI
            
            self.servidor_api = ServidorAPI(
                puerto=8081,
                inventario=self.inventario,
                registro=self.registro,
                app=self,
                pedidos_web=self.gestor_pedidos
            )
            
            api_thread = threading.Thread(target=self.servidor_api.iniciar, daemon=True)
            api_thread.start()
            
            print("✅ API iniciada en http://localhost:8081")
            self.status_bar.showMessage("API REST activa en puerto 8081")
            
        except Exception as e:
            print(f"❌ Error iniciando API: {e}")

    def detener_servidor_api(self):
        """Detener servidor API REST"""
        if self.servidor_api:
            self.servidor_api.detener()
            self.servidor_api = None

    def cargar_configuracion_impresora(self):
        """Cargar configuración de impresora desde archivo"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                if "impresora" in config and hasattr(self, 'entry_impresora'):
                    self.entry_impresora.setText(config["impresora"])
                    print(f"✅ Configuración de impresora cargada: {config['impresora']}")
        except FileNotFoundError:
            print("ℹ️ No se encontró archivo config.json, usando valores por defecto")
        except Exception as e:
            print(f"⚠️ Error al cargar configuración: {e}")

    def guardar_configuracion_impresora(self):
        """Guardar la configuración de la impresora"""
        try:
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                config = {}
            
            config["impresora"] = self.entry_impresora.text().strip() or "POS-80"
            
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Éxito", 
                f"✅ Configuración de impresora guardada:\n{self.entry_impresora.text()}")
            
            if hasattr(self, 'registro'):
                self.registro.registrar_actividad(
                    self.auth.usuario_actual,
                    "configuracion",
                    {"impresora": self.entry_impresora.text()}
                )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {str(e)}")

    def verificar_estado_api(self):
        """Verificar si la API REST está funcionando"""
        import urllib.request
        import urllib.error
        
        try:
            req = urllib.request.Request("http://localhost:8081/api", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    QMessageBox.information(self, "✅ API Activa", 
                        "La API REST está funcionando correctamente.\n\n"
                        "URL: http://localhost:8081/api\n\n"
                        "Endpoints disponibles:\n"
                        "• GET  /api/productos\n"
                        "• GET  /api/categorias\n"
                        "• POST /api/pedido")
                else:
                    QMessageBox.warning(self, "⚠️ API Inactiva", 
                        f"La API respondió con código: {response.status}")
        except urllib.error.URLError as e:
            QMessageBox.critical(self, "❌ Error de Conexión", 
                "No se pudo conectar con la API REST.\n\n"
                "Asegúrate de que:\n"
                "• La aplicación esté ejecutándose\n"
                "• El puerto 8081 no esté bloqueado\n\n"
                f"Error: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", f"Error inesperado: {str(e)}")

    def copiar_url_api(self):
        """Copiar la URL de la API al portapapeles"""
        
        clipboard = QApplication.clipboard()
        clipboard.setText("http://localhost:8081/api")
        
        QMessageBox.information(self, "📋 Copiado", 
            "URL de la API copiada al portapapeles:\n\n"
            "http://localhost:8081/api")

    def cargar_categorias(self):
        try:
            with open("categorias.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return ["Hamburguesas", "Pizzas", "Bebidas", "Postres", "Acompañantes"]
            
    def guardar_categorias(self):
        with open("categorias.json", "w", encoding="utf-8") as f:
            json.dump(self.categorias, f, indent=2, ensure_ascii=False)

    # ========== CREACIÓN DE INTERFAZ ==========
            
    def crear_interfaz(self):
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        widget_central.setLayout(layout)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        self.crear_pestana_inventario()
        self.crear_pestana_categorias()
        self.crear_pestana_materia_prima()
        self.crear_pestana_pedidos()
        self.crear_pestana_registros()
        
        if self.auth.es_admin:
            self.crear_pestana_configuracion()
            
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Servidor detenido")
        
    def crear_menu_superior(self):
        menubar = self.menuBar()
        
        archivo_menu = menubar.addMenu("Archivo")
        
        cambiar_pass_action = QAction("Cambiar Contraseña", self)
        cambiar_pass_action.triggered.connect(self.cambiar_password)
        archivo_menu.addAction(cambiar_pass_action)
        
        archivo_menu.addSeparator()
        
        cerrar_sesion_action = QAction("Cerrar Sesión", self)
        cerrar_sesion_action.triggered.connect(self.cerrar_sesion)
        archivo_menu.addAction(cerrar_sesion_action)
        
        salir_action = QAction("Salir", self)
        salir_action.triggered.connect(self.close)
        archivo_menu.addAction(salir_action)
        
        if self.auth.es_admin:
            usuarios_menu = menubar.addMenu("Usuarios")
            gestionar_action = QAction("Gestionar Usuarios", self)
            gestionar_action.triggered.connect(self.gestionar_usuarios)
            usuarios_menu.addAction(gestionar_action)
            
        reportes_menu = menubar.addMenu("Reportes")
        
        reporte_diario_action = QAction("Reporte Diario", self)
        reporte_diario_action.triggered.connect(self.generar_reporte_diario)
        reportes_menu.addAction(reporte_diario_action)
        
        reporte_semanal_action = QAction("Reporte Semanal", self)
        reporte_semanal_action.triggered.connect(self.generar_reporte_semanal)
        reportes_menu.addAction(reporte_semanal_action)
        
    def aplicar_permisos(self):
        if not self.auth.es_admin:
            self.tab_widget.setTabEnabled(1, False)
            if self.tab_widget.count() > 4:
                self.tab_widget.setTabEnabled(4, False)

    # ========== PESTAÑA INVENTARIO ==========
                
    def crear_pestana_inventario(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        ops_group = QGroupBox("Operaciones de Inventario")
        ops_layout = QVBoxLayout()
        ops_group.setLayout(ops_layout)
        
        ops_tabs = QTabWidget()
        ops_layout.addWidget(ops_tabs)
        
        # Tab Agregar Producto
        agregar_widget = QWidget()
        agregar_layout = QFormLayout()
        agregar_widget.setLayout(agregar_layout)
        
        self.entry_nombre = QLineEdit()
        agregar_layout.addRow("Nombre:", self.entry_nombre)
        
        self.combo_categoria = QComboBox()
        self.combo_categoria.addItems(self.categorias)
        agregar_layout.addRow("Categoría:", self.combo_categoria)
        
        self.entry_precio = QDoubleSpinBox()
        self.entry_precio.setRange(0, 999999)
        self.entry_precio.setPrefix("$")
        agregar_layout.addRow("Precio Unitario:", self.entry_precio)
        
        self.entry_cantidad = QSpinBox()
        self.entry_cantidad.setRange(0, 999999)
        agregar_layout.addRow("Cantidad Inicial:", self.entry_cantidad)
        
        btn_agregar = QPushButton("Agregar Producto")
        btn_agregar.clicked.connect(self.agregar_producto)
        agregar_layout.addRow(btn_agregar)
        
        ops_tabs.addTab(agregar_widget, "Agregar Producto")
        
        # Tab Ajustar Stock
        stock_widget = QWidget()
        stock_layout = QFormLayout()
        stock_widget.setLayout(stock_layout)
        
        self.combo_producto_stock = QComboBox()
        stock_layout.addRow("Producto:", self.combo_producto_stock)
        
        self.entry_cantidad_stock = QSpinBox()
        self.entry_cantidad_stock.setRange(1, 999999)
        stock_layout.addRow("Cantidad:", self.entry_cantidad_stock)
        
        stock_buttons = QHBoxLayout()
        btn_agregar_stock = QPushButton("➕ Agregar Stock")
        btn_agregar_stock.clicked.connect(self.agregar_stock)
        stock_buttons.addWidget(btn_agregar_stock)
        
        btn_restar_stock = QPushButton("➖ Restar Stock")
        btn_restar_stock.clicked.connect(self.restar_stock)
        stock_buttons.addWidget(btn_restar_stock)
        
        stock_layout.addRow(stock_buttons)
        
        ops_tabs.addTab(stock_widget, "Ajustar Stock")
        
        layout.addWidget(ops_group)
        
        # Barra de búsqueda
        busqueda_layout = QHBoxLayout()
        busqueda_layout.addWidget(QLabel("🔍 Buscar:"))
        
        self.entry_busqueda = QLineEdit()
        self.entry_busqueda.textChanged.connect(self.filtrar_inventario)
        busqueda_layout.addWidget(self.entry_busqueda)
        
        busqueda_layout.addSpacing(20)
        busqueda_layout.addWidget(QLabel("Filtrar por categoría:"))
        
        self.combo_filtro_categoria = QComboBox()
        self.combo_filtro_categoria.addItems(["Todas"] + self.categorias)
        self.combo_filtro_categoria.currentTextChanged.connect(self.filtrar_inventario)
        busqueda_layout.addWidget(self.combo_filtro_categoria)
        
        self.check_mostrar_total = QCheckBox("Mostrar valor total")
        self.check_mostrar_total.setChecked(True)
        self.check_mostrar_total.stateChanged.connect(self.actualizar_inventario_display)
        busqueda_layout.addWidget(self.check_mostrar_total)
        
        busqueda_layout.addStretch()
        layout.addLayout(busqueda_layout)
        
        # Tabla de inventario
        tabla_group = QGroupBox("Inventario Actual")
        tabla_layout = QVBoxLayout()
        tabla_group.setLayout(tabla_layout)
        
        self.tabla_inventario = QTableWidget()
        self.tabla_inventario.setColumnCount(6)
        self.tabla_inventario.setHorizontalHeaderLabels([
            "Nombre", "Categoría", "Precio Unit.", "Cantidad", "Valor Total", "Estado"
        ])
        self.tabla_inventario.horizontalHeader().setStretchLastSection(True)
        self.tabla_inventario.setAlternatingRowColors(True)
        self.tabla_inventario.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_inventario.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_inventario.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        self.tabla_inventario.doubleClicked.connect(self.modificar_producto)
        tabla_layout.addWidget(self.tabla_inventario)
        layout.addWidget(tabla_group)
        
        self.tab_widget.addTab(widget, "📦 Inventario")
        
        self.actualizar_combo_productos()
        self.actualizar_inventario_display()

    # ========== PESTAÑA CATEGORÍAS ==========
        
    def crear_pestana_categorias(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        tabs_categorias = QTabWidget()
        layout.addWidget(tabs_categorias)
        
        # ----- TAB 1: CATEGORÍAS DE INVENTARIO (PRODUCTOS) -----
        inventario_widget = QWidget()
        inventario_layout = QVBoxLayout()
        inventario_widget.setLayout(inventario_layout)
        
        agregar_inv_group = QGroupBox("➕ Agregar Categoría de Productos")
        agregar_inv_layout = QHBoxLayout()
        agregar_inv_group.setLayout(agregar_inv_layout)
        
        agregar_inv_layout.addWidget(QLabel("Nombre de la categoría:"))
        self.entry_nueva_categoria_inventario = QLineEdit()
        self.entry_nueva_categoria_inventario.setPlaceholderText("Ej: Hamburguesas, Bebidas, Postres...")
        agregar_inv_layout.addWidget(self.entry_nueva_categoria_inventario)
        
        btn_agregar_cat_inv = QPushButton("➕ Agregar Categoría")
        btn_agregar_cat_inv.clicked.connect(self.agregar_categoria_inventario)
        agregar_inv_layout.addWidget(btn_agregar_cat_inv)
        
        inventario_layout.addWidget(agregar_inv_group)
        
        lista_inv_group = QGroupBox("📦 Categorías de Productos")
        lista_inv_layout = QVBoxLayout()
        lista_inv_group.setLayout(lista_inv_layout)
        
        self.lista_categorias_inventario = QListWidget()
        self.lista_categorias_inventario.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        lista_inv_layout.addWidget(self.lista_categorias_inventario)
        
        botones_inv_layout = QHBoxLayout()
        
        btn_renombrar_inv = QPushButton("✏️ Renombrar")
        btn_renombrar_inv.clicked.connect(self.renombrar_categoria_inventario)
        botones_inv_layout.addWidget(btn_renombrar_inv)
        
        btn_eliminar_inv = QPushButton("❌ Eliminar")
        btn_eliminar_inv.clicked.connect(self.eliminar_categoria_inventario)
        botones_inv_layout.addWidget(btn_eliminar_inv)
        
        btn_actualizar_inv = QPushButton("🔄 Actualizar Lista")
        btn_actualizar_inv.clicked.connect(self.actualizar_lista_categorias_inventario)
        botones_inv_layout.addWidget(btn_actualizar_inv)
        
        botones_inv_layout.addStretch()
        lista_inv_layout.addLayout(botones_inv_layout)
        
        inventario_layout.addWidget(lista_inv_group)
        
        stats_inv_group = QGroupBox("📊 Estadísticas de Productos por Categoría")
        stats_inv_layout = QVBoxLayout()
        stats_inv_group.setLayout(stats_inv_layout)
        
        self.text_stats_categorias_inventario = QTextEdit()
        self.text_stats_categorias_inventario.setReadOnly(True)
        self.text_stats_categorias_inventario.setMaximumHeight(150)
        stats_inv_layout.addWidget(self.text_stats_categorias_inventario)
        
        inventario_layout.addWidget(stats_inv_group)
        
        tabs_categorias.addTab(inventario_widget, "📦 Productos")
        
        # ----- TAB 2: CATEGORÍAS DE MATERIA PRIMA (INGREDIENTES) -----
        materia_widget = QWidget()
        materia_layout = QVBoxLayout()
        materia_widget.setLayout(materia_layout)
        
        agregar_mat_group = QGroupBox("➕ Agregar Categoría de Ingredientes")
        agregar_mat_layout = QHBoxLayout()
        agregar_mat_group.setLayout(agregar_mat_layout)
        
        agregar_mat_layout.addWidget(QLabel("Nombre de la categoría:"))
        self.entry_nueva_categoria_materia = QLineEdit()
        self.entry_nueva_categoria_materia.setPlaceholderText("Ej: Carnes, Lácteos, Harinas, Verduras...")
        agregar_mat_layout.addWidget(self.entry_nueva_categoria_materia)
        
        btn_agregar_cat_mat = QPushButton("➕ Agregar Categoría")
        btn_agregar_cat_mat.clicked.connect(self.agregar_categoria_materia)
        agregar_mat_layout.addWidget(btn_agregar_cat_mat)
        
        materia_layout.addWidget(agregar_mat_group)
        
        lista_mat_group = QGroupBox("🥩 Categorías de Ingredientes")
        lista_mat_layout = QVBoxLayout()
        lista_mat_group.setLayout(lista_mat_layout)
        
        self.lista_categorias_materia = QListWidget()
        self.lista_categorias_materia.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        lista_mat_layout.addWidget(self.lista_categorias_materia)
        
        botones_mat_layout = QHBoxLayout()
        
        btn_renombrar_mat = QPushButton("✏️ Renombrar")
        btn_renombrar_mat.clicked.connect(self.renombrar_categoria_materia)
        botones_mat_layout.addWidget(btn_renombrar_mat)
        
        btn_eliminar_mat = QPushButton("❌ Eliminar")
        btn_eliminar_mat.clicked.connect(self.eliminar_categoria_materia)
        botones_mat_layout.addWidget(btn_eliminar_mat)
        
        btn_actualizar_mat = QPushButton("🔄 Actualizar Lista")
        btn_actualizar_mat.clicked.connect(self.actualizar_lista_categorias_materia)
        botones_mat_layout.addWidget(btn_actualizar_mat)
        
        botones_mat_layout.addStretch()
        lista_mat_layout.addLayout(botones_mat_layout)
        
        materia_layout.addWidget(lista_mat_group)
        
        stats_mat_group = QGroupBox("📊 Estadísticas de Ingredientes por Categoría")
        stats_mat_layout = QVBoxLayout()
        stats_mat_group.setLayout(stats_mat_layout)
        
        self.text_stats_categorias_materia = QTextEdit()
        self.text_stats_categorias_materia.setReadOnly(True)
        self.text_stats_categorias_materia.setMaximumHeight(150)
        stats_mat_layout.addWidget(self.text_stats_categorias_materia)
        
        materia_layout.addWidget(stats_mat_group)
        
        tabs_categorias.addTab(materia_widget, "🥩 Ingredientes")
        
        self.tab_widget.addTab(widget, "🏷️ Categorías")
        
        self.actualizar_lista_categorias_inventario()
        self.actualizar_lista_categorias_materia()

    # ========== MÉTODOS DE CATEGORÍAS DE INVENTARIO ==========

    def actualizar_lista_categorias_inventario(self):
        """Actualizar lista de categorías de productos"""
        if not hasattr(self, 'lista_categorias_inventario'):
            return
        
        self.lista_categorias_inventario.clear()
        for categoria in sorted(self.categorias):
            self.lista_categorias_inventario.addItem(categoria)
        self.actualizar_stats_categorias_inventario()

    def agregar_categoria_inventario(self):
        """Agregar nueva categoría de productos"""
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para agregar categorías")
            return
        
        if not hasattr(self, 'entry_nueva_categoria_inventario'):
            return
            
        nueva_categoria = self.entry_nueva_categoria_inventario.text().strip()
        
        if not nueva_categoria:
            QMessageBox.critical(self, "Error", "Ingrese un nombre para la categoría")
            return
            
        if nueva_categoria in self.categorias:
            QMessageBox.critical(self, "Error", "Esta categoría ya existe")
            return
        
        if hasattr(self, 'registro'):
            self.registro.registrar_actividad(
                self.auth.usuario_actual,
                "agregar_categoria_producto",
                {"categoria": nueva_categoria},
            )
        
        self.categorias.append(nueva_categoria)
        self.guardar_categorias()
        self.actualizar_lista_categorias_inventario()
        self.actualizar_combos_categorias()
        self.entry_nueva_categoria_inventario.clear()
        QMessageBox.information(self, "Éxito", f"Categoría '{nueva_categoria}' agregada a productos")

    def renombrar_categoria_inventario(self):
        """Renombrar categoría de productos"""
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para modificar categorías")
            return
        
        if not hasattr(self, 'lista_categorias_inventario'):
            return
            
        item = self.lista_categorias_inventario.currentItem()
        if not item:
            QMessageBox.warning(self, "Advertencia", "Seleccione una categoría")
            return
            
        categoria_actual = item.text()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Renombrar Categoría de Productos")
        dialog.setFixedSize(350, 120)
        
        layout = QFormLayout(dialog)
        entry_nuevo = QLineEdit()
        entry_nuevo.setPlaceholderText("Nuevo nombre para la categoría")
        layout.addRow(f"Renombrar '{categoria_actual}':", entry_nuevo)
        
        buttons = QHBoxLayout()
        btn_ok = QPushButton("✅ Renombrar")
        btn_cancelar = QPushButton("❌ Cancelar")
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancelar)
        layout.addRow(buttons)
        
        def aceptar():
            nuevo_nombre = entry_nuevo.text().strip()
            if not nuevo_nombre:
                QMessageBox.critical(dialog, "Error", "Ingrese un nombre válido")
                return
                
            if nuevo_nombre in self.categorias:
                QMessageBox.critical(dialog, "Error", "Ya existe una categoría con ese nombre")
                return
            
            if hasattr(self, 'registro'):
                self.registro.registrar_actividad(
                    self.auth.usuario_actual,
                    "renombrar_categoria_producto",
                    {"categoria_original": categoria_actual, "categoria_nueva": nuevo_nombre},
                )
            
            self.inventario.actualizar_categoria_productos(categoria_actual, nuevo_nombre)
            
            index = self.categorias.index(categoria_actual)
            self.categorias[index] = nuevo_nombre
            self.guardar_categorias()
            self.actualizar_lista_categorias_inventario()
            self.actualizar_combos_categorias()
            self.actualizar_inventario_display()
            dialog.accept()
            QMessageBox.information(self, "Éxito", f"Categoría renombrada a '{nuevo_nombre}'")
        
        btn_ok.clicked.connect(aceptar)
        btn_cancelar.clicked.connect(dialog.reject)
        dialog.exec()

    def eliminar_categoria_inventario(self):
        """Eliminar categoría de productos"""
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para eliminar categorías")
            return
        
        if not hasattr(self, 'lista_categorias_inventario'):
            return
            
        item = self.lista_categorias_inventario.currentItem()
        if not item:
            QMessageBox.warning(self, "Advertencia", "Seleccione una categoría")
            return
            
        categoria = item.text()
        
        productos_en_categoria = self.inventario.obtener_productos_por_categoria(categoria)
        
        mensaje = f"¿Eliminar categoría '{categoria}'?"
        if productos_en_categoria:
            mensaje += f"\n\n⚠️ Hay {len(productos_en_categoria)} productos en esta categoría."
            
        reply = QMessageBox.question(self, "Confirmar", mensaje,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self, 'registro'):
                self.registro.registrar_actividad(
                    self.auth.usuario_actual, 
                    "eliminar_categoria_producto", 
                    {"categoria": categoria}
                )
            
            self.inventario.eliminar_categoria_de_productos(categoria)
            
            self.categorias.remove(categoria)
            self.guardar_categorias()
            self.actualizar_lista_categorias_inventario()
            self.actualizar_combos_categorias()
            self.actualizar_inventario_display()
            QMessageBox.information(self, "Éxito", "Categoría eliminada")

    def actualizar_stats_categorias_inventario(self):
        """Actualizar estadísticas de productos por categoría"""
        if not hasattr(self, 'text_stats_categorias_inventario'):
            return
            
        self.text_stats_categorias_inventario.clear()
        stats = self.inventario.obtener_estadisticas_por_categoria()
        
        if not stats:
            self.text_stats_categorias_inventario.append("No hay productos registrados")
            return
        
        for categoria in sorted(self.categorias):
            if categoria in stats:
                s = stats[categoria]
                self.text_stats_categorias_inventario.append(f"📁 {categoria}:")
                self.text_stats_categorias_inventario.append(f"   • Productos: {s['cantidad_productos']}")
                self.text_stats_categorias_inventario.append(f"   • Unidades: {s['total_unidades']:,}".replace(",", "."))
                self.text_stats_categorias_inventario.append(f"   • Valor: ${s['valor_total']:,.2f}".replace(",", "."))
                self.text_stats_categorias_inventario.append("")

    def actualizar_combos_categorias(self):
        """Actualizar combos de categorías en la interfaz"""
        if hasattr(self, 'combo_categoria'):
            self.combo_categoria.clear()
            self.combo_categoria.addItems(sorted(self.categorias))
        
        if hasattr(self, 'combo_filtro_categoria'):
            self.combo_filtro_categoria.clear()
            self.combo_filtro_categoria.addItems(["Todas"] + sorted(self.categorias))

    # ========== MÉTODOS DE INVENTARIO ==========
    
    def actualizar_combo_productos(self):
        if hasattr(self, 'combo_producto_stock'):
            self.combo_producto_stock.clear()
            productos = self.inventario.obtener_todos_productos()
            nombres = [p["nombre"] for p in productos]
            self.combo_producto_stock.addItems(nombres)
            
    def agregar_producto(self):
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para agregar productos")
            return
            
        nombre = self.entry_nombre.text().strip()
        categoria = self.combo_categoria.currentText()
        precio = self.entry_precio.value()
        cantidad = self.entry_cantidad.value()
        
        if not nombre:
            QMessageBox.critical(self, "Error", "El nombre es requerido")
            return
            
        if precio <= 0:
            QMessageBox.critical(self, "Error", "El precio debe ser mayor a 0")
            return
            
        self.registro.registrar_cambio_inventario(
            self.auth.usuario_actual,
            "agregar_producto",
            nombre,
            0,
            cantidad,
            precio,
        )
        
        self.inventario.agregar_producto(nombre, categoria, precio, cantidad)
        self.actualizar_inventario_display()
        self.actualizar_combo_productos()
        self.entry_nombre.clear()
        self.entry_precio.setValue(0)
        self.entry_cantidad.setValue(0)
        QMessageBox.information(self, "Éxito", f"Producto '{nombre}' agregado correctamente")
        
    def agregar_stock(self):
        producto = self.combo_producto_stock.currentText()
        cantidad = self.entry_cantidad_stock.value()
        
        if not producto:
            QMessageBox.critical(self, "Error", "Seleccione un producto")
            return
            
        producto_actual = self.inventario.obtener_producto(producto)
        if not producto_actual:
            QMessageBox.critical(self, "Error", "Producto no encontrado")
            return
            
        cantidad_anterior = producto_actual["cantidad"]
        
        self.registro.registrar_cambio_inventario(
            self.auth.usuario_actual,
            "agregar_stock",
            producto,
            cantidad_anterior,
            cantidad_anterior + cantidad,
            producto_actual["precio"],
        )
        
        if self.inventario.agregar_stock(producto, cantidad):
            self.actualizar_inventario_display()
            self.entry_cantidad_stock.setValue(0)
            self.cargar_registro_hoy()
            QMessageBox.information(self, "Éxito", f"Se agregaron {cantidad} unidades a {producto}")
        else:
            QMessageBox.critical(self, "Error", "No se pudo agregar el stock")
            
    def restar_stock(self):
        producto = self.combo_producto_stock.currentText()
        cantidad = self.entry_cantidad_stock.value()
        
        if not producto:
            QMessageBox.critical(self, "Error", "Seleccione un producto")
            return
            
        producto_actual = self.inventario.obtener_producto(producto)
        if not producto_actual:
            QMessageBox.critical(self, "Error", "Producto no encontrado")
            return
            
        if cantidad > producto_actual["cantidad"]:
            QMessageBox.critical(self, "Error", f"Cantidad insuficiente. Stock actual: {producto_actual['cantidad']}")
            return
            
        self.registro.registrar_consumo(
            self.auth.usuario_actual,
            producto,
            cantidad,
            producto_actual["precio"],
            "ajuste_manual",
        )
        
        if self.inventario.quitar_producto(producto, cantidad):
            self.actualizar_inventario_display()
            self.entry_cantidad_stock.setValue(0)
            self.cargar_registro_hoy()
            QMessageBox.information(self, "Éxito", f"Se restaron {cantidad} unidades de {producto}")
        else:
            QMessageBox.critical(self, "Error", "No se pudo restar el stock")
            
    def mostrar_menu_contextual(self, pos):
        menu = QMenu()
        modificar_action = menu.addAction("✏️ Modificar Producto")
        ajustar_action = menu.addAction("📊 Ajustar Stock")
        historial_action = menu.addAction("📈 Ver Historial")
        menu.addSeparator()
        eliminar_action = menu.addAction("❌ Eliminar Producto")
        
        action = menu.exec(self.tabla_inventario.mapToGlobal(pos))
        
        if action == modificar_action:
            self.modificar_producto()
        elif action == ajustar_action:
            self.ajustar_stock()
        elif action == historial_action:
            self.ver_historial_producto()
        elif action == eliminar_action:
            self.eliminar_producto()
            
    def modificar_producto(self):
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para modificar productos")
            return
            
        fila = self.tabla_inventario.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Advertencia", "Seleccione un producto primero")
            return
            
        item = self.tabla_inventario.item(fila, 0)
        if item is None:
            QMessageBox.warning(self, "Advertencia", "No se pudo obtener el producto")
            return
            
        nombre_producto = item.text()
        producto = self.inventario.obtener_producto(nombre_producto)
        
        if not producto:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modificar Producto - {nombre_producto}")
        dialog.setFixedSize(400, 250)
        
        layout = QFormLayout(dialog)
        
        entry_nombre = QLineEdit(producto["nombre"])
        layout.addRow("Nombre:", entry_nombre)
        
        combo_categoria = QComboBox()
        combo_categoria.addItems(self.categorias)
        combo_categoria.setCurrentText(producto["categoria"])
        layout.addRow("Categoría:", combo_categoria)
        
        entry_precio = QDoubleSpinBox()
        entry_precio.setRange(0, 999999)
        entry_precio.setValue(producto["precio"])
        entry_precio.setPrefix("$")
        layout.addRow("Precio Unitario:", entry_precio)
        
        layout.addRow("Cantidad Actual:", QLabel(str(producto["cantidad"])))
        
        buttons = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancelar")
        buttons.addWidget(btn_guardar)
        buttons.addWidget(btn_cancelar)
        layout.addRow(buttons)
        
        def guardar():
            nuevo_nombre = entry_nombre.text().strip()
            nueva_categoria = combo_categoria.currentText()
            nuevo_precio = entry_precio.value()
            
            if not nuevo_nombre:
                QMessageBox.critical(dialog, "Error", "Nombre es requerido")
                return
                
            self.registro.registrar_actividad(
                self.auth.usuario_actual,
                "modificar_producto",
                {
                    "producto_original": nombre_producto,
                    "producto_nuevo": nuevo_nombre,
                    "categoria": nueva_categoria,
                    "precio": nuevo_precio,
                },
            )
            
            self.inventario.modificar_producto(
                nombre_producto, nuevo_nombre, nueva_categoria, nuevo_precio
            )
            self.actualizar_inventario_display()
            self.actualizar_combo_productos()
            dialog.accept()
            QMessageBox.information(self, "Éxito", "Producto modificado correctamente")
            
        btn_guardar.clicked.connect(guardar)
        btn_cancelar.clicked.connect(dialog.reject)
        
        dialog.exec()
        
    def ajustar_stock(self):
        fila = self.tabla_inventario.currentRow()
        if fila < 0:
            return
            
        item = self.tabla_inventario.item(fila, 0)
        if item is None:
            return
            
        nombre_producto = item.text()
        producto = self.inventario.obtener_producto(nombre_producto)
        
        if not producto:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Ajustar Stock - {nombre_producto}")
        dialog.setFixedSize(300, 180)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"Producto: {nombre_producto}"))
        layout.addWidget(QLabel(f"Stock actual: {producto['cantidad']}"))
        layout.addWidget(QLabel("Nueva cantidad:"))
        
        entry_cantidad = QSpinBox()
        entry_cantidad.setRange(0, 999999)
        entry_cantidad.setValue(producto["cantidad"])
        layout.addWidget(entry_cantidad)
        
        btn_aplicar = QPushButton("✓ Aplicar")
        layout.addWidget(btn_aplicar)
        
        def aplicar():
            nueva_cantidad = entry_cantidad.value()
            cantidad_anterior = producto["cantidad"]
            
            if nueva_cantidad < cantidad_anterior:
                self.registro.registrar_consumo(
                    self.auth.usuario_actual,
                    nombre_producto,
                    cantidad_anterior - nueva_cantidad,
                    producto["precio"],
                    "ajuste_stock",
                )
            else:
                self.registro.registrar_cambio_inventario(
                    self.auth.usuario_actual,
                    "ajustar_stock",
                    nombre_producto,
                    cantidad_anterior,
                    nueva_cantidad,
                    producto["precio"],
                )
                
            self.inventario.ajustar_stock(nombre_producto, nueva_cantidad)
            self.actualizar_inventario_display()
            self.cargar_registro_hoy()
            dialog.accept()
            QMessageBox.information(self, "Éxito", "Stock ajustado correctamente")
            
        btn_aplicar.clicked.connect(aplicar)
        dialog.exec()
        
    def ver_historial_producto(self):
        fila = self.tabla_inventario.currentRow()
        if fila < 0:
            return
            
        item = self.tabla_inventario.item(fila, 0)
        if item is None:
            return
        nombre_producto = item.text()
        historial = self.registro.obtener_historial_cambios(nombre_producto, dias=7)
        
        if not historial:
            QMessageBox.information(self, "Historial", 
                f"No hay cambios registrados para {nombre_producto} en los últimos 7 días")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Historial - {nombre_producto}")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        tabla = QTableWidget()
        tabla.setColumnCount(4)
        tabla.setHorizontalHeaderLabels(["Fecha", "Usuario", "Acción", "Detalles"])
        tabla.setRowCount(len(historial))
        
        for i, registro in enumerate(historial):
            tabla.setItem(i, 0, QTableWidgetItem(registro["fecha"]))
            tabla.setItem(i, 1, QTableWidgetItem(registro["usuario"]))
            tabla.setItem(i, 2, QTableWidgetItem(registro["accion"]))
            
            detalles = ""
            if registro["accion"] == "consumo":
                detalles = f"Consumo: {registro['detalles']['cantidad_consumida']} unidades"
            elif "diferencia" in registro["detalles"]:
                diff = registro["detalles"]["diferencia"]
                detalles = f"Cambio: {diff:+} unidades"
            tabla.setItem(i, 3, QTableWidgetItem(detalles))
            
        tabla.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(tabla)
        
        dialog.exec()
        
    def eliminar_producto(self):
        if not self.auth.es_admin:
            QMessageBox.critical(self, "Error", "No tiene permisos para eliminar productos")
            return
            
        fila = self.tabla_inventario.currentRow()
        if fila < 0:
            return
            
        item = self.tabla_inventario.item(fila, 0)
        if item is None:
            QMessageBox.warning(self, "Advertencia", "No se pudo obtener el producto")
            return
            
        nombre_producto = item.text()
        
        reply = QMessageBox.question(self, "Confirmar", 
            f"¿Está seguro de eliminar '{nombre_producto}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if reply == QMessageBox.StandardButton.Yes:
            self.registro.registrar_actividad(
                self.auth.usuario_actual,
                "eliminar_producto",
                {"producto": nombre_producto},
            )
            
            if self.inventario.eliminar_producto_completo(nombre_producto):
                self.actualizar_inventario_display()
                self.actualizar_combo_productos()
                QMessageBox.information(self, "Éxito", "Producto eliminado correctamente")
                
    def filtrar_inventario(self):
        busqueda = self.entry_busqueda.text().lower()
        categoria_filtro = self.combo_filtro_categoria.currentText()
        
        self.actualizar_inventario_display()
        
        for fila in range(self.tabla_inventario.rowCount() - 1, -1, -1):
            item_nombre = self.tabla_inventario.item(fila, 0)
            item_categoria = self.tabla_inventario.item(fila, 1)
            
            if item_nombre is None or item_categoria is None:
                continue
                
            nombre = item_nombre.text().lower()
            categoria = item_categoria.text()
            
            mostrar = True
            
            if categoria_filtro != "Todas" and categoria != categoria_filtro:
                mostrar = False
            elif busqueda and busqueda not in nombre:
                mostrar = False
                
            if not mostrar:
                self.tabla_inventario.removeRow(fila)
                
    def actualizar_inventario_display(self):
        self.tabla_inventario.setRowCount(0)
        
        productos = self.inventario.obtener_todos_productos()
        if isinstance(productos, dict):
            productos = [{"nombre": k, **v} if isinstance(v, dict) else {"nombre": k, "cantidad": v} for k, v in productos.items()]
        
        for producto in productos:
            if isinstance(producto, dict):
                self.insertar_producto_en_tabla(producto)
            
    def insertar_producto_en_tabla(self, producto):
        fila = self.tabla_inventario.rowCount()
        self.tabla_inventario.insertRow(fila)
        
        nombre = producto.get('nombre', 'N/A')
        categoria = producto.get('categoria', 'N/A')
        precio = producto.get('precio', 0)
        cantidad = producto.get('cantidad', 0)
        valor_total = precio * cantidad
        
        if cantidad == 0:
            estado = "Agotado"
        elif cantidad < 10:
            estado = "Stock Bajo"
        else:
            estado = "Disponible"
            
        mostrar_total = self.check_mostrar_total.isChecked()
        valor_display = f"${valor_total:,.2f}".replace(",", ".") if mostrar_total else "---"
        
        self.tabla_inventario.setItem(fila, 0, QTableWidgetItem(str(nombre)))
        self.tabla_inventario.setItem(fila, 1, QTableWidgetItem(str(categoria)))
        self.tabla_inventario.setItem(fila, 2, QTableWidgetItem(f"${precio:,.2f}".replace(",", ".")))
        self.tabla_inventario.setItem(fila, 3, QTableWidgetItem(f"{cantidad:,}".replace(",", ".")))
        self.tabla_inventario.setItem(fila, 4, QTableWidgetItem(valor_display))
        self.tabla_inventario.setItem(fila, 5, QTableWidgetItem(estado))

    # ========== PESTAÑA MATERIA PRIMA ==========

    def crear_pestana_materia_prima(self):
        """Crear pestaña de gestión de materia prima"""
        from materia_prima import MateriaPrima
        
        self.materia_prima = MateriaPrima()
        
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        tabs_materia = QTabWidget()
        layout.addWidget(tabs_materia)
        
        # ----- Tab 1: Ingredientes -----
        ingredientes_widget = QWidget()
        ingredientes_layout = QVBoxLayout()
        ingredientes_widget.setLayout(ingredientes_layout)
        
        ops_group = QGroupBox("Operaciones de Materia Prima")
        ops_layout = QHBoxLayout()
        ops_group.setLayout(ops_layout)
        
        btn_agregar_ing = QPushButton("➕ Agregar Ingrediente")
        btn_agregar_ing.clicked.connect(self.agregar_ingrediente_dialog)
        ops_layout.addWidget(btn_agregar_ing)
        
        btn_ajustar_stock = QPushButton("📊 Ajustar Stock")
        btn_ajustar_stock.clicked.connect(self.ajustar_stock_ingrediente_dialog)
        ops_layout.addWidget(btn_ajustar_stock)
        
        btn_actualizar_ing = QPushButton("🔄 Actualizar")
        btn_actualizar_ing.clicked.connect(self.actualizar_tabla_ingredientes)
        ops_layout.addWidget(btn_actualizar_ing)
        
        ops_layout.addStretch()
        ingredientes_layout.addWidget(ops_group)
        
        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("🔍 Buscar:"))
        
        self.entry_buscar_ingrediente = QLineEdit()
        self.entry_buscar_ingrediente.textChanged.connect(self.filtrar_ingredientes)
        filtro_layout.addWidget(self.entry_buscar_ingrediente)
        
        filtro_layout.addWidget(QLabel("Categoría:"))
        self.combo_categoria_ing = QComboBox()
        self.combo_categoria_ing.addItem("Todas")
        self.combo_categoria_ing.currentTextChanged.connect(self.filtrar_ingredientes)
        filtro_layout.addWidget(self.combo_categoria_ing)
        
        self.check_bajo_stock = QCheckBox("Solo bajo stock")
        self.check_bajo_stock.stateChanged.connect(self.filtrar_ingredientes)
        filtro_layout.addWidget(self.check_bajo_stock)
        
        filtro_layout.addStretch()
        ingredientes_layout.addLayout(filtro_layout)
        
        self.tabla_ingredientes = QTableWidget()
        self.tabla_ingredientes.setColumnCount(7)
        self.tabla_ingredientes.setHorizontalHeaderLabels([
            "Ingrediente", "Categoría", "Unidad", "Stock", "Stock Mínimo", 
            "Costo Unit.", "Valor Total"
        ])
        self.tabla_ingredientes.horizontalHeader().setStretchLastSection(True)
        self.tabla_ingredientes.setAlternatingRowColors(True)
        self.tabla_ingredientes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_ingredientes.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_ingredientes.customContextMenuRequested.connect(self.menu_contextual_ingredientes)
        self.tabla_ingredientes.doubleClicked.connect(self.modificar_ingrediente_dialog)
        ingredientes_layout.addWidget(self.tabla_ingredientes)
        
        stats_layout = QHBoxLayout()
        self.label_total_ingredientes = QLabel("Total ingredientes: 0")
        self.label_valor_inventario = QLabel("Valor inventario: $0")
        self.label_bajo_stock = QLabel("Bajo stock: 0")
        stats_layout.addWidget(self.label_total_ingredientes)
        stats_layout.addWidget(self.label_valor_inventario)
        stats_layout.addWidget(self.label_bajo_stock)
        stats_layout.addStretch()
        ingredientes_layout.addLayout(stats_layout)
        
        tabs_materia.addTab(ingredientes_widget, "📦 Ingredientes")
        
        # ----- Tab 2: Recetas -----
        recetas_widget = QWidget()
        recetas_layout = QHBoxLayout()
        recetas_widget.setLayout(recetas_layout)
        
        panel_izquierdo = QWidget()
        panel_izquierdo_layout = QVBoxLayout()
        panel_izquierdo.setLayout(panel_izquierdo_layout)
        
        panel_izquierdo_layout.addWidget(QLabel("📋 Productos del Menú"))
        
        self.lista_productos_recetas = QListWidget()
        self.lista_productos_recetas.itemSelectionChanged.connect(self.mostrar_receta_seleccionada)
        panel_izquierdo_layout.addWidget(self.lista_productos_recetas)
        
        btn_actualizar_productos = QPushButton("🔄 Actualizar Lista")
        btn_actualizar_productos.clicked.connect(self.cargar_productos_para_recetas)
        panel_izquierdo_layout.addWidget(btn_actualizar_productos)
        
        recetas_layout.addWidget(panel_izquierdo, 1)
        
        panel_derecho = QWidget()
        panel_derecho_layout = QVBoxLayout()
        panel_derecho.setLayout(panel_derecho_layout)
        
        panel_derecho_layout.addWidget(QLabel("🍳 Receta del Producto"))
        
        self.label_producto_seleccionado = QLabel("Seleccione un producto")
        self.label_producto_seleccionado.setStyleSheet("font-weight: bold; font-size: 14px;")
        panel_derecho_layout.addWidget(self.label_producto_seleccionado)
        
        self.tabla_receta = QTableWidget()
        self.tabla_receta.setColumnCount(4)
        self.tabla_receta.setHorizontalHeaderLabels(["Ingrediente", "Cantidad", "Unidad", "Acciones"])
        self.tabla_receta.horizontalHeader().setStretchLastSection(True)
        self.tabla_receta.setAlternatingRowColors(True)
        panel_derecho_layout.addWidget(self.tabla_receta)
        
        btn_receta_layout = QHBoxLayout()
        
        btn_agregar_ing_receta = QPushButton("➕ Agregar Ingrediente")
        btn_agregar_ing_receta.clicked.connect(self.agregar_ingrediente_receta_dialog)
        btn_receta_layout.addWidget(btn_agregar_ing_receta)
        
        btn_guardar_receta = QPushButton("💾 Guardar Receta")
        btn_guardar_receta.clicked.connect(self.guardar_receta_actual)
        btn_receta_layout.addWidget(btn_guardar_receta)
        
        btn_eliminar_receta = QPushButton("❌ Eliminar Receta")
        btn_eliminar_receta.clicked.connect(self.eliminar_receta_actual)
        btn_receta_layout.addWidget(btn_eliminar_receta)
        
        btn_verificar_stock = QPushButton("✅ Verificar Stock")
        btn_verificar_stock.clicked.connect(self.verificar_stock_receta)
        btn_receta_layout.addWidget(btn_verificar_stock)
        
        panel_derecho_layout.addLayout(btn_receta_layout)
        
        recetas_layout.addWidget(panel_derecho, 2)
        
        tabs_materia.addTab(recetas_widget, "📖 Recetas")
        
        # ----- Tab 3: Movimientos -----
        movimientos_widget = QWidget()
        movimientos_layout = QVBoxLayout()
        movimientos_widget.setLayout(movimientos_layout)
        
        filtro_mov_layout = QHBoxLayout()
        filtro_mov_layout.addWidget(QLabel("Ingrediente:"))
        
        self.combo_ingrediente_mov = QComboBox()
        self.combo_ingrediente_mov.addItem("Todos")
        self.combo_ingrediente_mov.currentTextChanged.connect(self.actualizar_tabla_movimientos)
        filtro_mov_layout.addWidget(self.combo_ingrediente_mov)
        
        btn_actualizar_mov = QPushButton("🔄 Actualizar")
        btn_actualizar_mov.clicked.connect(self.actualizar_tabla_movimientos)
        filtro_mov_layout.addWidget(btn_actualizar_mov)
        
        filtro_mov_layout.addStretch()
        movimientos_layout.addLayout(filtro_mov_layout)
        
        self.tabla_movimientos = QTableWidget()
        self.tabla_movimientos.setColumnCount(5)
        self.tabla_movimientos.setHorizontalHeaderLabels([
            "Fecha", "Ingrediente", "Tipo", "Cantidad", "Motivo"
        ])
        self.tabla_movimientos.horizontalHeader().setStretchLastSection(True)
        self.tabla_movimientos.setAlternatingRowColors(True)
        movimientos_layout.addWidget(self.tabla_movimientos)
        
        tabs_materia.addTab(movimientos_widget, "📊 Movimientos")
        
        self.tab_widget.addTab(widget, "🥩 Materia Prima")
        
        self.actualizar_tabla_ingredientes()
        self.cargar_productos_para_recetas()
        self.actualizar_combo_ingredientes()

    # ========== MÉTODOS DE MATERIA PRIMA (INGREDIENTES) ==========

    def actualizar_tabla_ingredientes(self):
        """Actualizar tabla de ingredientes"""
        if not hasattr(self, 'tabla_ingredientes'):
            return
        
        self.tabla_ingredientes.setRowCount(0)
        ingredientes = self.materia_prima.obtener_todos_ingredientes()
        
        total_valor = 0
        bajo_stock_count = 0
        
        for ing in ingredientes:
            fila = self.tabla_ingredientes.rowCount()
            self.tabla_ingredientes.insertRow(fila)
            
            stock = ing.get('stock', 0)
            stock_min = ing.get('stock_minimo', 0)
            costo = ing.get('costo_unitario', 0)
            valor_total = stock * costo
            total_valor += valor_total
            
            if stock <= stock_min:
                bajo_stock_count += 1
            
            self.tabla_ingredientes.setItem(fila, 0, QTableWidgetItem(ing.get('nombre', '')))
            self.tabla_ingredientes.setItem(fila, 1, QTableWidgetItem(ing.get('categoria', '')))
            self.tabla_ingredientes.setItem(fila, 2, QTableWidgetItem(ing.get('unidad', '')))
            self.tabla_ingredientes.setItem(fila, 3, QTableWidgetItem(f"{stock:,.2f}"))
            self.tabla_ingredientes.setItem(fila, 4, QTableWidgetItem(f"{stock_min:,.2f}"))
            self.tabla_ingredientes.setItem(fila, 5, QTableWidgetItem(f"${costo:,.2f}"))
            self.tabla_ingredientes.setItem(fila, 6, QTableWidgetItem(f"${valor_total:,.2f}"))
            
            if stock <= stock_min:
                for col in range(7):
                    item = self.tabla_ingredientes.item(fila, col)
                    if item:
                        item.setBackground(Qt.GlobalColor.yellow)
        
        self.label_total_ingredientes.setText(f"Total ingredientes: {len(ingredientes)}")
        self.label_valor_inventario.setText(f"Valor inventario: ${total_valor:,.2f}")
        self.label_bajo_stock.setText(f"Bajo stock: {bajo_stock_count}")
        
        categorias = self.materia_prima.obtener_categorias_ingredientes()
        self.combo_categoria_ing.clear()
        self.combo_categoria_ing.addItem("Todas")
        self.combo_categoria_ing.addItems(categorias)

    def filtrar_ingredientes(self):
        """Filtrar tabla de ingredientes"""
        if not hasattr(self, 'entry_buscar_ingrediente'):
            return
            
        busqueda = self.entry_buscar_ingrediente.text().lower()
        categoria = self.combo_categoria_ing.currentText()
        solo_bajo_stock = self.check_bajo_stock.isChecked()
        
        for fila in range(self.tabla_ingredientes.rowCount()):
            mostrar = True
            
            item_nombre = self.tabla_ingredientes.item(fila, 0)
            item_cat = self.tabla_ingredientes.item(fila, 1)
            item_stock = self.tabla_ingredientes.item(fila, 3)
            item_stock_min = self.tabla_ingredientes.item(fila, 4)
            
            if item_nombre is None or item_cat is None or item_stock is None or item_stock_min is None:
                self.tabla_ingredientes.setRowHidden(fila, True)
                continue
            
            nombre = item_nombre.text().lower()
            cat = item_cat.text()
            stock_texto = item_stock.text()
            stock_min_texto = item_stock_min.text()
            
            try:
                stock_texto_limpio = stock_texto.replace(',', '').replace('$', '').strip()
                stock_min_texto_limpio = stock_min_texto.replace(',', '').replace('$', '').strip()
                
                stock = float(stock_texto_limpio)
                stock_min = float(stock_min_texto_limpio)
            except (ValueError, AttributeError):
                stock = 0
                stock_min = 0
            
            if busqueda and busqueda not in nombre:
                mostrar = False
            elif categoria != "Todas" and cat != categoria:
                mostrar = False
            elif solo_bajo_stock and stock > stock_min:
                mostrar = False
            
            self.tabla_ingredientes.setRowHidden(fila, not mostrar)

    def agregar_ingrediente_dialog(self):
        """Diálogo para agregar ingrediente"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar Ingrediente")
        dialog.setFixedSize(400, 350)
        
        layout = QFormLayout(dialog)
        
        entry_nombre = QLineEdit()
        layout.addRow("Nombre:", entry_nombre)
        
        combo_categoria = QComboBox()
        if hasattr(self, 'categorias_materia') and self.categorias_materia:
            combo_categoria.addItems(sorted(self.categorias_materia))
        else:
            combo_categoria.addItems(["Carnes", "Lácteos", "Harinas", "Verduras", "Salsas", "Bebidas", "Especias"])
        combo_categoria.setEditable(True)
        combo_categoria.setCurrentText("General")
        layout.addRow("Categoría:", combo_categoria)
        
        combo_unidad = QComboBox()
        combo_unidad.addItems(["kg", "g", "L", "ml", "unidad", "docena", "paquete"])
        layout.addRow("Unidad:", combo_unidad)
        
        entry_stock = QDoubleSpinBox()
        entry_stock.setRange(0, 999999)
        entry_stock.setDecimals(2)
        layout.addRow("Stock inicial:", entry_stock)
        
        entry_costo = QDoubleSpinBox()
        entry_costo.setRange(0, 999999)
        entry_costo.setDecimals(2)
        entry_costo.setPrefix("$")
        layout.addRow("Costo unitario:", entry_costo)
        
        entry_stock_min = QDoubleSpinBox()
        entry_stock_min.setRange(0, 999999)
        entry_stock_min.setDecimals(2)
        layout.addRow("Stock mínimo:", entry_stock_min)
        
        buttons = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancelar")
        buttons.addWidget(btn_guardar)
        buttons.addWidget(btn_cancelar)
        layout.addRow(buttons)
        
        def guardar():
            nombre = entry_nombre.text().strip()
            if not nombre:
                QMessageBox.critical(dialog, "Error", "Nombre requerido")
                return
            
            categoria = combo_categoria.currentText().strip()
            if not categoria:
                categoria = "General"
            
            if self.materia_prima.agregar_ingrediente(
                nombre=nombre,
                categoria=categoria,
                unidad=combo_unidad.currentText(),
                stock_inicial=entry_stock.value(),
                costo_unitario=entry_costo.value(),
                stock_minimo=entry_stock_min.value()
            ):
                self.actualizar_tabla_ingredientes()
                self.actualizar_combo_ingredientes()
                dialog.accept()
                QMessageBox.information(self, "Éxito", f"Ingrediente '{nombre}' agregado")
            else:
                QMessageBox.critical(dialog, "Error", "El ingrediente ya existe")
        
        btn_guardar.clicked.connect(guardar)
        btn_cancelar.clicked.connect(dialog.reject)
        dialog.exec()

    def ajustar_stock_ingrediente_dialog(self):
        """Diálogo para ajustar stock"""
        fila = self.tabla_ingredientes.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Advertencia", "Seleccione un ingrediente")
            return
        
        item_nombre = self.tabla_ingredientes.item(fila, 0)
        if item_nombre is None:
            QMessageBox.warning(self, "Advertencia", "No se pudo obtener el ingrediente")
            return
        
        nombre = item_nombre.text()
        ingrediente = self.materia_prima.obtener_ingrediente(nombre)
        
        if not ingrediente:
            QMessageBox.warning(self, "Advertencia", f"Ingrediente '{nombre}' no encontrado")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Ajustar Stock - {nombre}")
        dialog.setFixedSize(350, 250)
        
        layout = QFormLayout(dialog)
        
        stock_actual = ingrediente.get('stock', 0)
        unidad = ingrediente.get('unidad', 'unidad')
        
        layout.addRow(QLabel(f"Stock actual: {stock_actual} {unidad}"))
        
        combo_tipo = QComboBox()
        combo_tipo.addItems(["ingreso", "egreso"])
        layout.addRow("Tipo de movimiento:", combo_tipo)
        
        entry_cantidad = QDoubleSpinBox()
        entry_cantidad.setRange(0.01, 999999)
        entry_cantidad.setDecimals(2)
        entry_cantidad.setSuffix(f" {unidad}")
        layout.addRow("Cantidad:", entry_cantidad)
        
        entry_motivo = QLineEdit()
        layout.addRow("Motivo:", entry_motivo)
        
        buttons = QHBoxLayout()
        btn_aplicar = QPushButton("Aplicar")
        btn_cancelar = QPushButton("Cancelar")
        buttons.addWidget(btn_aplicar)
        buttons.addWidget(btn_cancelar)
        layout.addRow(buttons)
        
        def aplicar():
            tipo = combo_tipo.currentText()
            cantidad = entry_cantidad.value()
            motivo = entry_motivo.text().strip() or "Ajuste manual"
            
            if self.materia_prima.ajustar_stock(nombre, cantidad, tipo, motivo):
                self.actualizar_tabla_ingredientes()
                self.actualizar_combo_ingredientes()
                dialog.accept()
                QMessageBox.information(self, "Éxito", f"Stock actualizado: {tipo} de {cantidad} {unidad}")
            else:
                QMessageBox.critical(dialog, "Error", "No se pudo ajustar el stock (stock insuficiente)")
        
        btn_aplicar.clicked.connect(aplicar)
        btn_cancelar.clicked.connect(dialog.reject)
        dialog.exec()

    def menu_contextual_ingredientes(self, pos):
        """Menú contextual para ingredientes"""
        fila = self.tabla_ingredientes.currentRow()
        if fila < 0:
            return
        
        item = self.tabla_ingredientes.item(fila, 0)
        if item is None:
            return
        
        menu = QMenu()
        modificar_action = menu.addAction("✏️ Modificar")
        ajustar_action = menu.addAction("📊 Ajustar Stock")
        menu.addSeparator()
        eliminar_action = menu.addAction("❌ Eliminar")
        
        action = menu.exec(self.tabla_ingredientes.mapToGlobal(pos))
        
        if action == modificar_action:
            self.modificar_ingrediente_dialog()
        elif action == ajustar_action:
            self.ajustar_stock_ingrediente_dialog()
        elif action == eliminar_action:
            self.eliminar_ingrediente()

    def modificar_ingrediente_dialog(self):
        """Diálogo para modificar ingrediente"""
        fila = self.tabla_ingredientes.currentRow()
        if fila < 0:
            return
        
        item_nombre = self.tabla_ingredientes.item(fila, 0)
        if item_nombre is None:
            QMessageBox.warning(self, "Advertencia", "No se pudo obtener el ingrediente")
            return
        
        nombre_original = item_nombre.text()
        ingrediente = self.materia_prima.obtener_ingrediente(nombre_original)
        
        if not ingrediente:
            QMessageBox.warning(self, "Advertencia", f"Ingrediente '{nombre_original}' no encontrado")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modificar - {nombre_original}")
        dialog.setFixedSize(400, 300)
        
        layout = QFormLayout(dialog)
        
        entry_nombre = QLineEdit(ingrediente.get('nombre', ''))
        layout.addRow("Nombre:", entry_nombre)
        
        combo_categoria = QComboBox()
        if hasattr(self, 'categorias_materia') and self.categorias_materia:
            combo_categoria.addItems(sorted(self.categorias_materia))
        else:
            combo_categoria.addItems(["Carnes", "Lácteos", "Harinas", "Verduras", "Salsas", "Bebidas", "Especias"])
        combo_categoria.setEditable(True)
        combo_categoria.setCurrentText(ingrediente.get('categoria', 'General'))
        layout.addRow("Categoría:", combo_categoria)
        
        combo_unidad = QComboBox()
        combo_unidad.addItems(["kg", "g", "L", "ml", "unidad", "docena", "paquete"])
        combo_unidad.setCurrentText(ingrediente.get('unidad', 'unidad'))
        layout.addRow("Unidad:", combo_unidad)
        
        entry_costo = QDoubleSpinBox()
        entry_costo.setRange(0, 999999)
        entry_costo.setDecimals(2)
        entry_costo.setValue(ingrediente.get('costo_unitario', 0))
        entry_costo.setPrefix("$")
        layout.addRow("Costo unitario:", entry_costo)
        
        entry_stock_min = QDoubleSpinBox()
        entry_stock_min.setRange(0, 999999)
        entry_stock_min.setDecimals(2)
        entry_stock_min.setValue(ingrediente.get('stock_minimo', 0))
        layout.addRow("Stock mínimo:", entry_stock_min)
        
        buttons = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancelar")
        buttons.addWidget(btn_guardar)
        buttons.addWidget(btn_cancelar)
        layout.addRow(buttons)
        
        def guardar():
            nuevo_nombre = entry_nombre.text().strip()
            if not nuevo_nombre:
                QMessageBox.critical(dialog, "Error", "Nombre requerido")
                return
            
            categoria = combo_categoria.currentText().strip()
            if not categoria:
                categoria = "General"
            
            datos = {
                'nombre': nuevo_nombre,
                'categoria': categoria,
                'unidad': combo_unidad.currentText(),
                'costo_unitario': entry_costo.value(),
                'stock_minimo': entry_stock_min.value()
            }
            
            if self.materia_prima.modificar_ingrediente(nombre_original, datos):
                self.actualizar_tabla_ingredientes()
                self.actualizar_combo_ingredientes()
                dialog.accept()
                QMessageBox.information(self, "Éxito", "Ingrediente modificado")
            else:
                QMessageBox.critical(dialog, "Error", "No se pudo modificar")
        
        btn_guardar.clicked.connect(guardar)
        btn_cancelar.clicked.connect(dialog.reject)
        dialog.exec()

    def eliminar_ingrediente(self):
        """Eliminar ingrediente seleccionado"""
        fila = self.tabla_ingredientes.currentRow()
        if fila < 0:
            return
        
        item_nombre = self.tabla_ingredientes.item(fila, 0)
        if item_nombre is None:
            QMessageBox.warning(self, "Advertencia", "No se pudo obtener el ingrediente")
            return
        
        nombre = item_nombre.text()
        
        reply = QMessageBox.question(self, "Confirmar",
            f"¿Eliminar ingrediente '{nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.materia_prima.eliminar_ingrediente(nombre):
                self.actualizar_tabla_ingredientes()
                self.actualizar_combo_ingredientes()
                QMessageBox.information(self, "Éxito", "Ingrediente eliminado")
            else:
                QMessageBox.critical(self, "Error", 
                    "No se pudo eliminar. El ingrediente puede estar en uso en alguna receta.")

    def cargar_productos_para_recetas(self):
        """Cargar productos del inventario en la lista de recetas"""
        if not hasattr(self, 'lista_productos_recetas'):
            return
        
        self.lista_productos_recetas.clear()
        productos = self.inventario.obtener_todos_productos()
        
        if isinstance(productos, dict):
            for nombre in productos.keys():
                self.lista_productos_recetas.addItem(str(nombre))
        else:
            for p in productos:
                nombre = p.get('nombre') if isinstance(p, dict) else p
                if nombre:
                    self.lista_productos_recetas.addItem(str(nombre))

    def mostrar_receta_seleccionada(self):
        """Mostrar receta del producto seleccionado"""
        item = self.lista_productos_recetas.currentItem()
        if not item:
            return
        
        producto = item.text()
        self.label_producto_seleccionado.setText(f"📝 Receta de: {producto}")
        
        receta = self.materia_prima.obtener_receta(producto)
        
        self.tabla_receta.setRowCount(0)
        for ing in receta:
            fila = self.tabla_receta.rowCount()
            self.tabla_receta.insertRow(fila)
            
            ingrediente = ing.get('ingrediente', '')
            cantidad = ing.get('cantidad', 0)
            unidad = ing.get('unidad', '')
            
            self.tabla_receta.setItem(fila, 0, QTableWidgetItem(ingrediente))
            self.tabla_receta.setItem(fila, 1, QTableWidgetItem(str(cantidad)))
            self.tabla_receta.setItem(fila, 2, QTableWidgetItem(unidad))
            
            btn_eliminar = QPushButton("🗑️")
            btn_eliminar.clicked.connect(lambda checked, r=fila: self.eliminar_ingrediente_receta(r))
            self.tabla_receta.setCellWidget(fila, 3, btn_eliminar)

    def agregar_ingrediente_receta_dialog(self):
        """Diálogo para agregar ingrediente a receta"""
        item = self.lista_productos_recetas.currentItem()
        if not item:
            QMessageBox.warning(self, "Advertencia", "Seleccione un producto primero")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar Ingrediente a Receta")
        dialog.setFixedSize(350, 200)
        
        layout = QFormLayout(dialog)
        
        combo_ingrediente = QComboBox()
        ingredientes = self.materia_prima.obtener_todos_ingredientes()
        
        if not ingredientes:
            QMessageBox.warning(self, "Advertencia", "No hay ingredientes registrados. Agregue ingredientes primero.")
            dialog.reject()
            return
        
        for ing in ingredientes:
            nombre = ing.get('nombre', '')
            if nombre:
                combo_ingrediente.addItem(nombre)
        layout.addRow("Ingrediente:", combo_ingrediente)
        
        entry_cantidad = QDoubleSpinBox()
        entry_cantidad.setRange(0.001, 999999)
        entry_cantidad.setDecimals(3)
        entry_cantidad.setSingleStep(0.1)
        layout.addRow("Cantidad:", entry_cantidad)
        
        buttons = QHBoxLayout()
        btn_agregar = QPushButton("Agregar")
        btn_cancelar = QPushButton("Cancelar")
        buttons.addWidget(btn_agregar)
        buttons.addWidget(btn_cancelar)
        layout.addRow(buttons)
        
        def agregar():
            ingrediente = combo_ingrediente.currentText()
            cantidad = entry_cantidad.value()
            
            if ingrediente and cantidad > 0:
                ing_data = self.materia_prima.obtener_ingrediente(ingrediente)
                
                if ing_data:
                    fila = self.tabla_receta.rowCount()
                    self.tabla_receta.insertRow(fila)
                    self.tabla_receta.setItem(fila, 0, QTableWidgetItem(ingrediente))
                    self.tabla_receta.setItem(fila, 1, QTableWidgetItem(str(cantidad)))
                    self.tabla_receta.setItem(fila, 2, QTableWidgetItem(ing_data.get('unidad', 'unidad')))
                    
                    btn_eliminar = QPushButton("🗑️")
                    btn_eliminar.clicked.connect(lambda checked, r=fila: self.eliminar_ingrediente_receta(r))
                    self.tabla_receta.setCellWidget(fila, 3, btn_eliminar)
                    
                    dialog.accept()
                else:
                    QMessageBox.critical(dialog, "Error", "Ingrediente no encontrado")
            else:
                QMessageBox.critical(dialog, "Error", "Seleccione un ingrediente y una cantidad válida")
        
        btn_agregar.clicked.connect(agregar)
        btn_cancelar.clicked.connect(dialog.reject)
        dialog.exec()

    def eliminar_ingrediente_receta(self, fila):
        """Eliminar ingrediente de la receta actual"""
        if fila >= 0 and fila < self.tabla_receta.rowCount():
            self.tabla_receta.removeRow(fila)

    def guardar_receta_actual(self):
        """Guardar la receta del producto seleccionado"""
        item = self.lista_productos_recetas.currentItem()
        if not item:
            QMessageBox.warning(self, "Advertencia", "Seleccione un producto primero")
            return
        
        producto = item.text()
        ingredientes = []
        
        for fila in range(self.tabla_receta.rowCount()):
            item_ingrediente = self.tabla_receta.item(fila, 0)
            item_cantidad = self.tabla_receta.item(fila, 1)
            item_unidad = self.tabla_receta.item(fila, 2)
            
            if item_ingrediente is None or item_cantidad is None or item_unidad is None:
                continue
            
            try:
                ingrediente = item_ingrediente.text().strip()
                cantidad_texto = item_cantidad.text().strip()
                unidad = item_unidad.text().strip()
                
                cantidad = float(cantidad_texto) if cantidad_texto else 0
                
                if ingrediente and cantidad > 0:
                    ingredientes.append({
                        'ingrediente': ingrediente,
                        'cantidad': cantidad,
                        'unidad': unidad
                    })
            except (ValueError, AttributeError):
                continue
        
        if not ingredientes:
            QMessageBox.warning(self, "Advertencia", "La receta debe tener al menos un ingrediente válido")
            return
        
        if self.materia_prima.crear_receta(producto, ingredientes):
            QMessageBox.information(self, "Éxito", f"Receta de '{producto}' guardada con {len(ingredientes)} ingredientes")
        else:
            QMessageBox.critical(self, "Error", "No se pudo guardar la receta")

    def eliminar_receta_actual(self):
        """Eliminar receta del producto seleccionado"""
        item = self.lista_productos_recetas.currentItem()
        if not item:
            return
        
        producto = item.text()
        
        reply = QMessageBox.question(self, "Confirmar",
            f"¿Eliminar receta de '{producto}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.materia_prima.eliminar_receta(producto):
                self.tabla_receta.setRowCount(0)
                QMessageBox.information(self, "Éxito", "Receta eliminada")

    def verificar_stock_receta(self):
        """Verificar stock para la receta actual"""
        item = self.lista_productos_recetas.currentItem()
        if not item:
            QMessageBox.warning(self, "Advertencia", "Seleccione un producto primero")
            return
        
        producto = item.text()
        
        if self.tabla_receta.rowCount() == 0:
            QMessageBox.warning(self, "Advertencia", "El producto no tiene receta definida")
            return
        
        disponible, mensaje = self.materia_prima.verificar_disponibilidad_receta(producto)
        
        if disponible:
            QMessageBox.information(self, "✅ Stock Suficiente", 
                f"Hay stock suficiente para producir {producto}\n\n{mensaje}")
        else:
            QMessageBox.warning(self, "⚠️ Stock Insuficiente", 
                f"Falta stock para producir {producto}:\n\n{mensaje}")

    def actualizar_combo_ingredientes(self):
        """Actualizar combo de ingredientes para movimientos"""
        if not hasattr(self, 'combo_ingrediente_mov'):
            return
        
        self.combo_ingrediente_mov.clear()
        self.combo_ingrediente_mov.addItem("Todos")
        
        ingredientes = self.materia_prima.obtener_todos_ingredientes()
        for ing in ingredientes:
            self.combo_ingrediente_mov.addItem(ing['nombre'])

    def actualizar_tabla_movimientos(self):
        """Actualizar tabla de movimientos"""
        if not hasattr(self, 'tabla_movimientos') or not hasattr(self, 'combo_ingrediente_mov'):
            return
        
        ingrediente = self.combo_ingrediente_mov.currentText()
        if ingrediente == "Todos":
            ingrediente = None
        
        movimientos = self.materia_prima.obtener_movimientos(ingrediente, limite=200)
        
        self.tabla_movimientos.setRowCount(0)
        for mov in reversed(movimientos):
            fila = self.tabla_movimientos.rowCount()
            self.tabla_movimientos.insertRow(fila)
            
            try:
                fecha = datetime.fromisoformat(mov['fecha']).strftime("%Y-%m-%d %H:%M")
            except:
                fecha = mov.get('fecha', 'N/A')
            
            tipo_icono = "🟢 Ingreso" if mov.get('tipo') == 'ingreso' else "🔴 Egreso"
            ingrediente_nombre = mov.get('ingrediente', 'N/A')
            cantidad = mov.get('cantidad', 0)
            motivo = mov.get('motivo', '')
            
            self.tabla_movimientos.setItem(fila, 0, QTableWidgetItem(fecha))
            self.tabla_movimientos.setItem(fila, 1, QTableWidgetItem(ingrediente_nombre))
            self.tabla_movimientos.setItem(fila, 2, QTableWidgetItem(tipo_icono))
            self.tabla_movimientos.setItem(fila, 3, QTableWidgetItem(f"{cantidad:,.2f}"))
            self.tabla_movimientos.setItem(fila, 4, QTableWidgetItem(motivo))

    # ========== PESTAÑA PEDIDOS ==========
        
    def crear_pestana_pedidos(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        pendientes_group = QGroupBox("Pedidos Pendientes")
        pendientes_layout = QVBoxLayout()
        pendientes_group.setLayout(pendientes_layout)
        
        self.tabla_pedidos = QTableWidget()
        self.tabla_pedidos.setColumnCount(5)
        self.tabla_pedidos.setHorizontalHeaderLabels([
            "ID", "Cliente", "Total", "Hora", "Estado"
        ])
        self.tabla_pedidos.horizontalHeader().setStretchLastSection(True)
        self.tabla_pedidos.setAlternatingRowColors(True)
        self.tabla_pedidos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_pedidos.itemSelectionChanged.connect(self.mostrar_detalle_pedido)
        pendientes_layout.addWidget(self.tabla_pedidos)
        
        layout.addWidget(pendientes_group)
        
        detalle_group = QGroupBox("Detalle del Pedido")
        detalle_layout = QVBoxLayout()
        detalle_group.setLayout(detalle_layout)
        
        self.text_detalle = QTextEdit()
        self.text_detalle.setReadOnly(True)
        detalle_layout.addWidget(self.text_detalle)
        
        layout.addWidget(detalle_group)
        
        acciones_layout = QHBoxLayout()
        
        btn_confirmar = QPushButton("✅ Confirmar Pedido")
        btn_confirmar.clicked.connect(self.confirmar_pedido)
        acciones_layout.addWidget(btn_confirmar)
        
        btn_rechazar = QPushButton("❌ Rechazar Pedido")
        btn_rechazar.clicked.connect(self.rechazar_pedido)
        acciones_layout.addWidget(btn_rechazar)
        
        btn_actualizar_pedidos = QPushButton("🔄 Actualizar")
        btn_actualizar_pedidos.clicked.connect(self.actualizar_pedidos_display)
        acciones_layout.addWidget(btn_actualizar_pedidos)
        
        acciones_layout.addStretch()
        layout.addLayout(acciones_layout)
        
        self.tab_widget.addTab(widget, "🛵 Pedidos Web")

    def actualizar_pedidos_display(self):
        if not hasattr(self, 'tabla_pedidos') or self.tabla_pedidos is None:
            return
            
        self.tabla_pedidos.setRowCount(0)
        
        try:
            pedidos = self.gestor_pedidos.obtener_pedidos_pendientes()
            for pedido in pedidos:
                fila = self.tabla_pedidos.rowCount()
                self.tabla_pedidos.insertRow(fila)
                self.tabla_pedidos.setItem(fila, 0, QTableWidgetItem(pedido["id"][:8]))
                self.tabla_pedidos.setItem(fila, 1, QTableWidgetItem(pedido["cliente"]))
                self.tabla_pedidos.setItem(fila, 2, QTableWidgetItem(f"${pedido['total']:,.2f}"))
                self.tabla_pedidos.setItem(fila, 3, QTableWidgetItem(pedido["hora"]))
                self.tabla_pedidos.setItem(fila, 4, QTableWidgetItem(pedido["estado"]))
        except Exception as e:
            print(f"Error al actualizar pedidos: {e}")
            
    def mostrar_detalle_pedido(self):
        fila = self.tabla_pedidos.currentRow()
        if fila < 0:
            return
            
        pedido_id_item = self.tabla_pedidos.item(fila, 0)
        if not pedido_id_item:
            return
            
        id_corto = pedido_id_item.text()
        pedidos = self.gestor_pedidos.obtener_pedidos_pendientes()
        
        for pedido in pedidos:
            if pedido.get("id", "").startswith(id_corto):
                self.pedido_actual = pedido
                self.text_detalle.clear()
                self.text_detalle.append(f"Pedido #{pedido['id'][:8]}")
                self.text_detalle.append(f"Cliente: {pedido.get('cliente', 'N/A')}")
                self.text_detalle.append(f"Teléfono: {pedido.get('telefono', 'N/A')}")
                self.text_detalle.append(f"Dirección: {pedido.get('direccion', 'N/A')}\n")
                self.text_detalle.append("Productos:")
                
                for item in pedido.get("items", []):
                    self.text_detalle.append(
                        f"  • {item['cantidad']}x {item['nombre']} - ${item['subtotal']:,.2f}"
                    )
                    
                self.text_detalle.append(f"\nTotal: ${pedido.get('total', 0):,.2f}")
                break
                
    def confirmar_pedido(self):
        if not self.pedido_actual:
            QMessageBox.warning(self, "Advertencia", "Seleccione un pedido primero")
            return
            
        for item in self.pedido_actual["items"]:
            self.registro.registrar_consumo(
                self.auth.usuario_actual,
                item["nombre"],
                item["cantidad"],
                item["precio_unitario"],
                "venta",
            )
            
        if self.gestor_pedidos.confirmar_pedido(self.pedido_actual["id"]):
            self.registro.registrar_actividad(
                self.auth.usuario_actual,
                "confirmar_pedido",
                {
                    "pedido_id": self.pedido_actual["id"],
                    "cliente": self.pedido_actual.get("cliente", "N/A"),
                    "total": self.pedido_actual.get("total", 0),
                    "items": len(self.pedido_actual.get("items", []))
                }
            )
            
            self.impresora.imprimir_recibo(self.pedido_actual, self.entry_impresora.text())
            self.actualizar_pedidos_display()
            self.actualizar_inventario_display()
            self.cargar_registro_hoy()
            self.text_detalle.clear()
            self.pedido_actual = None
            QMessageBox.information(self, "Éxito", "Pedido confirmado")
            
    def rechazar_pedido(self):
        if not self.pedido_actual:
            QMessageBox.warning(self, "Advertencia", "Seleccione un pedido primero")
            return
            
        if self.gestor_pedidos.rechazar_pedido(self.pedido_actual["id"]):
            self.registro.registrar_actividad(
                self.auth.usuario_actual,
                "rechazar_pedido",
                {
                    "pedido_id": self.pedido_actual["id"],
                    "cliente": self.pedido_actual.get("cliente", "N/A"),
                    "total": self.pedido_actual.get("total", 0),
                    "items": len(self.pedido_actual.get("items", []))
                }
            )
            
            self.actualizar_pedidos_display()
            self.text_detalle.clear()
            self.pedido_actual = None
            QMessageBox.information(self, "Éxito", "Pedido rechazado")

    # ========== PESTAÑA REGISTROS ==========

    def crear_pestana_registros(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        fecha_layout = QHBoxLayout()
        fecha_layout.addWidget(QLabel("Fecha:"))
        
        self.entry_fecha = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.entry_fecha.setMaximumWidth(120)
        fecha_layout.addWidget(self.entry_fecha)
        
        btn_buscar = QPushButton("📅 Buscar")
        btn_buscar.clicked.connect(self.cargar_registro_fecha)
        fecha_layout.addWidget(btn_buscar)
        
        btn_hoy = QPushButton("📊 Hoy")
        btn_hoy.clicked.connect(self.cargar_registro_hoy)
        fecha_layout.addWidget(btn_hoy)
        
        fecha_layout.addStretch()
        layout.addLayout(fecha_layout)
        
        resumen_group = QGroupBox("Resumen del Día")
        resumen_layout = QVBoxLayout()
        resumen_group.setLayout(resumen_layout)
        
        self.text_resumen = QTextEdit()
        self.text_resumen.setReadOnly(True)
        self.text_resumen.setMaximumHeight(100)
        resumen_layout.addWidget(self.text_resumen)
        
        layout.addWidget(resumen_group)
        
        tabs_registros = QTabWidget()
        layout.addWidget(tabs_registros)
        
        # Tab 1: Consumo
        consumidos_widget = QWidget()
        consumidos_layout = QVBoxLayout()
        consumidos_widget.setLayout(consumidos_layout)
        
        self.tabla_consumo = QTableWidget()
        self.tabla_consumo.setColumnCount(4)
        self.tabla_consumo.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio Unit.", "Valor Total"])
        self.tabla_consumo.horizontalHeader().setStretchLastSection(True)
        self.tabla_consumo.setAlternatingRowColors(True)
        consumidos_layout.addWidget(self.tabla_consumo)
        
        tabs_registros.addTab(consumidos_widget, "📦 Consumo")
        
        # Tab 2: Pedidos Aceptados
        aceptados_widget = QWidget()
        aceptados_layout = QVBoxLayout()
        aceptados_widget.setLayout(aceptados_layout)
        
        self.tabla_pedidos_aceptados = QTableWidget()
        self.tabla_pedidos_aceptados.setColumnCount(7)
        self.tabla_pedidos_aceptados.setHorizontalHeaderLabels(["ID", "Hora", "Cliente", "Tel.", "Dirección", "Total", "Items"])
        self.tabla_pedidos_aceptados.horizontalHeader().setStretchLastSection(True)
        self.tabla_pedidos_aceptados.setAlternatingRowColors(True)
        self.tabla_pedidos_aceptados.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_pedidos_aceptados.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_pedidos_aceptados.customContextMenuRequested.connect(self.menu_contextual_pedidos_aceptados)
        aceptados_layout.addWidget(self.tabla_pedidos_aceptados)
        
        tabs_registros.addTab(aceptados_widget, "✅ Aceptados")
        
        # Tab 3: Pedidos Rechazados
        rechazados_widget = QWidget()
        rechazados_layout = QVBoxLayout()
        rechazados_widget.setLayout(rechazados_layout)
        
        self.tabla_pedidos_rechazados = QTableWidget()
        self.tabla_pedidos_rechazados.setColumnCount(7)
        self.tabla_pedidos_rechazados.setHorizontalHeaderLabels(["ID", "Hora", "Cliente", "Tel.", "Dirección", "Total", "Items"])
        self.tabla_pedidos_rechazados.horizontalHeader().setStretchLastSection(True)
        self.tabla_pedidos_rechazados.setAlternatingRowColors(True)
        self.tabla_pedidos_rechazados.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_pedidos_rechazados.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_pedidos_rechazados.customContextMenuRequested.connect(self.menu_contextual_pedidos_rechazados)
        rechazados_layout.addWidget(self.tabla_pedidos_rechazados)
        
        tabs_registros.addTab(rechazados_widget, "❌ Rechazados")
        
        # Tab 4: Productos Agregados
        agregados_widget = QWidget()
        agregados_layout = QVBoxLayout()
        agregados_widget.setLayout(agregados_layout)
        
        self.tabla_agregados = QTableWidget()
        self.tabla_agregados.setColumnCount(5)
        self.tabla_agregados.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio", "Usuario", "Hora"])
        self.tabla_agregados.horizontalHeader().setStretchLastSection(True)
        self.tabla_agregados.setAlternatingRowColors(True)
        agregados_layout.addWidget(self.tabla_agregados)
        
        tabs_registros.addTab(agregados_widget, "📥 Agregados")
        
        # Tab 5: Actividades
        actividades_widget = QWidget()
        actividades_layout = QVBoxLayout()
        actividades_widget.setLayout(actividades_layout)
        
        self.tabla_actividades = QTableWidget()
        self.tabla_actividades.setColumnCount(4)
        self.tabla_actividades.setHorizontalHeaderLabels(["Hora", "Usuario", "Acción", "Detalles"])
        self.tabla_actividades.horizontalHeader().setStretchLastSection(True)
        self.tabla_actividades.setAlternatingRowColors(True)
        self.tabla_actividades.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_actividades.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_actividades.customContextMenuRequested.connect(self.menu_contextual_actividades)
        actividades_layout.addWidget(self.tabla_actividades)
        
        tabs_registros.addTab(actividades_widget, "📋 Actividades")
        
        self.tab_widget.addTab(widget, "📋 Registros Diarios")
        
        self.cargar_registro_hoy()

    def cargar_registro_hoy(self):
        self.entry_fecha.setText(datetime.now().strftime("%Y-%m-%d"))
        self.cargar_registro_fecha()
        
    def cargar_registro_fecha(self):
        try:
            fecha_str = self.entry_fecha.text()
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            consumo = self.registro.obtener_consumo_diario(fecha)
            actividades = self.registro.cargar_actividades(fecha)
            pedidos_aceptados, pedidos_rechazados = self._cargar_pedidos_por_fecha(fecha)
            
            if consumo is None:
                consumo = {"fecha": fecha_str, "total_unidades": 0, "valor_total": 0, "productos": {}, "productos_agregados": []}
            
            self.text_resumen.clear()
            self.text_resumen.append(f"📅 Fecha: {consumo.get('fecha', fecha_str)}")
            self.text_resumen.append(f"📦 Total unidades consumidas: {consumo.get('total_unidades', 0):,}".replace(",", "."))
            self.text_resumen.append(f"💰 Valor total consumido: ${consumo.get('valor_total', 0):,.2f}".replace(",", "."))
            self.text_resumen.append(f"📝 Total actividades registradas: {len(actividades) if actividades else 0}")
            self.text_resumen.append(f"✅ Pedidos aceptados: {len(pedidos_aceptados)}")
            self.text_resumen.append(f"❌ Pedidos rechazados: {len(pedidos_rechazados)}")
            
            # Tabla pedidos aceptados
            self.tabla_pedidos_aceptados.setRowCount(0)
            for pedido in pedidos_aceptados:
                fila = self.tabla_pedidos_aceptados.rowCount()
                self.tabla_pedidos_aceptados.insertRow(fila)
                
                pedido_id = pedido.get('id', 'N/A')[:8]
                hora = pedido.get('hora', 'N/A')
                cliente = pedido.get('cliente', 'N/A')
                telefono = pedido.get('telefono', 'N/A')
                direccion = pedido.get('direccion', 'N/A')
                direccion_corta = direccion[:25] + "..." if len(direccion) > 25 else direccion
                total = pedido.get('total', 0)
                items_count = len(pedido.get('items', []))

                item_id = QTableWidgetItem(pedido_id)
                self.tabla_pedidos_aceptados.setItem(fila, 0, item_id)
                self.tabla_pedidos_aceptados.setItem(fila, 1, QTableWidgetItem(hora))
                self.tabla_pedidos_aceptados.setItem(fila, 2, QTableWidgetItem(cliente))
                self.tabla_pedidos_aceptados.setItem(fila, 3, QTableWidgetItem(telefono))
                self.tabla_pedidos_aceptados.setItem(fila, 4, QTableWidgetItem(direccion_corta))
                self.tabla_pedidos_aceptados.setItem(fila, 5, QTableWidgetItem(f"${total:,.2f}".replace(",", ".")))
                self.tabla_pedidos_aceptados.setItem(fila, 6, QTableWidgetItem(str(items_count)))
                
                item_guardado = self.tabla_pedidos_aceptados.item(fila, 0)
                if item_guardado is not None:
                    item_guardado.setData(Qt.ItemDataRole.UserRole, pedido)
            
            # Tabla pedidos rechazados
            self.tabla_pedidos_rechazados.setRowCount(0)
            for pedido in pedidos_rechazados:
                fila = self.tabla_pedidos_rechazados.rowCount()
                self.tabla_pedidos_rechazados.insertRow(fila)
                
                pedido_id = pedido.get('id', 'N/A')[:8]
                hora = pedido.get('hora', 'N/A')
                cliente = pedido.get('cliente', 'N/A')
                telefono = pedido.get('telefono', 'N/A')
                direccion = pedido.get('direccion', 'N/A')
                direccion_corta = direccion[:25] + "..." if len(direccion) > 25 else direccion
                total = pedido.get('total', 0)
                items_count = len(pedido.get('items', []))

                item_id = QTableWidgetItem(pedido_id)
                self.tabla_pedidos_rechazados.setItem(fila, 0, item_id)
                self.tabla_pedidos_rechazados.setItem(fila, 1, QTableWidgetItem(hora))
                self.tabla_pedidos_rechazados.setItem(fila, 2, QTableWidgetItem(cliente))
                self.tabla_pedidos_rechazados.setItem(fila, 3, QTableWidgetItem(telefono))
                self.tabla_pedidos_rechazados.setItem(fila, 4, QTableWidgetItem(direccion_corta))
                self.tabla_pedidos_rechazados.setItem(fila, 5, QTableWidgetItem(f"${total:,.2f}".replace(",", ".")))
                self.tabla_pedidos_rechazados.setItem(fila, 6, QTableWidgetItem(str(items_count)))
                
                item_guardado = self.tabla_pedidos_rechazados.item(fila, 0)
                if item_guardado is not None:
                    item_guardado.setData(Qt.ItemDataRole.UserRole, pedido)
            
            # Tabla consumo
            self.tabla_consumo.setRowCount(0)
            if consumo and "productos" in consumo:
                productos_consumo = consumo["productos"]
                if isinstance(productos_consumo, dict):
                    for producto, datos in productos_consumo.items():
                        fila = self.tabla_consumo.rowCount()
                        self.tabla_consumo.insertRow(fila)
                        
                        cantidad = datos.get('cantidad', 0) if isinstance(datos, dict) else 0
                        precio_unit = datos.get('precio_unitario', 0) if isinstance(datos, dict) else 0
                        valor = datos.get('valor', 0) if isinstance(datos, dict) else 0
                        
                        self.tabla_consumo.setItem(fila, 0, QTableWidgetItem(str(producto)))
                        self.tabla_consumo.setItem(fila, 1, QTableWidgetItem(f"{cantidad:,}".replace(",", ".")))
                        self.tabla_consumo.setItem(fila, 2, QTableWidgetItem(f"${precio_unit:,.2f}".replace(",", ".")))
                        self.tabla_consumo.setItem(fila, 3, QTableWidgetItem(f"${valor:,.2f}".replace(",", ".")))
            
            # Tabla agregados
            self.tabla_agregados.setRowCount(0)
            productos_agregados = consumo.get("productos_agregados", []) if consumo else []
            for producto in productos_agregados:
                if isinstance(producto, dict):
                    fila = self.tabla_agregados.rowCount()
                    self.tabla_agregados.insertRow(fila)
                    
                    nombre = producto.get("nombre", "N/A")
                    cantidad = producto.get("cantidad", 0)
                    precio = producto.get("precio", 0)
                    usuario = producto.get("usuario", "N/A")
                    
                    try:
                        hora = datetime.fromisoformat(producto.get('hora', '')).strftime("%H:%M:%S")
                    except:
                        hora = producto.get('hora', 'N/A')
                    
                    self.tabla_agregados.setItem(fila, 0, QTableWidgetItem(nombre))
                    self.tabla_agregados.setItem(fila, 1, QTableWidgetItem(f"{cantidad:,}".replace(",", ".")))
                    self.tabla_agregados.setItem(fila, 2, QTableWidgetItem(f"${precio:,.2f}".replace(",", ".")))
                    self.tabla_agregados.setItem(fila, 3, QTableWidgetItem(usuario))
                    self.tabla_agregados.setItem(fila, 4, QTableWidgetItem(hora))
            
            # Tabla actividades
            self.tabla_actividades.setRowCount(0)
            if actividades:
                for actividad in reversed(actividades[-50:]):
                    fila = self.tabla_actividades.rowCount()
                    self.tabla_actividades.insertRow(fila)
                    
                    try:
                        timestamp = datetime.fromisoformat(actividad.get("timestamp", ""))
                        hora = timestamp.strftime("%H:%M:%S")
                    except:
                        hora = actividad.get("timestamp", "N/A")
                    
                    detalles = ""
                    if actividad.get("tipo") == "consumo":
                        d = actividad.get("detalles", {})
                        detalles = f"{d.get('producto', 'N/A')}: {d.get('cantidad_consumida', 0)} unidades"
                    elif actividad.get("tipo") == "inventario":
                        d = actividad.get("detalles", {})
                        detalles = f"{d.get('producto', 'N/A')}: {d.get('diferencia', 0):+,} unidades"
                    elif actividad.get("tipo") == "pedido":
                        d = actividad.get("detalles", {})
                        detalles = f"Pedido {d.get('pedido_id', 'N/A')[:8]}: {d.get('accion', 'N/A')}"
                    
                    item_hora = QTableWidgetItem(hora)
                    self.tabla_actividades.setItem(fila, 0, item_hora)
                    self.tabla_actividades.setItem(fila, 1, QTableWidgetItem(actividad.get("usuario", "N/A")))
                    self.tabla_actividades.setItem(fila, 2, QTableWidgetItem(actividad.get("accion", "N/A")))
                    self.tabla_actividades.setItem(fila, 3, QTableWidgetItem(detalles))
                    
                    item_guardado = self.tabla_actividades.item(fila, 0)
                    if item_guardado is not None:
                        item_guardado.setData(Qt.ItemDataRole.UserRole, actividad)
            
        except ValueError:
            QMessageBox.critical(self, "Error", "Formato de fecha inválido. Use YYYY-MM-DD")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar registro: {str(e)}")
            import traceback
            traceback.print_exc()

    def _cargar_pedidos_por_fecha(self, fecha):
        pedidos_aceptados = []
        pedidos_rechazados = []
        try:
            with open('pedidos.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                completados = data.get('completados', [])
                
                for pedido in completados:
                    if pedido.get('fecha') == fecha.strftime("%Y-%m-%d"):
                        if pedido.get('estado') == 'confirmado':
                            pedidos_aceptados.append(pedido)
                        elif pedido.get('estado') == 'rechazado':
                            pedidos_rechazados.append(pedido)
        except:
            pass
        return pedidos_aceptados, pedidos_rechazados

    def menu_contextual_pedidos_aceptados(self, pos):
        tabla = self.tabla_pedidos_aceptados
        if tabla is None:
            return
        
        index = tabla.indexAt(pos)
        if not index.isValid():
            return
        
        fila = index.row()
        if fila < 0:
            return
        
        item = tabla.item(fila, 0)
        if item is None:
            QMessageBox.warning(self, "Advertencia", "No se pudo obtener la información del pedido")
            return
        
        pedido = item.data(Qt.ItemDataRole.UserRole)
        if pedido is None:
            QMessageBox.warning(self, "Advertencia", "No se encontraron datos del pedido")
            return
        
        menu = QMenu()
        ver_action = menu.addAction("🔍 Ver Detalle Completo del Pedido")
        menu.addSeparator()
        copiar_id_action = menu.addAction("📋 Copiar ID del Pedido")
        copiar_cliente_action = menu.addAction("👤 Copiar Nombre del Cliente")
        copiar_telefono_action = menu.addAction("📞 Copiar Teléfono")
        copiar_direccion_action = menu.addAction("📍 Copiar Dirección")
        
        action = menu.exec(tabla.viewport().mapToGlobal(pos))
        
        if action == ver_action:
            self.mostrar_detalle_pedido_completo(pedido)
        elif action == copiar_id_action:
            QApplication.clipboard().setText(pedido.get('id', ''))
            self.status_bar.showMessage("✅ ID del pedido copiado", 2000)
        elif action == copiar_cliente_action:
            QApplication.clipboard().setText(pedido.get('cliente', ''))
            self.status_bar.showMessage("✅ Nombre del cliente copiado", 2000)
        elif action == copiar_telefono_action:
            QApplication.clipboard().setText(pedido.get('telefono', ''))
            self.status_bar.showMessage("✅ Teléfono copiado", 2000)
        elif action == copiar_direccion_action:
            QApplication.clipboard().setText(pedido.get('direccion', ''))
            self.status_bar.showMessage("✅ Dirección copiada", 2000)

    def menu_contextual_pedidos_rechazados(self, pos):
        tabla = self.tabla_pedidos_rechazados
        if tabla is None:
            return
        
        index = tabla.indexAt(pos)
        if not index.isValid():
            return
        
        fila = index.row()
        if fila < 0:
            return
        
        item = tabla.item(fila, 0)
        if item is None:
            QMessageBox.warning(self, "Advertencia", "No se pudo obtener la información del pedido")
            return
        
        pedido = item.data(Qt.ItemDataRole.UserRole)
        if pedido is None:
            QMessageBox.warning(self, "Advertencia", "No se encontraron datos del pedido")
            return
        
        menu = QMenu()
        ver_action = menu.addAction("🔍 Ver Detalle Completo del Pedido")
        menu.addSeparator()
        copiar_id_action = menu.addAction("📋 Copiar ID del Pedido")
        copiar_cliente_action = menu.addAction("👤 Copiar Nombre del Cliente")
        copiar_telefono_action = menu.addAction("📞 Copiar Teléfono")
        copiar_direccion_action = menu.addAction("📍 Copiar Dirección")
        
        action = menu.exec(tabla.viewport().mapToGlobal(pos))
        
        if action == ver_action:
            self.mostrar_detalle_pedido_completo(pedido)
        elif action == copiar_id_action:
            QApplication.clipboard().setText(pedido.get('id', ''))
            self.status_bar.showMessage("✅ ID del pedido copiado", 2000)
        elif action == copiar_cliente_action:
            QApplication.clipboard().setText(pedido.get('cliente', ''))
            self.status_bar.showMessage("✅ Nombre del cliente copiado", 2000)
        elif action == copiar_telefono_action:
            QApplication.clipboard().setText(pedido.get('telefono', ''))
            self.status_bar.showMessage("✅ Teléfono copiado", 2000)
        elif action == copiar_direccion_action:
            QApplication.clipboard().setText(pedido.get('direccion', ''))
            self.status_bar.showMessage("✅ Dirección copiada", 2000)

    def menu_contextual_actividades(self, pos):
        tabla = self.tabla_actividades
        if tabla is None:
            return
        
        index = tabla.indexAt(pos)
        if not index.isValid():
            return
        
        fila = index.row()
        if fila < 0:
            return
        
        item = tabla.item(fila, 0)
        if item is None:
            return
        
        actividad = item.data(Qt.ItemDataRole.UserRole)
        if actividad is None:
            QMessageBox.warning(self, "Advertencia", "No se encontraron datos de la actividad")
            return
        
        menu = QMenu()
        ver_action = menu.addAction("🔍 Ver Detalles Completos")
        menu.addSeparator()
        copiar_info_action = menu.addAction("📋 Copiar Información")
        copiar_json_action = menu.addAction("📋 Copiar JSON")
        
        action = menu.exec(tabla.viewport().mapToGlobal(pos))
        
        if action == ver_action:
            self.mostrar_detalle_actividad(actividad)
        elif action == copiar_info_action:
            self._copiar_actividad_completa(actividad)
        elif action == copiar_json_action:
            try:
                json_texto = json.dumps(actividad, indent=2, ensure_ascii=False, default=str)
                QApplication.clipboard().setText(json_texto)
                self.status_bar.showMessage("✅ JSON copiado al portapapeles", 2000)
            except:
                QApplication.clipboard().setText(str(actividad))
                self.status_bar.showMessage("✅ Datos copiados al portapapeles", 2000)

    def mostrar_detalle_pedido_completo(self, pedido):
        if not pedido:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalle Completo - Pedido #{pedido.get('id', '')[:8]}")
        dialog.setMinimumSize(650, 550)
        
        layout = QVBoxLayout(dialog)
        
        info_group = QGroupBox("📋 Información General")
        info_layout = QFormLayout(info_group)
        
        info_layout.addRow("ID:", QLabel(pedido.get('id', 'N/A')))
        estado = pedido.get('estado', 'N/A').upper()
        estado_label = QLabel(estado)
        if estado == 'CONFIRMADO':
            estado_label.setStyleSheet("color: green; font-weight: bold;")
        elif estado == 'RECHAZADO':
            estado_label.setStyleSheet("color: red; font-weight: bold;")
        info_layout.addRow("Estado:", estado_label)
        info_layout.addRow("Fecha:", QLabel(pedido.get('fecha', 'N/A')))
        info_layout.addRow("Hora:", QLabel(pedido.get('hora', 'N/A')))
        
        layout.addWidget(info_group)
        
        cliente_group = QGroupBox("👤 Datos del Cliente")
        cliente_layout = QFormLayout(cliente_group)
        
        cliente_layout.addRow("Nombre:", QLabel(pedido.get('cliente', 'N/A')))
        cliente_layout.addRow("Teléfono:", QLabel(pedido.get('telefono', 'N/A')))
        cliente_layout.addRow("Dirección:", QLabel(pedido.get('direccion', 'N/A')))
        
        if pedido.get('notas'):
            cliente_layout.addRow("Notas:", QLabel(pedido.get('notas', '')))
        
        layout.addWidget(cliente_group)
        
        items_group = QGroupBox("🛒 Productos del Pedido")
        items_layout = QVBoxLayout(items_group)
        
        items_tabla = QTableWidget()
        items_tabla.setColumnCount(4)
        items_tabla.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio Unit.", "Subtotal"])
        items_tabla.horizontalHeader().setStretchLastSection(True)
        items_tabla.setAlternatingRowColors(True)
        
        items = pedido.get('items', [])
        items_tabla.setRowCount(len(items))
        
        for i, item in enumerate(items):
            nombre = item.get('nombre', 'N/A')
            cantidad = item.get('cantidad', 0)
            precio_unit = item.get('precio_unitario', 0)
            subtotal = item.get('subtotal', precio_unit * cantidad)
            
            items_tabla.setItem(i, 0, QTableWidgetItem(nombre))
            items_tabla.setItem(i, 1, QTableWidgetItem(str(cantidad)))
            items_tabla.setItem(i, 2, QTableWidgetItem(f"${precio_unit:,.2f}".replace(",", ".")))
            items_tabla.setItem(i, 3, QTableWidgetItem(f"${subtotal:,.2f}".replace(",", ".")))
        
        items_layout.addWidget(items_tabla)
        
        total_layout = QHBoxLayout()
        total_layout.addStretch()
        total_label = QLabel(f"TOTAL: ${pedido.get('total', 0):,.2f}".replace(",", "."))
        total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ed573;")
        total_layout.addWidget(total_label)
        items_layout.addLayout(total_layout)
        
        layout.addWidget(items_group)
        
        if pedido.get('metodo_pago') or pedido.get('horario_entrega'):
            extra_group = QGroupBox("📌 Información Adicional")
            extra_layout = QFormLayout(extra_group)
            
            if pedido.get('metodo_pago'):
                extra_layout.addRow("Método de pago:", QLabel(pedido.get('metodo_pago', 'N/A')))
            if pedido.get('horario_entrega'):
                extra_layout.addRow("Horario preferido:", QLabel(pedido.get('horario_entrega', 'N/A')))
            
            layout.addWidget(extra_group)
        
        buttons = QHBoxLayout()
        
        btn_copiar_todo = QPushButton("📋 Copiar Todo")
        btn_copiar_todo.clicked.connect(lambda: self._copiar_pedido_completo(pedido))
        buttons.addWidget(btn_copiar_todo)
        
        buttons.addStretch()
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.accept)
        buttons.addWidget(btn_cerrar)
        
        layout.addLayout(buttons)
        
        dialog.exec()

    def _copiar_pedido_completo(self, pedido):
        texto = f"""
═══════════════════════════════════════════════════════════
                    DETALLE DE PEDIDO
═══════════════════════════════════════════════════════════

📋 INFORMACIÓN GENERAL
   ID: {pedido.get('id', 'N/A')}
   Estado: {pedido.get('estado', 'N/A').upper()}
   Fecha: {pedido.get('fecha', 'N/A')}
   Hora: {pedido.get('hora', 'N/A')}

👤 DATOS DEL CLIENTE
   Nombre: {pedido.get('cliente', 'N/A')}
   Teléfono: {pedido.get('telefono', 'N/A')}
   Dirección: {pedido.get('direccion', 'N/A')}"""
        
        if pedido.get('notas'):
            texto += f"\n   Notas: {pedido.get('notas', '')}"
        
        texto += "\n\n🛒 PRODUCTOS\n"
        for item in pedido.get('items', []):
            texto += f"   • {item.get('cantidad', 0)}x {item.get('nombre', 'N/A')} - ${item.get('subtotal', 0):,.2f}\n".replace(",", ".")
        
        texto += f"\n   TOTAL: ${pedido.get('total', 0):,.2f}\n".replace(",", ".")
        texto += "\n═══════════════════════════════════════════════════════════"
        
        QApplication.clipboard().setText(texto)
        QMessageBox.information(self, "Copiado", "Información completa copiada al portapapeles")

    def mostrar_detalle_actividad(self, actividad):
        if not actividad:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Detalle de Actividad")
        dialog.setMinimumSize(550, 450)
        
        layout = QVBoxLayout(dialog)
        
        info_group = QGroupBox("📋 Información de la Actividad")
        info_layout = QFormLayout(info_group)
        
        try:
            timestamp = datetime.fromisoformat(actividad.get("timestamp", ""))
            fecha_hora = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except:
            fecha_hora = actividad.get("timestamp", "N/A")
        
        info_layout.addRow("Fecha y Hora:", QLabel(fecha_hora))
        info_layout.addRow("Usuario:", QLabel(actividad.get("usuario", "N/A")))
        info_layout.addRow("Tipo:", QLabel(actividad.get("tipo", "N/A").upper()))
        info_layout.addRow("Acción:", QLabel(actividad.get("accion", "N/A")))
        
        layout.addWidget(info_group)
        
        detalles_group = QGroupBox("📝 Detalles")
        detalles_layout = QVBoxLayout(detalles_group)
        
        text_detalles = QTextEdit()
        text_detalles.setReadOnly(True)
        
        detalles = actividad.get("detalles", {})
        texto_detalles = ""
        
        if isinstance(detalles, dict):
            for clave, valor in detalles.items():
                if isinstance(valor, (int, float)):
                    if "precio" in clave.lower() or "total" in clave.lower() or "valor" in clave.lower():
                        valor = f"${valor:,.2f}".replace(",", ".")
                    elif "cantidad" in clave.lower():
                        valor = f"{valor:,}".replace(",", ".")
                texto_detalles += f"• {clave.replace('_', ' ').title()}: {valor}\n"
        else:
            texto_detalles = str(detalles)
        
        if not texto_detalles:
            texto_detalles = "No hay detalles adicionales disponibles."
        
        text_detalles.setText(texto_detalles)
        detalles_layout.addWidget(text_detalles)
        
        layout.addWidget(detalles_group)
        
        json_group = QGroupBox("🗂️ Datos Completos (JSON)")
        json_layout = QVBoxLayout(json_group)
        
        text_json = QTextEdit()
        text_json.setReadOnly(True)
        text_json.setMaximumHeight(150)
        text_json.setFont(QFont("Consolas", 9))
        
        try:
            json_texto = json.dumps(actividad, indent=2, ensure_ascii=False, default=str)
            text_json.setText(json_texto)
        except:
            text_json.setText(str(actividad))
        
        json_layout.addWidget(text_json)
        
        layout.addWidget(json_group)
        
        buttons = QHBoxLayout()
        
        btn_copiar = QPushButton("📋 Copiar Todo")
        btn_copiar.clicked.connect(lambda: self._copiar_actividad_completa(actividad))
        buttons.addWidget(btn_copiar)
        
        btn_copiar_json = QPushButton("📋 Copiar JSON")
        btn_copiar_json.clicked.connect(lambda: QApplication.clipboard().setText(text_json.toPlainText()))
        buttons.addWidget(btn_copiar_json)
        
        buttons.addStretch()
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.accept)
        buttons.addWidget(btn_cerrar)
        
        layout.addLayout(buttons)
        
        dialog.exec()

    def _copiar_actividad_completa(self, actividad):
        try:
            timestamp = datetime.fromisoformat(actividad.get("timestamp", ""))
            fecha_hora = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except:
            fecha_hora = actividad.get("timestamp", "N/A")
        
        texto = f"""
═══════════════════════════════════════════════════════════
                    DETALLE DE ACTIVIDAD
═══════════════════════════════════════════════════════════

📋 INFORMACIÓN GENERAL
   Fecha y Hora: {fecha_hora}
   Usuario: {actividad.get('usuario', 'N/A')}
   Tipo: {actividad.get('tipo', 'N/A').upper()}
   Acción: {actividad.get('accion', 'N/A')}

📝 DETALLES
"""
        
        detalles = actividad.get("detalles", {})
        if isinstance(detalles, dict):
            for clave, valor in detalles.items():
                if isinstance(valor, (int, float)):
                    if "precio" in clave.lower() or "total" in clave.lower():
                        valor = f"${valor:,.2f}".replace(",", ".")
                    elif "cantidad" in clave.lower():
                        valor = f"{valor:,}".replace(",", ".")
                texto += f"   • {clave.replace('_', ' ').title()}: {valor}\n"
        else:
            texto += f"   {detalles}\n"
        
        texto += "\n═══════════════════════════════════════════════════════════"
        
        QApplication.clipboard().setText(texto)
        self.status_bar.showMessage("✅ Información copiada al portapapeles", 2000)

    def detener_ngrok(self):
        """Detener el proceso de ngrok"""
        import subprocess
        
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], 
                            capture_output=True)
            else:
                subprocess.run(["pkill", "ngrok"], capture_output=True)
            
            QMessageBox.information(self, "✅ ngrok detenido",
                "ngrok ha sido detenido.\n"
                "La página web ya no está disponible públicamente.")
            
            self.actualizar_info_api()
        except Exception as e:
            QMessageBox.warning(self, "⚠️ Advertencia",
                f"No se pudo detener ngrok automáticamente.\n"
                f"Puedes detenerlo manualmente con Ctrl+C en la terminal.\n\n"
                f"Error: {str(e)}")


    def verificar_estado_ngrok(self):
        """Verificar si ngrok está ejecutándose"""
        import subprocess
        
        try:
            if sys.platform == "win32":
                result = subprocess.run(["tasklist"], capture_output=True, text=True)
                return "ngrok.exe" in result.stdout
            else:
                result = subprocess.run(["pgrep", "ngrok"], capture_output=True)
                return result.returncode == 0
        except:
            return False

    def toggle_ngrok(self):
        """Alternar entre iniciar y detener ngrok"""
        if self.verificar_estado_ngrok():
            # Si está activo, preguntar si quiere detener
            reply = QMessageBox.question(self, "Detener ngrok",
                "¿Estás seguro de que deseas detener ngrok?\n\n"
                "La página web dejará de estar disponible públicamente.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.detener_ngrok()
        else:
            # Si no está activo, iniciar
            self.iniciar_ngrok_automatico()

    def abrir_pagina_web(self):
        """Abrir la página web en el navegador"""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        
        url_ngrok = self.obtener_url_ngrok()
        
        if url_ngrok:
            QDesktopServices.openUrl(QUrl(url_ngrok))
            QMessageBox.information(self, "🌐 Página web abierta",
                f"Abriendo página web en tu navegador:\n{url_ngrok}")
        else:
            QDesktopServices.openUrl(QUrl("http://localhost:8081"))
            QMessageBox.information(self, "🌐 Página web local",
                "Abriendo página web en modo local:\nhttp://localhost:8081\n\n"
                "Para hacerla pública, inicia ngrok.")

    # ========== PESTAÑA CONFIGURACIÓN ==========

    def crear_pestana_configuracion(self):
        """Crear pestaña de configuración"""
        widget = QWidget()
        layout = QVBoxLayout()  # ← Este es el layout principal
        widget.setLayout(layout)
        
        # Grupo de API y ngrok
        grupo_api = QGroupBox("🌐 Configuración de API y Página Web")
        layout_api = QVBoxLayout()  # ← Layout para este grupo
        grupo_api.setLayout(layout_api)
        
        # Información de la API
        self.text_info_api = QTextEdit()
        self.text_info_api.setReadOnly(True)
        self.text_info_api.setMaximumHeight(200)
        layout_api.addWidget(self.text_info_api)
        
        # Botones de ngrok
        botones_ngrok_layout = QHBoxLayout()
        
        self.btn_toggle_ngrok = QPushButton("🚀 Iniciar ngrok (Publicar página web)")
        self.btn_toggle_ngrok.clicked.connect(self.toggle_ngrok)
        botones_ngrok_layout.addWidget(self.btn_toggle_ngrok)
        
        btn_actualizar_script = QPushButton("🔄 Actualizar script.js automáticamente")
        btn_actualizar_script.clicked.connect(self.actualizar_script_js_automatico)
        layout_api.addWidget(btn_actualizar_script)
        
        btn_refrescar = QPushButton("🔄 Refrescar estado")
        btn_refrescar.clicked.connect(self.actualizar_info_api)
        botones_ngrok_layout.addWidget(btn_refrescar)
        
        layout_api.addLayout(botones_ngrok_layout)
        
        # Nuevos botones para la página web
        botones_web_layout = QHBoxLayout()
        
        btn_copiar_url_web = QPushButton("📱 Copiar URL de página web")
        btn_copiar_url_web.clicked.connect(self.copiar_url_pagina_web)
        botones_web_layout.addWidget(btn_copiar_url_web)
        
        btn_abrir_web = QPushButton("🌐 Abrir página web")
        btn_abrir_web.clicked.connect(self.abrir_pagina_web)
        botones_web_layout.addWidget(btn_abrir_web)
        
        layout_api.addLayout(botones_web_layout)
        
        # Agregar el grupo al layout principal
        layout.addWidget(grupo_api)
        
        # Grupo de configuración de impresora
        grupo_impresora = QGroupBox("🖨️ Configuración de Impresora")
        layout_impresora = QFormLayout()
        grupo_impresora.setLayout(layout_impresora)
        
        self.entry_impresora = QLineEdit()
        self.entry_impresora.setPlaceholderText("Ej: POS-80, EPSON-TM-T20")
        layout_impresora.addRow("Nombre de impresora:", self.entry_impresora)
        
        btn_guardar_impresora = QPushButton("💾 Guardar configuración")
        btn_guardar_impresora.clicked.connect(self.guardar_configuracion_impresora)
        layout_impresora.addRow(btn_guardar_impresora)
        
        layout.addWidget(grupo_impresora)
        
        # Agregar espacio flexible al final
        layout.addStretch()
        
        # Actualizar info de API
        self.actualizar_info_api()
        
        # Agregar la pestaña
        self.tab_widget.addTab(widget, "⚙️ Configuración")        
    # ========== MÉTODOS DE AUTENTICACIÓN ==========
    
    def cambiar_password(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Cambiar Contraseña")
        dialog.setFixedSize(350, 220)
        
        layout = QFormLayout(dialog)
        
        entry_actual = QLineEdit()
        entry_actual.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Contraseña actual:", entry_actual)
        
        entry_nueva = QLineEdit()
        entry_nueva.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Nueva contraseña:", entry_nueva)
        
        entry_confirmar = QLineEdit()
        entry_confirmar.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Confirmar nueva contraseña:", entry_confirmar)
        
        btn_cambiar = QPushButton("Cambiar Contraseña")
        layout.addRow(btn_cambiar)
        
        def cambiar():
            actual = entry_actual.text()
            nueva = entry_nueva.text()
            confirmar = entry_confirmar.text()
            
            if not all([actual, nueva, confirmar]):
                QMessageBox.critical(dialog, "Error", "Todos los campos son requeridos")
                return
                
            if nueva != confirmar:
                QMessageBox.critical(dialog, "Error", "Las contraseñas no coinciden")
                return
                
            if len(nueva) < 6:
                QMessageBox.critical(dialog, "Error", "La contraseña debe tener al menos 6 caracteres")
                return
                
            if self.auth.cambiar_password(actual, nueva):
                QMessageBox.information(dialog, "Éxito", "Contraseña cambiada correctamente")
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "Error", "Contraseña actual incorrecta")
                
        btn_cambiar.clicked.connect(cambiar)
        dialog.exec()
        
    def cerrar_sesion(self):
        reply = QMessageBox.question(self, "Confirmar", "¿Cerrar sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if reply == QMessageBox.StandardButton.Yes:
            self.auth.logout()
            self.login_window = VentanaLogin()
            self.login_window.show()
            self.close()

    # ========== MÉTODOS DE REPORTES ==========
            
    def generar_reporte_diario(self):
        consumo = self.registro.obtener_consumo_diario()
        
        reporte = f"REPORTE DIARIO - {consumo['fecha']}\n"
        reporte += "=" * 50 + "\n\n"
        reporte += f"Total unidades consumidas: {consumo['total_unidades']:,}\n".replace(",", ".")
        reporte += f"Valor total: ${consumo['valor_total']:,.2f}\n\n".replace(",", ".")
        reporte += "PRODUCTOS CONSUMIDOS:\n"
        reporte += "-" * 40 + "\n"
        
        for producto, datos in consumo["productos"].items():
            reporte += f"{producto}: {datos['cantidad']:,} unidades - ${datos['valor']:,.2f}\n".replace(",", ".")
            
        QMessageBox.information(self, "Reporte Diario", reporte)
        
    def generar_reporte_semanal(self):
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=7)
        
        resumen = self.registro.obtener_resumen_periodo(fecha_inicio, fecha_fin)
        
        reporte = f"REPORTE SEMANAL - {resumen['periodo']}\n"
        reporte += "=" * 50 + "\n\n"
        reporte += f"Total actividades: {resumen['total_actividades']}\n"
        reporte += f"Consumo total: ${resumen['consumo_total']:,.2f}\n".replace(",", ".")
        reporte += f"Usuarios activos: {len(resumen['usuarios_activos'])}\n\n"
        reporte += "PRODUCTOS MÁS CONSUMIDOS:\n"
        reporte += "-" * 40 + "\n"
        
        productos_ordenados = sorted(
            resumen["productos_mas_consumidos"].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        for producto, cantidad in productos_ordenados[:10]:
            reporte += f"{producto}: {cantidad:,} unidades\n".replace(",", ".")
            
        QMessageBox.information(self, "Reporte Semanal", reporte)

    # ========== MÉTODOS DE BACKUP ==========
    
    def crear_backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup_{timestamp}"
        
        try:
            os.makedirs(backup_dir)
            
            archivos = ["productos.json", "usuarios.json", "categorias.json", "categorias_materia.json", 
                       "pedidos.json", "pedidos_web.json", "materia_prima.json", "config.json"]
            
            for archivo in archivos:
                if os.path.exists(archivo):
                    shutil.copy2(archivo, backup_dir)
                    
            if os.path.exists("logs"):
                shutil.copytree("logs", os.path.join(backup_dir, "logs"))
                
            self.registro.registrar_actividad(
                self.auth.usuario_actual,
                "backup",
                {"backup_dir": backup_dir}
            )
            
            QMessageBox.information(self, "Éxito", f"Backup creado en:\n{backup_dir}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear backup: {str(e)}")
            
    def importar_backup(self):
        backup_dir = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de backup")
        
        if not backup_dir:
            return
            
        reply = QMessageBox.question(
            self, 
            "Confirmar",
            "¿Importar backup? Los datos existentes se combinarán (no se borrará nada).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
            
        if reply == QMessageBox.StandardButton.No:
            return
            
        try:
            productos_actuales = self.inventario.productos.copy()
            
            backup_productos_path = os.path.join(backup_dir, "productos.json")
            if os.path.exists(backup_productos_path):
                with open(backup_productos_path, 'r', encoding='utf-8') as f:
                    productos_backup = json.load(f)
                    
                for nombre, datos in productos_backup.items():
                    if nombre not in productos_actuales:
                        productos_actuales[nombre] = datos
                        
                self.inventario.productos = productos_actuales
                self.inventario.guardar_inventario()
                
            backup_categorias_path = os.path.join(backup_dir, "categorias.json")
            if os.path.exists(backup_categorias_path):
                with open(backup_categorias_path, 'r', encoding='utf-8') as f:
                    categorias_backup = json.load(f)
                    
                for cat in categorias_backup:
                    if cat not in self.categorias:
                        self.categorias.append(cat)
                        
                self.guardar_categorias()
                
            backup_categorias_mat_path = os.path.join(backup_dir, "categorias_materia.json")
            if os.path.exists(backup_categorias_mat_path):
                with open(backup_categorias_mat_path, 'r', encoding='utf-8') as f:
                    categorias_mat_backup = json.load(f)
                    
                for cat in categorias_mat_backup:
                    if cat not in self.categorias_materia:
                        self.categorias_materia.append(cat)
                        
                self.guardar_categorias_materia_prima(self.categorias_materia)
                
            self.actualizar_inventario_display()
            self.actualizar_lista_categorias_inventario()
            self.actualizar_lista_categorias_materia()
            self.actualizar_combos_categorias()
            
            self.registro.registrar_actividad(
                self.auth.usuario_actual,
                "importar_backup",
                {"backup_dir": backup_dir}
            )
            
            QMessageBox.information(self, "Éxito", "Backup importado correctamente")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo importar backup: {str(e)}")

    # ========== GESTIÓN DE USUARIOS ==========
    
    def gestionar_usuarios(self):
        if not self.auth.es_admin:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Gestión de Usuarios")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        tabla = QTableWidget()
        tabla.setColumnCount(4)
        tabla.setHorizontalHeaderLabels(["Usuario", "Nombre Completo", "Rol", "Fecha Creación"])
        tabla.setAlternatingRowColors(True)
        tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        def cargar_usuarios():
            tabla.setRowCount(0)
            usuarios = self.auth.obtener_usuarios()
            for usuario, datos in usuarios.items():
                fila = tabla.rowCount()
                tabla.insertRow(fila)
                tabla.setItem(fila, 0, QTableWidgetItem(usuario))
                tabla.setItem(fila, 1, QTableWidgetItem(datos["nombre_completo"]))
                tabla.setItem(fila, 2, QTableWidgetItem(datos["rol"]))
                tabla.setItem(fila, 3, QTableWidgetItem(datos["fecha_creacion"][:10]))
                
        cargar_usuarios()
        layout.addWidget(tabla)
        
        agregar_group = QGroupBox("Agregar Nuevo Usuario")
        agregar_layout = QFormLayout(agregar_group)
        
        entry_usuario = QLineEdit()
        agregar_layout.addRow("Usuario:", entry_usuario)
        
        entry_nombre = QLineEdit()
        agregar_layout.addRow("Nombre:", entry_nombre)
        
        entry_password = QLineEdit()
        entry_password.setEchoMode(QLineEdit.EchoMode.Password)
        agregar_layout.addRow("Password:", entry_password)
        
        combo_rol = QComboBox()
        combo_rol.addItems(["admin", "usuario"])
        agregar_layout.addRow("Rol:", combo_rol)
        
        btn_agregar = QPushButton("Agregar Usuario")
        agregar_layout.addRow(btn_agregar)
        
        layout.addWidget(agregar_group)
        
        btn_eliminar = QPushButton("Eliminar Usuario Seleccionado")
        layout.addWidget(btn_eliminar)
        
        def agregar_usuario():
            usuario = entry_usuario.text().strip()
            nombre = entry_nombre.text().strip()
            password = entry_password.text()
            rol = combo_rol.currentText()
            
            if not all([usuario, nombre, password]):
                QMessageBox.critical(dialog, "Error", "Todos los campos son requeridos")
                return
                
            if len(password) < 6:
                QMessageBox.critical(dialog, "Error", "La contraseña debe tener al menos 6 caracteres")
                return
                
            if self.auth.crear_usuario(usuario, password, rol, nombre):
                QMessageBox.information(dialog, "Éxito", "Usuario creado correctamente")
                cargar_usuarios()
                entry_usuario.clear()
                entry_nombre.clear()
                entry_password.clear()
            else:
                QMessageBox.critical(dialog, "Error", "El usuario ya existe")
                
        btn_agregar.clicked.connect(agregar_usuario)
        
        def eliminar_usuario():
            fila = tabla.currentRow()
            if fila < 0:
                QMessageBox.warning(dialog, "Advertencia", "Seleccione un usuario")
                return
                
            item = tabla.item(fila, 0)
            if item is None:
                QMessageBox.warning(dialog, "Advertencia", "No se pudo obtener el usuario")
                return
                
            usuario = item.text()
            
            if usuario == "admin":
                QMessageBox.critical(dialog, "Error", "No se puede eliminar al usuario admin")
                return
                
            reply = QMessageBox.question(
                dialog, 
                "Confirmar", 
                f"¿Eliminar usuario '{usuario}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
                
            if reply == QMessageBox.StandardButton.Yes:
                if self.auth.eliminar_usuario(usuario):
                    cargar_usuarios()
                    QMessageBox.information(dialog, "Éxito", "Usuario eliminado")
                    
        btn_eliminar.clicked.connect(eliminar_usuario)
        
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    login = VentanaLogin()
    login.show()
    
    sys.exit(app.exec())