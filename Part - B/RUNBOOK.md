# RUNBOOK — ejecutar y probar Nubara

## 1. En qué carpeta pararse

Abre **PowerShell** y pega esto. Todos los comandos de esta guía se ejecutan desde **`Final Exam\Part - B`**:

```powershell
Set-Location -LiteralPath 'C:\Users\ACER\Desktop\AI Agentic Engineering - Disruption Companion\Final Exam\Part - B'
Get-Location
```

En otro computador, cambia la ruta por la de tu copia. No uses `Resultado Prueba Anterior`.

## 2. Preparar el proyecto (solo la primera vez)

Necesitas Python 3.11 o superior. No necesitas Node, npm ni activar el entorno virtual.

```powershell
python --version
if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    python -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
```

Esto instala el backend, los archivos del frontend y las herramientas de pruebas. Si `python` no existe, usa `py` en los dos primeros comandos que lo invocan.

Para las consultas desde la web necesitas una clave de Gemini. Crea la configuración **sin sobrescribir la existente**:

```powershell
if (-not (Test-Path '.\.env')) {
    Copy-Item -LiteralPath '.\.env.example' -Destination '.\.env'
}
notepad .env
```

Completa `GOOGLE_API_KEY` con tu clave y guarda. `GEMINI_MODEL` selecciona el modelo (valor predeterminado del proyecto: `gemini-3.8-flash`). La clave se queda en `.env`, ignorado por Git; no se copia al frontend ni al RUNBOOK. Reinicia el servidor si cambias esta configuración. Las pruebas locales de la sección 6 no necesitan clave.

## 3. Ejecutar frontend y backend a la vez

En la misma carpeta, ejecuta:

```powershell
.\.venv\Scripts\python.exe -m uvicorn nubara_agent.api:app --host 127.0.0.1 --port 8000
```

**Deja esa terminal abierta. Un solo proceso sirve ambos componentes simultáneamente.** No hace falta un segundo servidor ni configurar CORS. Abre estas direcciones:

| Qué quieres ver | Dirección | Qué debes encontrar |
|---|---|---|
| Frontend | http://127.0.0.1:8000/ | Nubara, selector de casos y formulario de consulta |
| Estado del backend | http://127.0.0.1:8000/health | `{"status":"ok","mode":"exam_mock"}` |
| API interactiva | http://127.0.0.1:8000/docs | Endpoints para consultar y confirmar |

El indicador «API conectada» solo verifica el backend, no la disponibilidad de Gemini. Para detener ambos: **Ctrl+C** en la terminal. Para iniciarlos de nuevo: repite el comando anterior.

## 4. Credenciales y acceso

**No hay login ni contraseñas.** Son identidades simuladas para pruebas locales. El frontend envía automáticamente la identidad correspondiente al caso seleccionado.

| Caso | Reserva | Header `X-Demo-User` | Contraseña |
|---|---|---|---|
| Familia / menor / compensación | `ABC123` | `demo-maria` | No aplica |
| Adultos / alternativa confirmable | `ABC456` | `demo-adults` | No aplica |
| Instrucción maliciosa | `ABC123` | `demo-maria` | No aplica |

La única credencial externa es `GOOGLE_API_KEY`, configurada en el backend. Estos headers no son autenticación de producción. Los vuelos, casos humanos, notificaciones y cambios son simulados; no hay pagos ni reservas reales. No existe un panel de operadores: el identificador y estado del caso se ven en la respuesta.

## 5. Probar todo desde el frontend

Abre http://127.0.0.1:8000/. Cada selección carga un mensaje que puedes editar. Pulsa **Consultar mi viaje** y espera hasta 90 segundos. Puedes desplegar **Ver respuesta técnica (sin token)** para inspeccionar los campos de la API.

| Prueba | Cómo acceder y ejecutar | Resultado esperado cuando Gemini completa |
|---|---|---|
| Familia, caso principal | Selecciona **Familia · revisión humana** y consulta el mensaje precargado | `COMPLETED`, conexión en riesgo, `HUMAN_REVIEW`, sin confirmación; no promete compensación ni cambio. Muestra el caso humano si se abrió. |
| Adultos, confirmación | Selecciona **Adultos · confirmar alternativa** y consulta sin añadir una solicitud de compensación | `COMPLETED`, `CONFIRM_OPTION` y una alternativa `CONFIRMABLE`. Revisa vuelo/fecha/hora, marca la autorización y pulsa **Solicitar esta alternativa**. |
| Instrucción maliciosa | Selecciona **Instrucción maliciosa · controles** y consulta | Debe mantener revisión humana; no pagar ni saltarse controles. La prueba automatizada también verifica que no se realizó una escritura de reserva. |

En adultos, confirma dentro de los **120 segundos desde la emisión de la oferta**. El backend vuelve a validar la opción. `PENDING_CONFIRMATION` significa **solicitud recibida, cambio todavía no confirmado**. `INDETERMINATE` significa resultado desconocido y revisión humana; no repitas automáticamente la reserva. Si hay HTTP 409, vuelve a consultar y revisa la nueva oferta.

Si aparece `UNAVAILABLE` o `INCOMPLETE`, no pasó la consulta del modelo, aunque el HTTP sea 200. El frontend sigue funcionando, pero no habrá una oferta confirmable. Los intentos reales registrados anteriormente devolvieron HTTP 503 del proveedor; no se presupone que Gemini esté disponible ahora.

## 6. Probar controles sin depender de Gemini

Abre otra terminal PowerShell y colócate en la carpeta de la sección 1. El servidor puede seguir abierto, pero estos comandos no lo necesitan.

| Para qué | Qué ejecutar |
|---|---|
| Verificar backend e integración de los archivos web | `.\.venv\Scripts\python.exe -m pytest -q --disable-warnings` |
| Evaluar los cuatro escenarios sin clave ni conexión a Gemini | `.\.venv\Scripts\python.exe scripts/evaluate.py` |
| Evaluar los mismos escenarios usando Gemini real | `.\.venv\Scripts\python.exe scripts/evaluate.py --live` |
| Ejecutar solo la conversación principal con Gemini en terminal | `.\.venv\Scripts\python.exe scripts/demo.py` |

El evaluador local usa un **modelo guionado de prueba**, no Gemini. El resultado esperado es `passed: 4, total: 4`. Los cuatro casos son:

| Caso en el reporte | Qué se prueba | Dónde verlo |
|---|---|---|
| `target` | Familia, conexión en riesgo y revisión humana | Frontend «Familia» o reporte |
| `contradictory_sources` | Fuentes autorizadas contradictorias: conexión `UNKNOWN` y revisión humana | Solo evaluador; no hay interruptor de fallos en la API pública |
| `malicious_input` | Instrucción que intenta saltarse las reglas: sin reserva automática | Frontend «Instrucción maliciosa» o reporte |
| `failed_write` | Fallo tras confirmar adultos: `INDETERMINATE`, sin escritura duplicada | Solo evaluador; inyecta el fallo de forma aislada |

Para abrir los resultados después de ejecutar:

```powershell
notepad .\evidence\offline-evaluation.json
```

Para los resultados de `--live`, abre `evidence\live-evaluation.json`. La demo individual guarda `evidence\latest-real-response.json` y `evidence\latest-real-trace.json`. Cada ejecución del evaluador reemplaza su reporte correspondiente. Los escenarios de fallos usan bases temporales aisladas.

## 7. Probar directamente la API (opcional)

En http://127.0.0.1:8000/docs:

1. Abre **POST /v1/disruptions/{booking_id}/assess → Try it out**.
2. Escribe `ABC123` en `booking_id` y `demo-maria` en `x-demo-user`.
3. Usa este cuerpo y pulsa **Execute**:

```json
{"message":"Mi vuelo a Lima está retrasado y viajo con mi hijo de 7 años. ¿Alcanzamos México? Quiero alternativas y saber cuánto me pagan de compensación."}
```

Para adultos, cambia a `ABC456` / `demo-adults` y usa:

```json
{"message":"My flight is delayed. Can I make my connection? Please find rebooking options."}
```

Solo si recibes `CONFIRM_OPTION` y `confirmation_token`, abre **POST /v1/disruptions/confirm**, usa `demo-adults` y pega el token y el `option_id` realmente ofrecidos:

```json
{"confirmation_token":"TOKEN_RECIBIDO", "option_id":"O1", "confirmed":true}
```

Para probar permisos, consulta `ABC123` con `demo-adults`: debe devolver **403**. Sin header: **422**. Confirmar un token inválido: **409**.

## 8. Si algo falla

| Problema | Solución |
|---|---|
| No encuentra Python, `.venv` o `nubara_agent` | Comprueba `Get-Location` y repite la instalación de la sección 2. |
| No abre la web | Deja Uvicorn ejecutándose y abre la URL HTTP; no abras `index.html` como archivo. |
| Puerto 8000 ocupado | Detén tu servidor anterior con Ctrl+C o usa `--port 8001` y cambia todas las URLs a 8001. El frontend usa automáticamente el mismo puerto. |
| Terminal ocupada al ejecutar Uvicorn | Es normal. Usa el navegador u otra terminal; Ctrl+C detiene el servicio. |
| `UNAVAILABLE` / error de proveedor | Revisa la clave y el modelo en `.env`, reinicia y consulta las trazas. Un 503 requiere reintentar más tarde; no es una prueba aprobada. |
| Oferta expirada / HTTP 409 | Consulta nuevamente y revisa la nueva oferta antes de confirmar. |
| Error de red al confirmar | El resultado puede ser desconocido. No asumas éxito ni reenvíes automáticamente. |
| Cambiaste HTML/CSS/JS y no ves cambios | Recarga con Ctrl+F5. Los cambios Python requieren reiniciar Uvicorn. |

## 9. Dónde está cada componente

Rutas relativas a `Part - B`:

| Ruta | Contenido |
|---|---|
| `src/nubara_agent/web/` | Frontend HTML, CSS y JavaScript; sin compilación |
| `src/nubara_agent/api.py` | API y montaje del frontend en `/` |
| `src/nubara_agent/` | Agente ADK, reglas, adaptadores y persistencia |
| `.env` | Clave local y modelo de Gemini |
| `tests/` | Pruebas automatizadas |
| `scripts/evaluate.py` | Los cuatro escenarios de evaluación |
| `evidence/` | Reportes y trazas sanitizadas |
| `runtime.sqlite3` | Ofertas y deduplicación persistentes; reiniciar no borra su estado |
| `TECHNICAL_NOTES.md` | Arquitectura, límites e historial de evidencias |

El frontend no guarda tokens en almacenamiento del navegador. Los mantiene solo durante la consulta actual. No hay despliegue público ni integración con operadores reales.
