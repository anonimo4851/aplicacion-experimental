import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class Inventario:
    def __init__(self, archivo='productos.json'):
        self.archivo = archivo
        self.productos = self.cargar_inventario()
        self.historial = []



    def cargar_inventario(self) -> Dict:
        """Carga el inventario desde el archivo JSON"""
        if os.path.exists(self.archivo):
            try:
                with open(self.archivo, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
        
    def guardar_inventario(self):
        """Guarda el inventario en el archivo JSON"""
        try:
            with open(self.archivo, 'w', encoding='utf-8') as f:
                json.dump(self.productos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar inventario: {e}")
            
    def agregar_producto(self, nombre: str, categoria: str, precio: float, cantidad: int):
        """Agrega un producto o actualiza su cantidad si ya existe"""
        if not nombre or not categoria:
            raise ValueError("Nombre y categoría son requeridos")
            
        if precio < 0 or cantidad < 0:
            raise ValueError("Precio y cantidad deben ser positivos")
            
        if nombre in self.productos:
            self.productos[nombre]['cantidad'] += cantidad
            self.productos[nombre]['precio'] = precio
            self.productos[nombre]['categoria'] = categoria
        else:
            self.productos[nombre] = {
                'nombre': nombre,
                'categoria': categoria,
                'precio': precio,
                'cantidad': cantidad,
                'fecha_creacion': datetime.now().isoformat()
            }
        self.guardar_inventario()
        
    def modificar_producto(self, nombre_actual: str, nuevo_nombre: str, 
                          nueva_categoria: str, nuevo_precio: float):
        """Modifica completamente un producto"""
        if nombre_actual not in self.productos:
            return False
            
        producto = self.productos[nombre_actual]
        
        # Si cambia el nombre, crear nueva entrada y eliminar la anterior
        if nombre_actual != nuevo_nombre:
            self.productos[nuevo_nombre] = {
                'nombre': nuevo_nombre,
                'categoria': nueva_categoria,
                'precio': nuevo_precio,
                'cantidad': producto['cantidad'],
                'fecha_creacion': producto.get('fecha_creacion', datetime.now().isoformat())
            }
            del self.productos[nombre_actual]
        else:
            producto['categoria'] = nueva_categoria
            producto['precio'] = nuevo_precio
            
        self.guardar_inventario()
        return True
        
    def ajustar_stock(self, nombre: str, nueva_cantidad: int):
        """Ajusta el stock a una cantidad específica"""
        if nombre in self.productos and nueva_cantidad >= 0:
            self.productos[nombre]['cantidad'] = nueva_cantidad
            self.guardar_inventario()
            return True
        return False
        
    def agregar_stock(self, nombre: str, cantidad: int) -> bool:
        """Agrega stock a un producto existente"""
        if nombre in self.productos and cantidad > 0:
            self.productos[nombre]['cantidad'] += cantidad
            self.guardar_inventario()
            return True
        return False
        
    def quitar_producto(self, nombre: str, cantidad: int) -> bool:
        """Quita una cantidad específica de un producto"""
        if cantidad <= 0:
            return False
        
        if nombre not in self.productos:
            return False
        
        if self.productos[nombre]['cantidad'] >= cantidad:
            self.productos[nombre]['cantidad'] -= cantidad
        # ELIMINADO: Ya no se borra el producto cuando llega a 0
            self.guardar_inventario()
            return True
        return False
        
    def eliminar_producto_completo(self, nombre: str) -> bool:
        """Elimina completamente un producto del inventario"""
        if nombre in self.productos:
            del self.productos[nombre]
            self.guardar_inventario()
            return True
        return False
        
    def obtener_producto(self, nombre: str) -> Optional[Dict]:
        """Obtiene un producto por su nombre"""
        producto = self.productos.get(nombre)
        return producto.copy() if producto else None
        
    def obtener_todos_productos(self) -> List[Dict]:
        """Obtiene todos los productos del inventario"""
        return [producto.copy() for producto in self.productos.values()]
        
    def verificar_disponibilidad(self, nombre: str, cantidad: int) -> bool:
        """Verifica si hay suficiente cantidad de un producto"""
        producto = self.obtener_producto(nombre)
        return producto is not None and producto['cantidad'] >= cantidad
        
    def actualizar_categoria_productos(self, categoria_antigua: str, categoria_nueva: str):
        """Actualiza la categoría en todos los productos que la tengan"""
        for producto in self.productos.values():
            if producto['categoria'] == categoria_antigua:
                producto['categoria'] = categoria_nueva
        self.guardar_inventario()
        
    def eliminar_categoria_de_productos(self, categoria: str):
        """Elimina la categoría de los productos (la deja vacía)"""
        for producto in self.productos.values():
            if producto['categoria'] == categoria:
                producto['categoria'] = "Sin categoría"
        self.guardar_inventario()
        
    def obtener_productos_por_categoria(self, categoria: str) -> List[Dict]:
        """Retorna productos de una categoría específica"""
        return [p.copy() for p in self.productos.values() if p['categoria'] == categoria]
        
    def obtener_estadisticas_por_categoria(self) -> Dict:
        """Retorna estadísticas agrupadas por categoría"""
        stats = {}
        
        for producto in self.productos.values():
            cat = producto['categoria']
            if cat not in stats:
                stats[cat] = {
                    'cantidad_productos': 0,
                    'total_unidades': 0,
                    'valor_total': 0
                }
            
            stats[cat]['cantidad_productos'] += 1
            stats[cat]['total_unidades'] += producto['cantidad']
            stats[cat]['valor_total'] += producto['precio'] * producto['cantidad']
            
        return stats