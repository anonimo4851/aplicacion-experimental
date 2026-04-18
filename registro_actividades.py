import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class RegistroActividades:
    def __init__(self, directorio_logs='logs'):
        self.directorio_logs = directorio_logs
        self.asegurar_directorio()
        
    def asegurar_directorio(self):
        """Crea el directorio de logs si no existe"""
        if not os.path.exists(self.directorio_logs):
            os.makedirs(self.directorio_logs)
            
    def obtener_archivo_hoy(self) -> str:
        """Obtiene el nombre del archivo de log para hoy"""
        fecha = datetime.now().strftime('%Y%m%d')
        return os.path.join(self.directorio_logs, f'actividades_{fecha}.json')
        
    def cargar_actividades(self, fecha: Optional[datetime] = None) -> List[Dict]:
        """Carga las actividades de una fecha específica"""
        if fecha is None:
            archivo = self.obtener_archivo_hoy()
        else:
            archivo = os.path.join(self.directorio_logs, f'actividades_{fecha.strftime("%Y%m%d")}.json')
            
        if os.path.exists(archivo):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
        
    def guardar_actividades(self, actividades: List[Dict], fecha: Optional[datetime] = None):
        """Guarda las actividades de una fecha específica"""
        if fecha is None:
            archivo = self.obtener_archivo_hoy()
        else:
            archivo = os.path.join(self.directorio_logs, f'actividades_{fecha.strftime("%Y%m%d")}.json')
            
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(actividades, f, indent=2, ensure_ascii=False)
            
    def registrar_actividad(self, usuario: str, accion: str, detalles: Dict, 
                           tipo: str = "inventario"):
        """Registra una nueva actividad"""
        actividad = {
            "timestamp": datetime.now().isoformat(),
            "usuario": usuario,
            "accion": accion,
            "tipo": tipo,
            "detalles": detalles
        }
        
        actividades = self.cargar_actividades()
        actividades.append(actividad)
        self.guardar_actividades(actividades)
        
    def registrar_cambio_inventario(self, usuario: str, accion: str, 
                                   producto: str, cantidad_anterior: int, 
                                   cantidad_nueva: int, precio_unitario: float = 0):
        """Registra un cambio en el inventario"""
        detalles = {
            "producto": producto,
            "cantidad_anterior": cantidad_anterior,
            "cantidad_nueva": cantidad_nueva,
            "diferencia": cantidad_nueva - cantidad_anterior,
            "precio_unitario": precio_unitario,
            "valor_cambio": abs(cantidad_nueva - cantidad_anterior) * precio_unitario
        }
        self.registrar_actividad(usuario, accion, detalles, "inventario")
        
    def registrar_consumo(self, usuario: str, producto: str, cantidad: int, 
                         precio_unitario: float, motivo: str = "venta"):
        """Registra específicamente un consumo de producto"""
        detalles = {
            "producto": producto,
            "cantidad_consumida": cantidad,
            "precio_unitario": precio_unitario,
            "valor_total": cantidad * precio_unitario,
            "motivo": motivo
        }
        self.registrar_actividad(usuario, "consumo", detalles, "consumo")
        
    def obtener_consumo_diario(self, fecha: Optional[datetime] = None) -> Dict:
        """Obtiene el resumen de consumo diario"""
        actividades = self.cargar_actividades(fecha)
        
        consumo = {
            "fecha": fecha.strftime('%Y-%m-%d') if fecha else datetime.now().strftime('%Y-%m-%d'),
            "productos": {},
            "total_unidades": 0,
            "valor_total": 0,
            "productos_agregados": []  # NUEVO: Lista de productos agregados
        }
        
        for actividad in actividades:
            if actividad["tipo"] == "consumo":
                detalles = actividad["detalles"]
                producto = detalles.get("producto", "Desconocido")
                
                if producto not in consumo["productos"]:
                    consumo["productos"][producto] = {
                        "cantidad": 0,
                        "valor": 0,
                        "precio_unitario": detalles.get("precio_unitario", 0)
                    }
                    
                consumo["productos"][producto]["cantidad"] += detalles.get("cantidad_consumida", 0)
                consumo["productos"][producto]["valor"] += detalles.get("valor_total", 0)
                consumo["total_unidades"] += detalles.get("cantidad_consumida", 0)
                consumo["valor_total"] += detalles.get("valor_total", 0)
            
            # NUEVO: Registrar productos agregados
            elif actividad["tipo"] == "inventario" and actividad["accion"] == "agregar_producto":
                detalles = actividad["detalles"]
                producto = detalles.get("producto", "Desconocido")
                if producto not in [p["nombre"] for p in consumo["productos_agregados"]]:
                    consumo["productos_agregados"].append({
                        "nombre": producto,
                        "cantidad": detalles.get("cantidad_nueva", 0),
                        "precio": detalles.get("precio_unitario", 0),
                        "usuario": actividad["usuario"],
                        "hora": actividad["timestamp"]
                    })
                
        return consumo
        
    def obtener_historial_cambios(self, producto: str, dias: int = 7) -> List[Dict]:
        """Obtiene el historial de cambios de un producto específico"""
        historial = []
        fecha_actual = datetime.now()
        
        for i in range(dias):
            fecha = fecha_actual - timedelta(days=i)
            actividades = self.cargar_actividades(fecha)
            
            for actividad in actividades:
                if (actividad["tipo"] in ["inventario", "consumo"] and 
                    actividad["detalles"].get("producto") == producto):
                    historial.append({
                        "fecha": fecha.strftime('%Y-%m-%d'),
                        "timestamp": actividad["timestamp"],
                        "usuario": actividad["usuario"],
                        "accion": actividad["accion"],
                        "detalles": actividad["detalles"]
                    })
                    
        return sorted(historial, key=lambda x: x["timestamp"], reverse=True)
        
    def obtener_resumen_periodo(self, fecha_inicio: datetime, fecha_fin: datetime) -> Dict:
        """Obtiene resumen de actividades en un período"""
        resumen = {
            "periodo": f"{fecha_inicio.strftime('%Y-%m-%d')} a {fecha_fin.strftime('%Y-%m-%d')}",
            "total_actividades": 0,
            "consumo_total": 0,
            "productos_mas_consumidos": {},
            "usuarios_activos": set()
        }
        
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            actividades = self.cargar_actividades(fecha_actual)
            
            for actividad in actividades:
                resumen["total_actividades"] += 1
                resumen["usuarios_activos"].add(actividad["usuario"])
                
                if actividad["tipo"] == "consumo":
                    detalles = actividad["detalles"]
                    resumen["consumo_total"] += detalles.get("valor_total", 0)
                    
                    producto = detalles.get("producto", "Desconocido")
                    if producto not in resumen["productos_mas_consumidos"]:
                        resumen["productos_mas_consumidos"][producto] = 0
                    resumen["productos_mas_consumidos"][producto] += detalles.get("cantidad_consumida", 0)
                    
            fecha_actual += timedelta(days=1)
            
        resumen["usuarios_activos"] = list(resumen["usuarios_activos"])
        return resumen