import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Optional

class Autenticacion:
    def __init__(self, archivo='usuarios.json'):
        self.archivo = archivo
        self.usuarios = self.cargar_usuarios()
        self.usuario_actual = None
        self.es_admin = False
        
    def cargar_usuarios(self) -> Dict:
        """Carga los usuarios desde el archivo JSON"""
        if os.path.exists(self.archivo):
            try:
                with open(self.archivo, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Crear usuarios por defecto
        usuarios_default = {
            "admin": {
                "password": self.encriptar_password("admin123"),
                "rol": "admin",
                "nombre_completo": "Administrador",
                "fecha_creacion": datetime.now().isoformat()
            },
            "usuario": {
                "password": self.encriptar_password("usuario123"),
                "rol": "usuario",
                "nombre_completo": "Usuario Regular",
                "fecha_creacion": datetime.now().isoformat()
            }
        }
        self.guardar_usuarios(usuarios_default)
        return usuarios_default
        
    def guardar_usuarios(self, usuarios=None):
        """Guarda los usuarios en el archivo JSON"""
        if usuarios is None:
            usuarios = self.usuarios
        with open(self.archivo, 'w', encoding='utf-8') as f:
            json.dump(usuarios, f, indent=2, ensure_ascii=False)
            
    def encriptar_password(self, password: str) -> str:
        """Encripta la contraseña usando SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def verificar_password(self, password: str, password_encriptado: str) -> bool:
        """Verifica si la contraseña coincide"""
        return self.encriptar_password(password) == password_encriptado
        
    def login(self, usuario: str, password: str) -> bool:
        """Intenta iniciar sesión"""
        if usuario in self.usuarios:
            if self.verificar_password(password, self.usuarios[usuario]["password"]):
                self.usuario_actual = usuario
                self.es_admin = self.usuarios[usuario]["rol"] == "admin"
                return True
        return False
        
    def logout(self):
        """Cierra la sesión actual"""
        self.usuario_actual = None
        self.es_admin = False
        
    def crear_usuario(self, usuario: str, password: str, rol: str, nombre_completo: str) -> bool:
        """Crea un nuevo usuario (solo admin)"""
        if not self.es_admin:
            return False
            
        if usuario in self.usuarios:
            return False
            
        self.usuarios[usuario] = {
            "password": self.encriptar_password(password),
            "rol": rol,
            "nombre_completo": nombre_completo,
            "fecha_creacion": datetime.now().isoformat()
        }
        self.guardar_usuarios()
        return True
        
    def cambiar_password(self, password_actual: str, nuevo_password: str) -> bool:
        """Cambia la contraseña del usuario actual"""
        if not self.usuario_actual:
            return False
            
        if self.verificar_password(password_actual, self.usuarios[self.usuario_actual]["password"]):
            self.usuarios[self.usuario_actual]["password"] = self.encriptar_password(nuevo_password)
            self.guardar_usuarios()
            return True
        return False
        
    def obtener_usuarios(self) -> Dict:
        """Obtiene la lista de usuarios (solo admin)"""
        if not self.es_admin:
            return {}
        return self.usuarios.copy()
        
    def eliminar_usuario(self, usuario: str) -> bool:
        """Elimina un usuario (solo admin)"""
        if not self.es_admin or usuario == "admin":
            return False
            
        if usuario in self.usuarios:
            del self.usuarios[usuario]
            self.guardar_usuarios()
            return True
        return False