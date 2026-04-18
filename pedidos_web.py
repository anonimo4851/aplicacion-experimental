# pedidos_web.py - Solo lógica de gestión de pedidos (sin servidor HTTP)
import json
import uuid
from datetime import datetime


class ServidorPedidos:
    """Gestor de pedidos (sin servidor HTTP)"""
    
    def __init__(self, inventario, app=None):
        self.inventario = inventario
        self.app = app
        self.pedidos = []
        self.pedidos_pendientes = []
        self.cargar_pedidos()
    
    def cargar_pedidos(self):
        """Cargar pedidos desde archivo"""
        try:
            with open('pedidos.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.pedidos = data.get('completados', [])
                self.pedidos_pendientes = data.get('pendientes', [])
        except:
            pass
    
    def guardar_pedidos(self):
        """Guardar pedidos a archivo"""
        with open('pedidos.json', 'w', encoding='utf-8') as f:
            json.dump({
                'completados': self.pedidos,
                'pendientes': self.pedidos_pendientes
            }, f, indent=2, ensure_ascii=False)
    
    def procesar_pedido(self, datos):
        """Procesar un nuevo pedido desde la API"""
        pedido = {
            'id': str(uuid.uuid4()),
            'cliente': datos.get('cliente', 'N/A'),
            'telefono': datos.get('telefono', 'N/A'),
            'direccion': datos.get('direccion', 'N/A'),
            'notas': datos.get('notas', ''),
            'items': [],
            'total': 0,
            'hora': datetime.now().strftime('%H:%M'),
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'estado': 'pendiente'
        }
        
        total = 0
        for item in datos.get('items', []):
            nombre = item.get('nombre', 'N/A')
            cantidad = item.get('cantidad', 0)
            
            # Obtener precio del inventario
            producto = self.inventario.obtener_producto(nombre)
            precio = producto.get('precio', 0) if producto else item.get('precio', 0)
            
            subtotal = precio * cantidad
            total += subtotal
            
            pedido['items'].append({
                'nombre': nombre,
                'cantidad': cantidad,
                'precio_unitario': precio,
                'subtotal': subtotal
            })
        
        pedido['total'] = total
        self.pedidos_pendientes.append(pedido)
        self.guardar_pedidos()
        
        # Notificar a la aplicación principal
        if self.app and hasattr(self.app, 'actualizar_pedidos_display'):
            self.app.actualizar_pedidos_display()
        
        return pedido
    
    def confirmar_pedido(self, pedido_id):
        """Confirmar un pedido pendiente"""
        for pedido in self.pedidos_pendientes:
            if pedido['id'] == pedido_id or pedido['id'].startswith(pedido_id):
                # Descontar del inventario
                for item in pedido['items']:
                    self.inventario.quitar_producto(item['nombre'], item['cantidad'])
                
                pedido['estado'] = 'confirmado'
                self.pedidos.append(pedido)
                self.pedidos_pendientes.remove(pedido)
                self.guardar_pedidos()
                return True
        return False
    
    def rechazar_pedido(self, pedido_id):
        """Rechazar un pedido pendiente"""
        for pedido in self.pedidos_pendientes:
            if pedido['id'] == pedido_id or pedido['id'].startswith(pedido_id):
                pedido['estado'] = 'rechazado'
                self.pedidos.append(pedido)
                self.pedidos_pendientes.remove(pedido)
                self.guardar_pedidos()
                return True
        return False
    
    def obtener_pedidos_pendientes(self):
        """Obtener lista de pedidos pendientes"""
        return self.pedidos_pendientes
    
    def obtener_pedido(self, pedido_id):
        """Obtener un pedido por ID"""
        for pedido in self.pedidos_pendientes:
            if pedido['id'] == pedido_id or pedido['id'].startswith(pedido_id):
                return pedido
        for pedido in self.pedidos:
            if pedido['id'] == pedido_id or pedido['id'].startswith(pedido_id):
                return pedido
        return None
    
    def verificar_disponibilidad(self, nombre, cantidad):
        """Verificar si hay stock suficiente"""
        return self.inventario.verificar_disponibilidad(nombre, cantidad)