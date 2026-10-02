# API externa de pacientes

## Consulta por CIP

`POST /api/v1/patients/lookup/`

La llamada requiere `Authorization: Bearer <api-key>`. La clave solo autoriza
pacientes cuyo propietario sea la organización asignada a esa credencial.
El CIP va en el cuerpo JSON, no en la URL, para evitar que se incluya en logs
habituales del servidor o proxy.

Ejemplo:

```bash
curl -X POST \
  -H 'Authorization: Bearer cap_..._...' \
  -H 'Content-Type: application/json' \
  --data '{"cip":"CIP-123"}' \
  https://capsulae.example/api/v1/patients/lookup/
```

Una respuesta satisfactoria (`200`) incluye únicamente `cip`, `patient_id`,
`external_id`, nombre, apellidos y fecha de nacimiento. `patient_id` permite
abrir la ficha autorizada del paciente en Cápsulae2. El endpoint no expone teléfono, NIF,
dirección, correo ni documentos de consentimiento.

Errores: `401 invalid_credentials`, `400 invalid_cip`, `404 patient_not_found`
y `429 rate_limit_exceeded` (60 solicitudes por minuto y credencial/IP).
En producción configure una caché compartida entre procesos para que ese límite
sea global (por ejemplo, Redis).

## Alta y revocación de claves

Crear una clave (se muestra una sola vez):

```bash
python manage.py create_external_api_key --owner <id-o-usuario> --name 'Nombre de plataforma'
```

La clave se guarda con hash. Para revocarla, marque `active` como falso desde
Administración → Credenciales API externas. Las consultas se auditan con hash
del CIP, resultado, credencial, IP y fecha; nunca se almacena el CIP en claro
en el registro de auditoría.
