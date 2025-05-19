# Instrucciones para acceder al Panel de Administración de Citas

1. Abre tu navegador web.

2. Ingresa la siguiente URL en la barra de direcciones:
   (Reemplaza <tu-dominio> por el dominio real de tu app en Render o el servidor donde esté desplegada)

   https://<tu-dominio>/admin
   
   Ejemplo:
   https://genesis-llc.onrender.com/admin

3. Introduce la contraseña de administrador cuando se te pida:
   genesis2025
   (O la que hayas configurado en la variable de entorno ADMIN_PANEL_PASSWORD)

4. Una vez dentro, verás la tabla con todas las citas registradas.
   Puedes descargar todas las citas en formato Excel/CSV haciendo clic en "Descargar Excel".

Si tienes problemas de acceso, revisa la variable de entorno ADMIN_PANEL_PASSWORD en la configuración de tu servidor Render o donde esté desplegada la app.

---

Si ves el mensaje "Not Found" o "Página no encontrada", revisa que la URL esté bien escrita y que tu aplicación esté corriendo correctamente en el servidor.
