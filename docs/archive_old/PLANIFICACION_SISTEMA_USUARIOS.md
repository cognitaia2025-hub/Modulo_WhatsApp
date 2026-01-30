# Planificacion: Sistema de Identificacion de Usuarios

## Diagrama del Sistema Propuesto

```mermaid
graph TD
    %% ============================================================
    %% INICIO DEL FLUJO
    %% ============================================================
    START((Mensaje WhatsApp)) --> N0["<b>0. Nodo Identificacion</b><br/>Extrae numero telefono<br/>Consulta BD usuarios"]
    
    %% Bifurcacion de Identificacion
    N0 -- "Usuario Admin" --> ADMIN_FLAG["Flag: es_admin=true<br/>Permisos completos"]
    N0 -- "Usuario Registrado" --> USER_FLAG["Flag: es_admin=false<br/>Carga perfil existente"]
    N0 -- "Usuario Nuevo" --> REGISTRO["Auto-registro<br/>Crea perfil basico"]
    
    ADMIN_FLAG --> N1
    USER_FLAG --> N1
    REGISTRO --> N1
    
    %% ============================================================
    %% FLUJO EXISTENTE (7 NODOS)
    %% ============================================================
    N1["<b>1. Nodo Cache</b><br/>Sesion Activa?<br/>Rolling Window 24h"] --> N2
    
    N2["<b>2. Nodo Filtrado</b><br/>Requiere Herramientas?<br/>Deteccion de Intencion"]
    
    N2 -- "SI - Calendario" --> N3["<b>3. Recuperacion Episodica</b><br/>Busqueda en Memoria<br/>Embeddings 384D"]
    N2 -- "NO - Conversacion" --> N5
    
    N3 --> N4["<b>4. Seleccion de Herramientas</b><br/>Que herramienta usar?<br/>DeepSeek LLM"]
    
    N4 -- "Herramienta Detectada" --> N5["<b>5. Ejecucion de Herramientas</b><br/>Google Calendar API<br/>+ Orquestador LLM"]
    N4 -- "Sin Herramienta" --> N5
    
    N5 --> N6["<b>6. Generacion de Resumen</b><br/>Auditor LLM<br/>Resumen + Preferencias"]
    
    N6 --> N7["<b>7. Persistencia Episodica</b><br/>Guarda en Memoria<br/>Embeddings + Metadatos"]
    
    N7 --> END((Respuesta al Usuario))

    %% ============================================================
    %% BASE DE DATOS - TABLA NUEVA: usuarios
    %% ============================================================
    subgraph DB_USERS["Nueva Tabla: usuarios"]
        direction TB
        
        DB_U["usuarios<br/>─────────────────<br/>id SERIAL PRIMARY KEY<br/>phone_number VARCHAR UNIQUE<br/>display_name VARCHAR<br/>es_admin BOOLEAN DEFAULT false<br/>timezone VARCHAR<br/>preferencias JSONB<br/>created_at TIMESTAMP<br/>last_seen TIMESTAMP"]
    end

    %% ============================================================
    %% BASES DE DATOS EXISTENTES
    %% ============================================================
    subgraph DB["Base de Datos PostgreSQL (puerto 5434)"]
        direction TB
        
        DB_V["memoria_episodica<br/>Conversaciones pasadas<br/>Busqueda por similitud"]
        
        DB_T["herramientas_disponibles<br/>6 herramientas activas"]
        
        DB_CK["Control de Sesiones<br/>checkpoints<br/>TTL: 24 horas"]
        
        DB_A["auditoria_conversaciones<br/>Registro completo"]
        
        DB_US["user_sessions<br/>Sesiones activas<br/>phone_number indexado"]
    end

    %% ============================================================
    %% ESTADO ACTUALIZADO
    %% ============================================================
    subgraph STATE["Estado Actualizado (WhatsAppAgentState)"]
        direction TB
        
        ST["user_id (phone_number)<br/>session_id<br/>─────────────────<br/><b>NUEVOS CAMPOS:</b><br/>es_admin: bool<br/>usuario_info: dict<br/>usuario_registrado: bool<br/>─────────────────<br/>messages[]<br/>herramientas_seleccionadas[]<br/>contexto_episodico{}"]
    end

    %% ============================================================
    %% CONEXIONES DEL NODO 0
    %% ============================================================
    N0 -.->|"SELECT por phone"| DB_U
    N0 -.->|"INSERT si nuevo"| DB_U
    N0 -.->|"Actualiza estado"| ST

    %% ============================================================
    %% ESTILOS
    %% ============================================================
    classDef nodoNuevo fill:#FF5722,stroke:#BF360C,stroke-width:3px,color:#fff
    classDef nodoExistente fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    classDef nodoDecision fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
    classDef dbNueva fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff
    classDef dbExistente fill:#00BCD4,stroke:#006064,stroke-width:2px,color:#fff
    classDef estado fill:#FFC107,stroke:#FF8F00,stroke-width:2px,color:#000
    classDef flag fill:#8BC34A,stroke:#558B2F,stroke-width:2px,color:#fff
    
    class N0 nodoNuevo
    class N1,N5,N6,N7 nodoExistente
    class N2,N3,N4 nodoDecision
    class DB_U dbNueva
    class DB_V,DB_T,DB_CK,DB_A,DB_US dbExistente
    class ST,STATE estado
    class ADMIN_FLAG,USER_FLAG,REGISTRO flag
```

---

## Explicacion del Sistema Propuesto

### El Problema que Resolvemos

Actualmente el sistema recibe mensajes de WhatsApp y los procesa sin saber realmente quien esta hablando. Todos los usuarios son tratados de la misma manera, sin distincion entre el administrador del sistema y los demas usuarios. Tampoco existe un registro persistente de los usuarios que han interactuado con el sistema.

Lo que necesitamos es un mecanismo que, antes de procesar cualquier mensaje, primero identifique quien esta hablando. El numero de telefono de WhatsApp sera nuestra llave principal para esto.

### Como Funciona la Identificacion

Cuando llega un mensaje de WhatsApp, este viene acompanado del numero de telefono de quien lo envia. Este numero es unico para cada persona y no cambia, lo que lo hace perfecto para identificar usuarios de manera confiable.

El nuevo nodo de identificacion funcionaria como un portero en la entrada de un edificio. Antes de dejar pasar a alguien, primero verifica su identidad. Este portero tiene una lista de residentes (la tabla de usuarios en la base de datos) y sabe quien es el dueno del edificio (el administrador).

### El Proceso Paso a Paso

Primero, cuando llega un mensaje, el sistema extrae el numero de telefono del remitente. Este numero viene en el formato que WhatsApp utiliza, que incluye el codigo de pais seguido del numero local.

Segundo, con ese numero en mano, el sistema consulta la base de datos para ver si ya conoce a esa persona. Busca en la tabla de usuarios usando el numero de telefono como identificador.

Si encuentra al usuario, carga toda su informacion: su nombre, sus preferencias, su zona horaria preferida, y muy importante, si es el administrador o no. Esta informacion se coloca en el estado del sistema para que todos los nodos siguientes puedan acceder a ella.

Si no encuentra al usuario, significa que es alguien nuevo que nunca ha hablado con el sistema. En este caso, automaticamente crea un registro basico con el numero de telefono y la fecha actual. El sistema podria pedirle su nombre en la primera interaccion para completar el perfil.

### La Distincion del Administrador

El administrador es un caso especial. Su numero de telefono estara guardado en una variable de configuracion del sistema. Cuando el nodo de identificacion detecta que el numero entrante coincide con el numero del administrador, activa una bandera especial en el estado.

Esta bandera de administrador podria usarse en el futuro para funcionalidades exclusivas: ver estadisticas del sistema, modificar configuraciones, acceder a herramientas de gestion, o recibir notificaciones especiales sobre el uso del sistema.

### La Nueva Tabla de Usuarios

La base de datos necesita una nueva tabla llamada usuarios. Esta tabla guardara toda la informacion importante de cada persona que interactue con el sistema.

El campo principal es el numero de telefono, que sera unico para cada registro. Tambien guardaremos el nombre que la persona prefiera usar, su zona horaria para calcular correctamente las fechas de los eventos, y un campo flexible de preferencias donde se pueden almacenar configuraciones personalizadas.

Un campo booleano indicara si el usuario es administrador. Por defecto sera falso, y solo el registro del administrador tendra este valor en verdadero. Tambien se guardaran las fechas de creacion del registro y de la ultima vez que el usuario interactuo con el sistema.

### Cambios en el Estado del Sistema

El estado que fluye a traves del grafo necesita tres nuevos campos. El primero es un indicador booleano que dice si el usuario actual es el administrador. El segundo es un diccionario con toda la informacion del usuario cargada de la base de datos. El tercero es otro indicador que dice si el usuario ya estaba registrado o si acaba de ser creado automaticamente.

Estos campos estaran disponibles para todos los nodos siguientes, lo que permite personalizar el comportamiento del sistema segun quien este hablando.

### Integracion con el Flujo Existente

El nodo de identificacion se inserta al principio del flujo, antes del nodo de cache. Esto garantiza que siempre sepamos quien esta hablando antes de procesar cualquier cosa.

El nodo de cache y todos los demas continuan funcionando igual que antes, pero ahora tienen acceso a informacion adicional sobre el usuario. Por ejemplo, el nodo de recuperacion episodica podria filtrar las memorias solo por las conversaciones de ese usuario especifico. El nodo de generacion de resumen podria personalizar el tono de las respuestas segun las preferencias guardadas.

### Beneficios de Este Enfoque

Esta arquitectura sigue las mejores practicas de LangGraph para sistemas multiusuario. Usa el numero de telefono como identificador natural, aprovechando lo que WhatsApp ya proporciona. No requiere que los usuarios se registren manualmente ni recuerden credenciales.

La separacion en un nodo dedicado hace el codigo mas limpio y facil de mantener. Si en el futuro se necesita cambiar la logica de identificacion, solo se modifica este nodo sin afectar al resto del sistema.

El auto-registro elimina friccion para usuarios nuevos. Pueden empezar a usar el sistema inmediatamente sin pasos adicionales, y su perfil se va completando con el tiempo a medida que interactuan.

### Consideraciones para la Implementacion

La variable con el numero del administrador deberia guardarse en las variables de entorno del sistema, no directamente en el codigo. Esto permite cambiar el administrador sin tener que modificar archivos de codigo.

Las consultas a la base de datos deben ser eficientes ya que se ejecutaran en cada mensaje. El indice en el campo de numero de telefono garantiza busquedas rapidas incluso con miles de usuarios.

El campo de preferencias usa formato JSON, lo que permite agregar nuevas configuraciones en el futuro sin modificar la estructura de la tabla. Esto da flexibilidad para evolucionar el sistema.
