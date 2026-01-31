# Test Fixtures

Datos de prueba en formato CSV para tests rápidos sin depender de PostgreSQL real.

## Uso

```python
import pandas as pd

@pytest.fixture
def mock_citas():
    return pd.read_csv('tests/fixtures/citas_doctor_1.csv')

def test_algo(mock_citas):
    total = len(mock_citas)
    assert total == 8
```

## Archivos

- **citas_doctor_1.csv**: Doctor con 8 citas (3 completadas, 5 pendientes)
- **citas_doctor_sin_citas.csv**: Doctor sin citas (día libre)
- **citas_doctor_muchas.csv**: Doctor con 15 citas (caso edge)
- **pacientes_ejemplo.csv**: 10 pacientes de prueba
- **doctores_ejemplo.csv**: 3 doctores de prueba

## Crear nuevo fixture

1. Copiar un CSV existente
2. Modificar datos según el escenario a probar
3. Usar en test con `pd.read_csv()`