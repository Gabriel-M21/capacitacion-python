# Capacitación Python

Repositorio de laboratorios de capacitación en Python. Cada carpeta `Modulo_X`
es un proyecto independiente con su propio entorno Poetry y README con el
contenido, los requisitos y los pasos para ejecutar ese módulo.

## Recorrido

Los módulos implementados en este repositorio son:

### Nivel fundamental

| Módulo | Tema | Guía |
|---|---|---|
| 1 | Entorno y herramientas | [README](./Modulo_1/README.md) |
| 2 | Fundamentos del lenguaje | [README](./Modulo_2/README.md) |
| 3 | Funciones y programación Pythonica | [README](./Modulo_3/README.md) |
| 4 | Objetos y modelos de datos | [README](./Modulo_4/README.md) |
| 5 | Tipado estático y calidad | [README](./Modulo_5/README.md) |
| 6 | Librería estándar y entrada/salida | [README](./Modulo_6/README.md) |
| 7 | HTTP y consumo de APIs con Smocker | [README](./Modulo_7/README.md) |

### Nivel intermedio

| Módulo | Tema | Guía |
|---|---|---|
| 8 | Acceso a datos y ORM | [README](./Modulo_8/README.md) |
| 9 | APIs web con FastAPI | [README](./Modulo_9/README.md) |
| 10 | Pruebas y TDD | [README](./Modulo_10/README.md) |
| 11 | Concurrencia y rendimiento | [README](./Modulo_11/README.md) |
| 12 | Principios SOLID | [README](./Modulo_12/README.md) |
| 13 | Patrones de diseño | [README](./Modulo_13/README.md) |
| 14 | Ciencia de datos | [README](./Modulo_14/README.md) |

### Nivel avanzado

| Módulo | Tema | Guía |
|---|---|---|
| 15 | Arquitectura Hexagonal | [README](./Modulo_15/README.md) |
| 16 | Arquitectura Limpia | [README](./Modulo_16/README.md) |
| 17 | Empaquetado, distribución y CI/CD | [README](./Modulo_17/README.md) |
| 18 | CLI y automatización | [README](./Modulo_18/README.md) |
| 19 | Seguridad y mantenimiento | [README](./Modulo_19/README.md) |

El Módulo 20 aparece como opcional en el temario, pero actualmente no tiene una
carpeta de implementación en este repositorio.

## Requisitos generales

- Python 3.12
- Poetry
- Docker Desktop sólo para los laboratorios que lo requieren

No ejecutes `poetry install` desde la raíz: instala las dependencias dentro de la
carpeta del módulo que vas a trabajar. Por ejemplo, desde **CMD** abierto en la
raíz del repositorio:

```cmd
cd /d Modulo_7
poetry install
```

Después, sigue el README de esa carpeta. Ahí se indican los comandos de ejecución
propios del laboratorio y si necesita servicios adicionales como Smocker, una API
o Docker. Algunas demostraciones requieren dos ventanas CMD para mantener el
servicio activo mientras se ejecuta el cliente.

## Proyecto final integrador

El proyecto de gestión de pedidos está en una carpeta independiente:

- [`order-management-system/README.md`](./order-management-system/README.md):
  instalación, configuración, API, pruebas y validación del proyecto final.

Sus dependencias y comandos se ejecutan desde `order-management-system`, no desde
la raíz de la capacitación ni desde las carpetas `Modulo_X`.
