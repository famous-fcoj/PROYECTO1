import requests
import json

url = "http://localhost:8000/api/recibir-orden/"
data = {
    "numero_ot": "OT-TEST-001",
    "fecha_creacion": "2025-10-16", 
    "equipo_id": 1,
    "tipo_accion_id": 1,
    "responsable_ejecucion_id": 1,
    "supervisor_id": 1,
    "fecha_planificada": "2025-10-20",
    "observaciones": "Prueba desde Python",
    "odometro": 1500
}

response = requests.post(url, json=data)
print("Status Code:", response.status_code)
print("Response:", response.json())