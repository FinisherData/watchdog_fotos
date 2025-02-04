import os
import time
import requests

from django.core.management.base import BaseCommand
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ruta de la carpeta principal (usa raw string para evitar problemas con backslashes)
WATCHED_DIR = r'/var/www/html/api/public/ftp'

def process_image(image_path):
    """
    Extrae el nombre de la carpeta desde la ruta y envía la imagen al endpoint.
    Se espera la estructura: <nombre>/archivo.jpg

    Si el envío es exitoso, elimina la imagen local.
    Implementa reintentos en caso de error de permiso (archivo bloqueado).
    """
    # Extraer la ruta relativa respecto a WATCHED_DIR.
    # Se espera que la imagen esté dentro de una carpeta cuyo nombre usaremos para el endpoint.
    relative_path = os.path.relpath(image_path, WATCHED_DIR)
    parts = relative_path.split(os.sep)
    if len(parts) < 2:
        print("Estructura de carpetas inválida. Se esperaba: nombre/imagen")
        return

    nombre = parts[0]
    url = f"https://fotos.raceline.app/ia/imagenes/uploadxNombre/{nombre}/"
    print(f"Llamando a {url} con la imagen: {image_path}")

    # Intentar abrir y enviar el archivo con reintentos en caso de PermissionError
    retries = 5
    for attempt in range(retries):
        try:
            with open(image_path, 'rb') as f:
                files = {
                    'images': (os.path.basename(image_path), f, 'image/jpeg')
                }
                response = requests.post(url, files=files)
            # Si se logró abrir y enviar, salimos del loop
            break
        except PermissionError as e:
            print(f"Intento {attempt+1}/{retries} - Error al abrir la imagen: {e}. Reintentando en 1 segundo...")
            time.sleep(1)
    else:
        print("No se pudo acceder al archivo luego de varios intentos.")
        return

    print("Respuesta del endpoint:", response.status_code, response.text)
    if response.status_code in [200, 201]:
        # Intentar eliminar la imagen local si el endpoint respondió exitosamente
        try:
            os.remove(image_path)
            print(f"Imagen eliminada: {image_path}")
        except Exception as e:
            print(f"Error al eliminar la imagen: {e}")
    else:
        print("La imagen no se eliminó porque la respuesta del endpoint no fue exitosa.")

class FolderImageHandler(FileSystemEventHandler):
    """
    Este handler se activa cuando se crea un archivo.
    Si el archivo es una imagen (extensión jpg, jpeg, png o gif), se invoca process_image.
    """
    def on_created(self, event):
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                print("Imagen detectada:", event.src_path)
                process_image(event.src_path)

class Command(BaseCommand):
    help = ("Monitorea la carpeta 'imagenes' para detectar la creación de imágenes "
            "en una estructura de carpetas (nombre/imagen) y llama al endpoint uploadxNombre, "
            "eliminando la imagen local luego de procesarla.")

    def handle(self, *args, **kwargs):
        event_handler = FolderImageHandler()
        observer = Observer()
        observer.schedule(event_handler, WATCHED_DIR, recursive=True)
        observer.start()
        self.stdout.write(self.style.SUCCESS(f"Monitoreando la carpeta: {WATCHED_DIR}"))

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Deteniendo el monitoreo..."))
            observer.stop()
        observer.join()