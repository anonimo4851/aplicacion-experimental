# materia_prima.py - Gestión de Materia Prima e Ingredientes
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class MateriaPrima:
    """Gestor de materia prima e ingredientes"""
    
    def __init__(self, archivo="materia_prima.json"):
        self.archivo = archivo
        self.materia_prima = {}  # {"nombre": {"categoria": "...", "stock": 0, "unidad": "...", "costo": 0, "stock_minimo": 0}}
        self.recetas = {}  # {"producto": [{"ingrediente": "...", "cantidad": 0, "unidad": "..."}]}
        self.movimientos = []  # Historial de movimientos
        self.cargar_datos()
    
    def cargar_datos(self):
        """Cargar datos desde archivo"""
        try:
            with open(self.archivo, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.materia_prima = data.get('materia_prima', {})
                self.recetas = data.get('recetas', {})
                self.movimientos = data.get('movimientos', [])
        except FileNotFoundError:
            print(f"ℹ️ Archivo {self.archivo} no encontrado, creando nuevo")
        except Exception as e:
            print(f"⚠️ Error cargando materia prima: {e}")
    
    def guardar_datos(self):
        """Guardar datos a archivo"""
        try:
            with open(self.archivo, 'w', encoding='utf-8') as f:
                json.dump({
                    'materia_prima': self.materia_prima,
                    'recetas': self.recetas,
                    'movimientos': self.movimientos
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error guardando materia prima: {e}")
    
    # ========== MATERIA PRIMA ==========
    def agregar_ingrediente(self, nombre: str, categoria: str, unidad: str, 
                           stock_inicial: float = 0, costo_unitario: float = 0, 
                           stock_minimo: float = 0) -> bool:
        """Agregar un nuevo ingrediente"""
        if nombre in self.materia_prima:
            return False
        
        self.materia_prima[nombre] = {
            'nombre': nombre,
            'categoria': categoria,
            'unidad': unidad,
            'stock': stock_inicial,
            'costo_unitario': costo_unitario,
            'stock_minimo': stock_minimo,
            'fecha_creacion': datetime.now().isoformat()
        }
        
        if stock_inicial > 0:
            self._registrar_movimiento(nombre, 'ingreso', stock_inicial, 'Stock inicial')
        
        self.guardar_datos()
        return True
    
    def modificar_ingrediente(self, nombre_original: str, datos: dict) -> bool:
        """Modificar un ingrediente existente"""
        if nombre_original not in self.materia_prima:
            return False
        
        nuevo_nombre = datos.get('nombre', nombre_original)
        
        # Si cambia el nombre, actualizar recetas
        if nuevo_nombre != nombre_original:
            self._actualizar_ingrediente_en_recetas(nombre_original, nuevo_nombre)
            self.materia_prima[nuevo_nombre] = self.materia_prima.pop(nombre_original)
        
        # Actualizar datos
        ingrediente = self.materia_prima.get(nuevo_nombre, {})
        ingrediente.update({
            'categoria': datos.get('categoria', ingrediente.get('categoria')),
            'unidad': datos.get('unidad', ingrediente.get('unidad')),
            'costo_unitario': datos.get('costo_unitario', ingrediente.get('costo_unitario')),
            'stock_minimo': datos.get('stock_minimo', ingrediente.get('stock_minimo'))
        })
        
        self.guardar_datos()
        return True
    
    def eliminar_ingrediente(self, nombre: str) -> bool:
        """Eliminar un ingrediente"""
        if nombre not in self.materia_prima:
            return False
        
        # Verificar si está en alguna receta
        for producto, receta in self.recetas.items():
            for ing in receta:
                if ing.get('ingrediente') == nombre:
                    return False  # No se puede eliminar si está en uso
        
        del self.materia_prima[nombre]
        self.guardar_datos()
        return True
    
    def ajustar_stock(self, nombre: str, cantidad: float, tipo: str, motivo: str = "") -> bool:
        """Ajustar stock (ingreso/egreso)"""
        if nombre not in self.materia_prima:
            return False
        
        if tipo == 'ingreso':
            self.materia_prima[nombre]['stock'] += cantidad
        elif tipo == 'egreso':
            if self.materia_prima[nombre]['stock'] < cantidad:
                return False
            self.materia_prima[nombre]['stock'] -= cantidad
        else:
            return False
        
        self._registrar_movimiento(nombre, tipo, cantidad, motivo)
        self.guardar_datos()
        return True
    
    def obtener_ingrediente(self, nombre: str) -> Optional[Dict]:
        """Obtener un ingrediente por nombre"""
        return self.materia_prima.get(nombre)
    
    def obtener_todos_ingredientes(self) -> List[Dict]:
        """Obtener lista de todos los ingredientes"""
        return list(self.materia_prima.values())
    
    def obtener_ingredientes_bajo_stock(self) -> List[Dict]:
        """Obtener ingredientes con stock bajo"""
        bajo_stock = []
        for ing in self.materia_prima.values():
            if ing['stock'] <= ing.get('stock_minimo', 0):
                bajo_stock.append(ing)
        return bajo_stock
    
    # ========== RECETAS ==========
    def crear_receta(self, producto: str, ingredientes: List[Dict]) -> bool:
        """Crear o actualizar receta de un producto"""
        self.recetas[producto] = ingredientes
        self.guardar_datos()
        return True
    
    def obtener_receta(self, producto: str) -> List[Dict]:
        """Obtener la receta de un producto"""
        return self.recetas.get(producto, [])
    
    def eliminar_receta(self, producto: str) -> bool:
        """Eliminar receta de un producto"""
        if producto in self.recetas:
            del self.recetas[producto]
            self.guardar_datos()
            return True
        return False
    
    def consumir_receta(self, producto: str, cantidad_productos: int = 1) -> bool:
        """Consumir ingredientes según la receta al producir/vender"""
        receta = self.recetas.get(producto, [])
        if not receta:
            return False
        
        # Verificar stock disponible
        for ing in receta:
            nombre = ing['ingrediente']
            cantidad_necesaria = ing['cantidad'] * cantidad_productos
            
            if nombre not in self.materia_prima:
                return False
            if self.materia_prima[nombre]['stock'] < cantidad_necesaria:
                return False
        
        # Consumir ingredientes
        for ing in receta:
            nombre = ing['ingrediente']
            cantidad_necesaria = ing['cantidad'] * cantidad_productos
            self.materia_prima[nombre]['stock'] -= cantidad_necesaria
            self._registrar_movimiento(nombre, 'egreso', cantidad_necesaria, 
                                      f"Consumo por producción de {cantidad_productos}x {producto}")
        
        self.guardar_datos()
        return True
    
    def verificar_disponibilidad_receta(self, producto: str, cantidad: int = 1) -> tuple:
        """Verificar si hay stock suficiente para producir una cantidad de productos"""
        receta = self.recetas.get(producto, [])
        if not receta:
            return (False, "No hay receta definida")
        
        faltantes = []
        for ing in receta:
            nombre = ing['ingrediente']
            cantidad_necesaria = ing['cantidad'] * cantidad
            
            if nombre not in self.materia_prima:
                faltantes.append(f"{nombre}: No existe")
            elif self.materia_prima[nombre]['stock'] < cantidad_necesaria:
                faltantes.append(
                    f"{nombre}: Necesita {cantidad_necesaria} {ing.get('unidad', '')}, "
                    f"disponible {self.materia_prima[nombre]['stock']} {ing.get('unidad', '')}"
                )
        
        if faltantes:
            return (False, "\n".join(faltantes))
        return (True, "Stock suficiente")
    
    # ========== MOVIMIENTOS ==========
    def _registrar_movimiento(self, ingrediente: str, tipo: str, cantidad: float, motivo: str = ""):
        """Registrar movimiento de stock"""
        movimiento = {
            'fecha': datetime.now().isoformat(),
            'ingrediente': ingrediente,
            'tipo': tipo,
            'cantidad': cantidad,
            'motivo': motivo
        }
        self.movimientos.append(movimiento)
    
    def obtener_movimientos(self, ingrediente: Optional[str] = None, limite: int = 100) -> List[Dict]:
        """
        Obtener historial de movimientos
        
        Args:
            ingrediente: Nombre del ingrediente (opcional). Si es None, devuelve todos.
            limite: Número máximo de movimientos a devolver
        
        Returns:
            Lista de movimientos
        """
        if ingrediente is None:
            # Devolver todos los movimientos
            movimientos = self.movimientos.copy()
        else:
            # Filtrar por ingrediente
            movimientos = [m for m in self.movimientos if m.get('ingrediente') == ingrediente]
        
        # Devolver los más recientes primero (limitados por 'limite')
        return movimientos[-limite:] if len(movimientos) > limite else movimientos
    
    # ========== UTILIDADES ==========
    def _actualizar_ingrediente_en_recetas(self, nombre_antiguo: str, nombre_nuevo: str):
        """Actualizar nombre de ingrediente en todas las recetas"""
        for producto, receta in self.recetas.items():
            for ing in receta:
                if ing.get('ingrediente') == nombre_antiguo:
                    ing['ingrediente'] = nombre_nuevo
    
    def obtener_categorias_ingredientes(self) -> List[str]:
        """Obtener lista de categorías únicas"""
        categorias = set()
        for ing in self.materia_prima.values():
            if ing.get('categoria'):
                categorias.add(ing['categoria'])
        return sorted(list(categorias))
    
    def obtener_estadisticas(self) -> Dict:
        """Obtener estadísticas generales"""
        total_ingredientes = len(self.materia_prima)
        valor_inventario = sum(
            ing['stock'] * ing['costo_unitario'] 
            for ing in self.materia_prima.values()
        )
        bajo_stock = len(self.obtener_ingredientes_bajo_stock())
        total_recetas = len(self.recetas)
        
        return {
            'total_ingredientes': total_ingredientes,
            'valor_inventario': valor_inventario,
            'ingredientes_bajo_stock': bajo_stock,
            'total_recetas': total_recetas,
            'total_movimientos': len(self.movimientos)
        }