import os
import platform
from datetime import datetime
import tempfile

class ImpresoraRecibos:
    def __init__(self):
        self.sistema = platform.system()
        
    def imprimir_recibo(self, pedido, nombre_impresora="POS-80"):
        """Genera e imprime un recibo para el pedido"""
        
        # Generar contenido del recibo
        recibo = self.generar_recibo_texto(pedido)
        
        if self.sistema == "Windows":
            self.imprimir_windows(recibo, nombre_impresora)
        else:
            self.imprimir_linux(recibo, nombre_impresora)
            
    def generar_recibo_texto(self, pedido):
        """Genera el texto formateado del recibo"""
        ancho = 40
        
        lineas = []
        lineas.append("=" * ancho)
        lineas.append("COCINA CENTRAL".center(ancho))
        lineas.append("Comidas Rápidas".center(ancho))
        lineas.append("=" * ancho)
        lineas.append(f"Pedido: #{pedido['id'][:8]}".center(ancho))
        lineas.append(f"Fecha: {pedido['fecha']} {pedido['hora']}".center(ancho))
        lineas.append("-" * ancho)
        lineas.append(f"Cliente: {pedido['cliente']}")
        lineas.append(f"Tel: {pedido['telefono']}")
        lineas.append(f"Dir: {pedido['direccion']}")
        lineas.append("-" * ancho)
        lineas.append("PRODUCTOS:")
        lineas.append("-" * ancho)
        
        for item in pedido['items']:
            linea = f"{item['cantidad']}x {item['nombre']}"
            precio = f"${item['subtotal']:.2f}"
            espacios = ancho - len(linea) - len(precio)
            lineas.append(linea + " " * espacios + precio)
            
        lineas.append("-" * ancho)
        total_linea = f"TOTAL:"
        total_precio = f"${pedido['total']:.2f}"
        espacios = ancho - len(total_linea) - len(total_precio)
        lineas.append(total_linea + " " * espacios + total_precio)
        lineas.append("=" * ancho)
        lineas.append("¡Gracias por su compra!".center(ancho))
        lineas.append("=" * ancho)
        lineas.append("\n\n\n")  # Espacio para cortar
        
        return "\n".join(lineas)
        
    def imprimir_windows(self, texto, nombre_impresora):
        """Imprime usando comandos de Windows"""
        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(texto)
                temp_file = f.name
                
            # Imprimir usando el comando print de Windows
            os.system(f'print /D:"{nombre_impresora}" "{temp_file}"')
            
            # Limpiar archivo temporal
            os.unlink(temp_file)
            
        except Exception as e:
            print(f"Error al imprimir: {e}")
            # Respaldo: guardar en archivo
            self.guardar_respaldo(texto)
            
    def imprimir_linux(self, texto, nombre_impresora):
        """Imprime usando comandos de Linux/Mac"""
        try:
            # Usar lp para imprimir
            import subprocess
            proceso = subprocess.Popen(['lp', '-d', nombre_impresora], 
                                      stdin=subprocess.PIPE, 
                                      text=True)
            proceso.communicate(texto)
            
        except Exception as e:
            print(f"Error al imprimir: {e}")
            self.guardar_respaldo(texto)
            
    def guardar_respaldo(self, texto):
        """Guarda el recibo como archivo de texto como respaldo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recibo_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(texto)
            
        print(f"Recibo guardado como respaldo: {filename}")