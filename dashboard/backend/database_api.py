"""
Database API - Endpoints para explorar PostgreSQL desde el Dashboard

Proporciona:
- Lista de tablas
- Datos de tablas con paginación
- Información de foreign keys
- Datos de vectores para visualización 3D
- Decodificación de blobs msgpack
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

# Configuración de conexión
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5434/agente_whatsapp")

print(f"[DEBUG] Dashboard Backend - DATABASE_URL: {DATABASE_URL}")

router = APIRouter(prefix="/api/database", tags=["Database"])


# Modelos para requests
class DecodeBlobRequest(BaseModel):
    table_name: str
    thread_id: Optional[str] = None
    channel: Optional[str] = None
    version: Optional[str] = None
    checkpoint_id: Optional[str] = None


def get_connection():
    """Obtiene conexión a PostgreSQL."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def decode_langchain_exttype(ext_data: bytes) -> dict:
    """
    Decodifica un ExtType de msgpack que contiene un mensaje de LangChain.
    El formato interno es otro msgpack con la estructura del mensaje.
    """
    try:
        # El data dentro del ExtType es otro msgpack
        inner = msgpack.unpackb(ext_data, raw=False, strict_map_key=False)
        
        # Estructura típica: [module_path, class_name, data_dict, ...]
        if isinstance(inner, (list, tuple)) and len(inner) >= 3:
            # inner[0] = module path (e.g., 'langchain_core.messages.human')
            # inner[1] = class name (e.g., 'HumanMessage')
            # inner[2] = dict con el contenido
            module_path = inner[0] if isinstance(inner[0], str) else inner[0].decode('utf-8') if isinstance(inner[0], bytes) else str(inner[0])
            class_name = inner[1] if isinstance(inner[1], str) else inner[1].decode('utf-8') if isinstance(inner[1], bytes) else str(inner[1])
            
            # Determinar el tipo basado en el nombre de la clase
            msg_type = 'unknown'
            if 'Human' in class_name or 'human' in module_path:
                msg_type = 'human'
            elif 'AI' in class_name or 'ai' in module_path:
                msg_type = 'ai'
            elif 'System' in class_name or 'system' in module_path:
                msg_type = 'system'
            elif 'Tool' in class_name or 'tool' in module_path:
                msg_type = 'tool'
            
            # Extraer el contenido del mensaje
            if isinstance(inner[2], dict):
                content = inner[2].get('content', inner[2].get(b'content', ''))
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='replace')
                
                name = inner[2].get('name', inner[2].get(b'name', ''))
                if isinstance(name, bytes):
                    name = name.decode('utf-8', errors='replace')
                
                return {
                    'type': msg_type,
                    'content': str(content) if content else '',
                    'name': str(name) if name else '',
                    'class': class_name
                }
        
        # Fallback: intentar extraer contenido de cualquier estructura
        return {'type': 'unknown', 'content': str(inner)[:200], 'raw': True}
        
    except Exception as e:
        return {'type': 'error', 'content': f'Error decoding: {str(e)[:100]}'}


def decode_msgpack_messages(blob: bytes) -> list:
    """
    Decodifica un blob msgpack que puede contener mensajes de LangChain
    envueltos en ExtType.
    """
    if not MSGPACK_AVAILABLE:
        return []
    
    try:
        # Decodificar el blob principal
        decoded = msgpack.unpackb(blob, raw=False, strict_map_key=False)
        
        messages = []
        
        if isinstance(decoded, list):
            for item in decoded:
                # Verificar si es un ExtType (mensajes de LangChain)
                if hasattr(item, 'code') and hasattr(item, 'data'):
                    # Es un ExtType
                    msg = decode_langchain_exttype(item.data)
                    if msg.get('content'):
                        messages.append(msg)
                elif isinstance(item, dict):
                    # Dict normal
                    content = item.get('content', '')
                    if isinstance(content, bytes):
                        content = content.decode('utf-8', errors='replace')
                    if content:
                        messages.append({
                            'type': item.get('type', 'unknown'),
                            'content': str(content),
                            'name': item.get('name', '')
                        })
        elif isinstance(decoded, dict):
            content = decoded.get('content', '')
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            if content:
                messages.append({
                    'type': decoded.get('type', 'unknown'),
                    'content': str(content),
                    'name': decoded.get('name', '')
                })
        
        return messages
        
    except Exception as e:
        return [{'type': 'error', 'content': f'Decode error: {str(e)[:100]}'}]


def decode_msgpack_content(blob: bytes) -> Any:
    """Decodifica contenido msgpack a Python objects."""
    if not MSGPACK_AVAILABLE:
        return {"error": "msgpack not installed"}
    
    try:
        # Intentar decodificar con diferentes opciones
        result = msgpack.unpackb(blob, raw=False, strict_map_key=False)
        # Asegurarse de que todo sea serializable
        return convert_bytes_to_str(result)
    except Exception as e:
        try:
            # Intentar con raw=True
            result = msgpack.unpackb(blob, raw=True)
            # Convertir bytes a strings si es posible
            return convert_bytes_to_str(result)
        except:
            return {"error": f"Could not decode msgpack: {str(e)}"}


def convert_bytes_to_str(obj: Any) -> Any:
    """Convierte bytes a strings recursivamente, manejando objetos complejos."""
    if obj is None:
        return None
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except:
            return f"<binary {len(obj)} bytes>"
    elif isinstance(obj, dict):
        return {convert_bytes_to_str(k): convert_bytes_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_bytes_to_str(item) for item in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, '__dict__'):
        # Objetos con atributos
        return {k: convert_bytes_to_str(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    return obj


def serialize_value(value: Any) -> Any:
    """Serializa valores para JSON."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return f"<binary {len(value)} bytes>"
    if isinstance(value, (list, dict)):
        return value
    return value


@router.get("/tables")
async def list_tables() -> Dict[str, Any]:
    """
    Lista todas las tablas en la base de datos con información básica.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Obtener tablas del esquema public
                cur.execute("""
                    SELECT 
                        t.table_name,
                        t.table_type,
                        COALESCE(
                            (SELECT reltuples::bigint 
                             FROM pg_class 
                             WHERE relname = t.table_name),
                            0
                        ) as estimated_rows,
                        obj_description(
                            (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass, 
                            'pg_class'
                        ) as description
                    FROM information_schema.tables t
                    WHERE t.table_schema = 'public'
                    AND t.table_type IN ('BASE TABLE', 'VIEW')
                    ORDER BY t.table_name
                """)
                tables = cur.fetchall()
                
                # Obtener conteo real para tablas pequeñas
                result = []
                for table in tables:
                    table_info = dict(table)
                    table_name = table['table_name']
                    
                    # Para tablas con pocos registros estimados, contar exactamente
                    if table['estimated_rows'] < 10000:
                        try:
                            cur.execute(f'SELECT COUNT(*) as count FROM "{table_name}"')
                            count_result = cur.fetchone()
                            table_info['row_count'] = count_result['count'] if count_result else 0
                        except:
                            table_info['row_count'] = table['estimated_rows']
                    else:
                        table_info['row_count'] = table['estimated_rows']
                    
                    result.append(table_info)
                
                return {
                    "success": True,
                    "tables": result,
                    "total": len(result)
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/schema")
async def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    Obtiene el esquema de una tabla: columnas, tipos, constraints y foreign keys.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Obtener columnas
                cur.execute("""
                    SELECT 
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        c.character_maximum_length,
                        c.numeric_precision,
                        c.ordinal_position
                    FROM information_schema.columns c
                    WHERE c.table_schema = 'public' 
                    AND c.table_name = %s
                    ORDER BY c.ordinal_position
                """, (table_name,))
                columns = cur.fetchall()
                
                if not columns:
                    raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
                
                # Obtener primary keys
                cur.execute("""
                    SELECT a.attname as column_name
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = %s::regclass
                    AND i.indisprimary
                """, (table_name,))
                pk_columns = [row['column_name'] for row in cur.fetchall()]
                
                # Obtener foreign keys
                cur.execute("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name,
                        tc.constraint_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = %s
                """, (table_name,))
                foreign_keys = cur.fetchall()
                
                # Construir respuesta
                columns_info = []
                for col in columns:
                    col_info = dict(col)
                    col_info['is_primary_key'] = col['column_name'] in pk_columns
                    
                    # Buscar FK para esta columna
                    fk = next((fk for fk in foreign_keys if fk['column_name'] == col['column_name']), None)
                    if fk:
                        col_info['foreign_key'] = {
                            'table': fk['foreign_table_name'],
                            'column': fk['foreign_column_name'],
                            'constraint': fk['constraint_name']
                        }
                    else:
                        col_info['foreign_key'] = None
                    
                    columns_info.append(col_info)
                
                return {
                    "success": True,
                    "table_name": table_name,
                    "columns": columns_info,
                    "primary_keys": pk_columns,
                    "foreign_keys": [dict(fk) for fk in foreign_keys]
                }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/data")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    order_by: Optional[str] = None,
    order_dir: str = Query("asc", pattern="^(asc|desc)$")
) -> Dict[str, Any]:
    """
    Obtiene datos de una tabla con paginación.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Verificar que la tabla existe
                cur.execute("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                """, (table_name,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
                
                # Obtener total de registros
                cur.execute(f'SELECT COUNT(*) as total FROM "{table_name}"')
                total = cur.fetchone()['total']
                
                # Construir query con paginación
                offset = (page - 1) * page_size
                
                if order_by:
                    # Validar que la columna existe
                    cur.execute("""
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = %s AND column_name = %s
                    """, (table_name, order_by))
                    if cur.fetchone():
                        query = f'SELECT * FROM "{table_name}" ORDER BY "{order_by}" {order_dir} LIMIT %s OFFSET %s'
                    else:
                        query = f'SELECT * FROM "{table_name}" LIMIT %s OFFSET %s'
                else:
                    query = f'SELECT * FROM "{table_name}" LIMIT %s OFFSET %s'
                
                cur.execute(query, (page_size, offset))
                rows = cur.fetchall()
                
                # Serializar datos
                data = []
                for row in rows:
                    serialized_row = {}
                    for key, value in row.items():
                        serialized_row[key] = serialize_value(value)
                    data.append(serialized_row)
                
                return {
                    "success": True,
                    "table_name": table_name,
                    "data": data,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_rows": total,
                        "total_pages": (total + page_size - 1) // page_size
                    }
                }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/row/{row_id}")
async def get_row_by_id(
    table_name: str,
    row_id: int,
    id_column: str = Query("id", description="Column name for ID")
) -> Dict[str, Any]:
    """
    Obtiene una fila específica por su ID.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT * FROM "{table_name}" WHERE "{id_column}" = %s', (row_id,))
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail=f"Row not found")
                
                serialized_row = {}
                for key, value in row.items():
                    serialized_row[key] = serialize_value(value)
                
                return {
                    "success": True,
                    "table_name": table_name,
                    "data": serialized_row
                }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vectors")
async def get_vectors(
    limit: int = Query(500, ge=1, le=2000),
    table: str = Query("memoria_episodica", description="Table with vector embeddings")
) -> Dict[str, Any]:
    """
    Obtiene vectores para visualización 3D.
    Usa primeros 3 componentes para 3D (idealmente usaríamos PCA/UMAP).
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Tablas con vectores - orden de prioridad
                vector_tables = [
                    ("memoria_episodica", "embedding", "resumen", "metadata"),
                    ("historiales_medicos", "embedding", "contenido", "metadata"),
                    ("memory_store", "embedding", "content", "metadata"),
                    ("langchain_pg_embedding", "embedding", "document", "cmetadata"),
                ]
                
                # Buscar tabla que exista y tenga datos
                selected_table = None
                for tbl, emb_col, text_col, meta_col in vector_tables:
                    cur.execute("""
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    """, (tbl,))
                    if cur.fetchone():
                        # Verificar si tiene registros con embeddings
                        cur.execute(f'SELECT COUNT(*) as cnt FROM "{tbl}" LIMIT 1')
                        count_result = cur.fetchone()
                        if count_result and count_result['cnt'] > 0:
                            selected_table = (tbl, emb_col, text_col, meta_col)
                            break
                        else:
                            # Tabla existe pero está vacía, continuar buscando
                            continue
                
                if not selected_table:
                    # No hay vectores, devolver datos de ejemplo para demo
                    import math
                    example_vectors = []
                    for i in range(50):
                        angle = (i / 50) * 2 * math.pi
                        example_vectors.append({
                            "id": f"example_{i}",
                            "x": math.cos(angle) * 30 + (i % 5) * 10,
                            "y": math.sin(angle) * 30 + (i // 10) * 5,
                            "z": (i % 10) * 5 - 25,
                            "label": f"Ejemplo memoria {i+1}",
                            "metadata": {"type": "example", "index": i}
                        })
                    return {
                        "success": True,
                        "vectors": example_vectors,
                        "total": len(example_vectors),
                        "message": "No hay vectores reales, mostrando datos de ejemplo",
                        "is_example": True
                    }
                
                tbl, emb_col, text_col, meta_col = selected_table
                
                # Verificar si la columna de embedding existe y es vector
                cur.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{tbl}' AND column_name = '{emb_col}'
                """)
                col_info = cur.fetchone()
                
                if not col_info:
                    return {
                        "success": True,
                        "vectors": [],
                        "total": 0,
                        "message": f"Embedding column '{emb_col}' not found in '{tbl}'"
                    }
                
                # Obtener vectores - usar primeros 3 componentes como coordenadas 3D
                # Para vectores reales, deberíamos usar PCA, pero por simplicidad usamos primeros 3
                try:
                    cur.execute(f"""
                        SELECT 
                            COALESCE(id::text, md5(random()::text)) as id,
                            {emb_col}[1:3] as coords,
                            LEFT({text_col}::text, 100) as label,
                            {meta_col}::text as metadata
                        FROM "{tbl}"
                        WHERE {emb_col} IS NOT NULL
                        LIMIT %s
                    """, (limit,))
                except:
                    # Fallback si la sintaxis de array no funciona
                    cur.execute(f"""
                        SELECT 
                            COALESCE(id::text, md5(random()::text)) as id,
                            {emb_col}::text as embedding_raw,
                            LEFT({text_col}::text, 100) as label,
                            {meta_col}::text as metadata
                        FROM "{tbl}"
                        WHERE {emb_col} IS NOT NULL
                        LIMIT %s
                    """, (limit,))
                
                rows = cur.fetchall()
                
                vectors = []
                for row in rows:
                    try:
                        # Intentar parsear coordenadas
                        if 'coords' in row and row['coords']:
                            coords = row['coords']
                            if isinstance(coords, str):
                                coords = json.loads(coords.replace('{', '[').replace('}', ']'))
                            x, y, z = coords[0] if len(coords) > 0 else 0, coords[1] if len(coords) > 1 else 0, coords[2] if len(coords) > 2 else 0
                        elif 'embedding_raw' in row:
                            # Parsear el embedding raw
                            emb_str = row['embedding_raw']
                            if emb_str.startswith('['):
                                coords = json.loads(emb_str)
                            else:
                                coords = [float(x) for x in emb_str.strip('{}[]').split(',')[:3]]
                            x, y, z = coords[0] if len(coords) > 0 else 0, coords[1] if len(coords) > 1 else 0, coords[2] if len(coords) > 2 else 0
                        else:
                            continue
                        
                        # Escalar para visualización
                        scale = 50
                        vectors.append({
                            "id": row['id'],
                            "x": float(x) * scale,
                            "y": float(y) * scale,
                            "z": float(z) * scale,
                            "label": row.get('label', '')[:50],
                            "metadata": row.get('metadata')
                        })
                    except Exception as e:
                        continue
                
                return {
                    "success": True,
                    "table": tbl,
                    "vectors": vectors,
                    "total": len(vectors)
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships")
async def get_table_relationships() -> Dict[str, Any]:
    """
    Obtiene todas las relaciones (FKs) entre tablas para visualización.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        tc.table_name as source_table,
                        kcu.column_name as source_column,
                        ccu.table_name AS target_table,
                        ccu.column_name AS target_column,
                        tc.constraint_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    ORDER BY tc.table_name, kcu.column_name
                """)
                relationships = cur.fetchall()
                
                return {
                    "success": True,
                    "relationships": [dict(r) for r in relationships],
                    "total": len(relationships)
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_database_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas generales de la base de datos.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Tamaño de la base de datos
                cur.execute("SELECT pg_size_pretty(pg_database_size(current_database())) as size")
                db_size = cur.fetchone()['size']
                
                # Conteo de tablas
                cur.execute("""
                    SELECT COUNT(*) as count FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
                table_count = cur.fetchone()['count']
                
                # Conteo de índices
                cur.execute("""
                    SELECT COUNT(*) as count FROM pg_indexes 
                    WHERE schemaname = 'public'
                """)
                index_count = cur.fetchone()['count']
                
                # Conexiones activas
                cur.execute("SELECT count(*) as count FROM pg_stat_activity WHERE state = 'active'")
                active_connections = cur.fetchone()['count']
                
                return {
                    "success": True,
                    "stats": {
                        "database_size": db_size,
                        "table_count": table_count,
                        "index_count": index_count,
                        "active_connections": active_connections
                    }
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decode-blob")
async def decode_blob(request: DecodeBlobRequest) -> Dict[str, Any]:
    """
    Decodifica un blob binario (msgpack) de checkpoint_blobs o checkpoint_writes.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                blob_data = None
                source_info = {}
                
                if request.table_name == 'checkpoint_blobs' and request.thread_id and request.channel:
                    # Buscar en checkpoint_blobs
                    cur.execute("""
                        SELECT blob, type, channel, version
                        FROM checkpoint_blobs
                        WHERE thread_id = %s AND channel = %s
                        ORDER BY version DESC
                        LIMIT 1
                    """, (request.thread_id, request.channel))
                    row = cur.fetchone()
                    if row:
                        blob_data = row['blob']
                        source_info = {
                            "type": row['type'],
                            "channel": row['channel'],
                            "version": row['version']
                        }
                        
                elif request.table_name == 'checkpoint_writes' and request.thread_id:
                    # Buscar en checkpoint_writes
                    cur.execute("""
                        SELECT blob, type, channel, task_id
                        FROM checkpoint_writes
                        WHERE thread_id = %s
                        ORDER BY idx DESC
                        LIMIT 1
                    """, (request.thread_id,))
                    row = cur.fetchone()
                    if row:
                        blob_data = row['blob']
                        source_info = {
                            "type": row['type'],
                            "channel": row['channel'],
                            "task_id": row['task_id']
                        }
                        
                elif request.table_name == 'checkpoints' and request.thread_id:
                    # Para checkpoints, el campo checkpoint ya es JSONB
                    cur.execute("""
                        SELECT checkpoint, metadata
                        FROM checkpoints
                        WHERE thread_id = %s
                        ORDER BY checkpoint_id DESC
                        LIMIT 1
                    """, (request.thread_id,))
                    row = cur.fetchone()
                    if row:
                        return {
                            "success": True,
                            "decoded": {
                                "checkpoint": row['checkpoint'],
                                "metadata": row['metadata']
                            },
                            "source": "checkpoints (JSONB)"
                        }
                
                if blob_data is None:
                    return {
                        "success": False,
                        "error": "No blob found with given parameters"
                    }
                
                # Decodificar msgpack
                decoded = decode_msgpack_content(blob_data)
                
                # Extraer mensajes si existen
                if isinstance(decoded, dict):
                    # Buscar mensajes en diferentes formatos
                    messages = None
                    if 'messages' in decoded:
                        messages = decoded['messages']
                    elif 'data' in decoded and isinstance(decoded['data'], list):
                        messages = decoded['data']
                    
                    if messages:
                        # Formatear mensajes de LangChain
                        formatted_messages = []
                        for msg in messages:
                            if isinstance(msg, dict):
                                formatted_msg = {
                                    "type": msg.get('type', msg.get('role', 'unknown')),
                                    "content": msg.get('content', msg.get('text', '')),
                                    "name": msg.get('name', msg.get('sender', None))
                                }
                                # Agregar metadatos adicionales si existen
                                if 'additional_kwargs' in msg:
                                    formatted_msg['additional'] = msg['additional_kwargs']
                                formatted_messages.append(formatted_msg)
                            else:
                                formatted_messages.append({"content": str(msg)})
                        
                        return {
                            "success": True,
                            "decoded": formatted_messages,
                            "source": source_info,
                            "message_count": len(formatted_messages)
                        }
                
                return {
                    "success": True,
                    "decoded": decoded,
                    "source": source_info
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# ENDPOINTS DE GESTIÓN DE USUARIOS (PACIENTES/DOCTORES)
# ============================================================================

class SearchUsersRequest(BaseModel):
    search_term: str
    search_type: str = "all"  # "all", "name", "id", "phone"
    user_type: str = "pacientes"  # "pacientes" o "doctores"


class DeleteUsersRequest(BaseModel):
    user_ids: List[int]
    user_type: str  # "pacientes" o "doctores"
    include_related: bool = False  # Si borrar datos relacionados (vectores, citas, etc.)


@router.post("/users/search")
async def search_users(request: SearchUsersRequest) -> Dict[str, Any]:
    """
    Busca pacientes o doctores por nombre, id o teléfono.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                search_term = request.search_term.strip()
                
                if request.user_type == "pacientes":
                    # Construir query para pacientes
                    conditions = []
                    params = []
                    
                    if request.search_type in ["all", "name"]:
                        conditions.append("LOWER(p.nombre_completo) LIKE LOWER(%s)")
                        params.append(f"%{search_term}%")
                    
                    if request.search_type in ["all", "id"]:
                        try:
                            id_val = int(search_term)
                            conditions.append("p.id = %s")
                            params.append(id_val)
                        except ValueError:
                            pass
                    
                    if request.search_type in ["all", "phone"]:
                        conditions.append("p.telefono LIKE %s")
                        params.append(f"%{search_term}%")
                    
                    if not conditions:
                        conditions = ["1=0"]
                    
                    query = f"""
                        SELECT 
                            p.id, 
                            p.nombre_completo, 
                            p.telefono, 
                            p.email,
                            p.doctor_id,
                            d.nombre_completo as doctor_nombre,
                            p.created_at,
                            (SELECT COUNT(*) FROM citas_medicas WHERE paciente_id = p.id) as total_citas,
                            (SELECT COUNT(*) FROM historiales_medicos WHERE paciente_id = p.id) as total_historiales
                        FROM pacientes p
                        LEFT JOIN doctores d ON p.doctor_id = d.id
                        WHERE {" OR ".join(conditions)}
                        ORDER BY p.nombre_completo
                        LIMIT 100
                    """
                    
                    cur.execute(query, params)
                    
                else:  # doctores
                    conditions = []
                    params = []
                    
                    if request.search_type in ["all", "name"]:
                        conditions.append("LOWER(d.nombre_completo) LIKE LOWER(%s)")
                        params.append(f"%{search_term}%")
                    
                    if request.search_type in ["all", "id"]:
                        try:
                            id_val = int(search_term)
                            conditions.append("d.id = %s")
                            params.append(id_val)
                        except ValueError:
                            pass
                    
                    if request.search_type in ["all", "phone"]:
                        conditions.append("d.phone_number LIKE %s")
                        params.append(f"%{search_term}%")
                    
                    if not conditions:
                        conditions = ["1=0"]
                    
                    query = f"""
                        SELECT 
                            d.id, 
                            d.nombre_completo, 
                            d.phone_number as telefono, 
                            d.especialidad,
                            d.created_at,
                            (SELECT COUNT(*) FROM pacientes WHERE doctor_id = d.id) as total_pacientes,
                            (SELECT COUNT(*) FROM citas_medicas WHERE doctor_id = d.id) as total_citas
                        FROM doctores d
                        WHERE {" OR ".join(conditions)}
                        ORDER BY d.nombre_completo
                        LIMIT 100
                    """
                    
                    cur.execute(query, params)
                
                results = cur.fetchall()
                
                return {
                    "success": True,
                    "users": [dict(row) for row in results],
                    "total": len(results),
                    "user_type": request.user_type
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/all/{user_type}")
async def get_all_users(user_type: str) -> Dict[str, Any]:
    """
    Obtiene todos los pacientes o doctores.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if user_type == "pacientes":
                    cur.execute("""
                        SELECT 
                            p.id, 
                            p.nombre_completo, 
                            p.telefono, 
                            p.email,
                            p.doctor_id,
                            d.nombre_completo as doctor_nombre,
                            p.created_at,
                            (SELECT COUNT(*) FROM citas_medicas WHERE paciente_id = p.id) as total_citas,
                            (SELECT COUNT(*) FROM historiales_medicos WHERE paciente_id = p.id) as total_historiales
                        FROM pacientes p
                        LEFT JOIN doctores d ON p.doctor_id = d.id
                        ORDER BY p.nombre_completo
                    """)
                else:
                    cur.execute("""
                        SELECT 
                            d.id, 
                            d.nombre_completo, 
                            d.phone_number as telefono, 
                            d.especialidad,
                            d.created_at,
                            (SELECT COUNT(*) FROM pacientes WHERE doctor_id = d.id) as total_pacientes,
                            (SELECT COUNT(*) FROM citas_medicas WHERE doctor_id = d.id) as total_citas
                        FROM doctores d
                        ORDER BY d.nombre_completo
                    """)
                
                results = cur.fetchall()
                
                return {
                    "success": True,
                    "users": [dict(row) for row in results],
                    "total": len(results),
                    "user_type": user_type
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/delete")
async def delete_users(request: DeleteUsersRequest) -> Dict[str, Any]:
    """
    Elimina usuarios (pacientes o doctores) y opcionalmente sus datos relacionados.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                deleted_count = 0
                related_deleted = {
                    "citas": 0,
                    "historiales": 0,
                    "memoria_episodica": 0,
                    "disponibilidad": 0,
                    "metricas": 0,
                    "reportes": 0
                }
                
                for user_id in request.user_ids:
                    try:
                        if request.user_type == "pacientes":
                            # Primero eliminar datos relacionados si está habilitado
                            if request.include_related:
                                # Eliminar citas médicas
                                cur.execute("DELETE FROM citas_medicas WHERE paciente_id = %s", (user_id,))
                                related_deleted["citas"] += cur.rowcount
                                
                                # Eliminar historiales médicos (incluye vectores)
                                cur.execute("DELETE FROM historiales_medicos WHERE paciente_id = %s", (user_id,))
                                related_deleted["historiales"] += cur.rowcount
                            
                            # Eliminar paciente
                            cur.execute("DELETE FROM pacientes WHERE id = %s", (user_id,))
                            if cur.rowcount > 0:
                                deleted_count += 1
                                
                        else:  # doctores
                            if request.include_related:
                                # Primero desasociar pacientes (no eliminarlos)
                                cur.execute("UPDATE pacientes SET doctor_id = NULL WHERE doctor_id = %s", (user_id,))
                                
                                # Eliminar citas
                                cur.execute("DELETE FROM citas_medicas WHERE doctor_id = %s", (user_id,))
                                related_deleted["citas"] += cur.rowcount
                                
                                # Eliminar disponibilidad
                                cur.execute("DELETE FROM disponibilidad_medica WHERE doctor_id = %s", (user_id,))
                                related_deleted["disponibilidad"] += cur.rowcount
                                
                                # Eliminar métricas
                                cur.execute("DELETE FROM metricas_consultas WHERE doctor_id = %s", (user_id,))
                                related_deleted["metricas"] += cur.rowcount
                                
                                # Eliminar reportes
                                cur.execute("DELETE FROM reportes_generados WHERE doctor_id = %s", (user_id,))
                                related_deleted["reportes"] += cur.rowcount
                                
                                # Eliminar control de turnos
                                cur.execute("DELETE FROM control_turnos WHERE ultimo_doctor_id = %s", (user_id,))
                            
                            # Eliminar doctor
                            cur.execute("DELETE FROM doctores WHERE id = %s", (user_id,))
                            if cur.rowcount > 0:
                                deleted_count += 1
                                
                    except Exception as e:
                        # Continuar con el siguiente si hay error (puede ser FK constraint)
                        print(f"Error deleting user {user_id}: {e}")
                        continue
                
                conn.commit()
                
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "related_deleted": related_deleted,
                    "message": f"Se eliminaron {deleted_count} {request.user_type}"
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/related-data/{user_type}/{user_id}")
async def get_related_data_count(user_type: str, user_id: int) -> Dict[str, Any]:
    """
    Obtiene conteo de datos relacionados para un usuario.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                counts = {}
                
                if user_type == "pacientes":
                    cur.execute("SELECT COUNT(*) as count FROM citas_medicas WHERE paciente_id = %s", (user_id,))
                    counts["citas"] = cur.fetchone()["count"]
                    
                    cur.execute("SELECT COUNT(*) as count FROM historiales_medicos WHERE paciente_id = %s", (user_id,))
                    counts["historiales"] = cur.fetchone()["count"]
                    
                else:  # doctores
                    cur.execute("SELECT COUNT(*) as count FROM pacientes WHERE doctor_id = %s", (user_id,))
                    counts["pacientes"] = cur.fetchone()["count"]
                    
                    cur.execute("SELECT COUNT(*) as count FROM citas_medicas WHERE doctor_id = %s", (user_id,))
                    counts["citas"] = cur.fetchone()["count"]
                    
                    cur.execute("SELECT COUNT(*) as count FROM disponibilidad_medica WHERE doctor_id = %s", (user_id,))
                    counts["disponibilidad"] = cur.fetchone()["count"]
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "user_type": user_type,
                    "related_counts": counts
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vectors/delete-by-user")
async def delete_vectors_by_user(user_type: str, user_ids: str) -> Dict[str, Any]:
    """
    Elimina vectores/embeddings asociados a usuarios específicos.
    user_ids es una cadena separada por comas.
    """
    try:
        ids = [int(x.strip()) for x in user_ids.split(",") if x.strip()]
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                deleted = {"memoria_episodica": 0, "historiales": 0}
                
                if user_type == "pacientes":
                    # Eliminar de historiales_medicos (tienen embedding)
                    if ids:
                        cur.execute(
                            "DELETE FROM historiales_medicos WHERE paciente_id = ANY(%s::int[])", 
                            (ids,)
                        )
                        deleted["historiales"] = cur.rowcount
                
                # Eliminar de memoria_episodica basándose en user_id
                # Nota: El user_id en memoria_episodica es el phone_number/chat_id
                
                conn.commit()
                
                return {
                    "success": True,
                    "deleted": deleted,
                    "message": f"Vectores eliminados para {len(ids)} usuarios"
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory-vectors")
async def get_memory_vectors(
    limit: int = Query(500, ge=1, le=2000),
    user_id: str = Query(None, description="Filtrar por usuario específico"),
    tipo_usuario: str = Query(None, description="Filtrar: paciente o doctor"),
    categoria: str = Query(None, description="Filtrar por categoría")
) -> Dict[str, Any]:
    """
    Obtiene vectores de MEMORIA EPISÓDICA para visualización 3D estilo TensorFlow Projector.
    
    Características:
    - Agrupación por usuario (vectores del mismo usuario cercanos)
    - Colores por tipo: azul=paciente, blanco=doctor
    - Clustering temporal (fechas cercanas = vectores cercanos)
    - Metadata completa para tooltips y panel de detalles
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Query corregida usando solo columnas que existen en la tabla
                cur.execute("""
                    SELECT 
                        id,
                        user_id,
                        resumen,
                        embedding,
                        metadata,
                        timestamp
                    FROM memoria_episodica
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
                
                memorias = cur.fetchall()
                
                if not memorias:
                    return {
                        "success": True,
                        "vectors": [],
                        "total": 0,
                        "message": "No hay memorias episódicas en la base de datos"
                    }
                
                # Agrupar por usuario para calcular offsets de clustering
                import math
                usuarios_vistos = {}
                vectors = []
                
                for idx, mem in enumerate(memorias):
                    user = mem['user_id']
                    user_short = user[:8] if user else f"user_{idx}"
                    
                    # Extraer info desde metadata si existe
                    metadata = mem.get('metadata', {}) or {}
                    
                    # Calcular posición del grupo (usuarios diferentes en círculos diferentes)
                    if user not in usuarios_vistos:
                        grupo_idx = len(usuarios_vistos)
                        # Espiral para grupos
                        angulo_grupo = (grupo_idx / max(len(set(m['user_id'] for m in memorias)), 1)) * 2 * math.pi
                        usuarios_vistos[user] = {
                            'offset_x': 30 * math.cos(angulo_grupo),
                            'offset_z': 30 * math.sin(angulo_grupo),
                            'count': 0
                        }
                    
                    grupo_info = usuarios_vistos[user]
                    grupo_info['count'] += 1
                    
                    # Generar coordenadas basadas en hash del user_id
                    x_base = hash(user) % 100 - 50
                    y_base = hash(mem['resumen'][:20]) % 100 - 50
                    z_base = hash(str(mem['timestamp'])) % 100 - 50
                    
                    # Agregar a la lista de vectores
                    vectors.append(vector_data)
                
                # Estadísticas por grupo
                grupos_stats = {
                    grupo: info['count'] 
                    for grupo, info in usuarios_vistos.items()
                }
                
                return {
                    "success": True,
                    "vectors": vectors,
                    "total": len(vectors),
                    "table": "memoria_episodica",
                    "is_real_data": True,
                    "grupos": grupos_stats,
                    "tipos": {
                        "pacientes": sum(1 for v in vectors if v['tipo_usuario'] == 'paciente'),
                        "doctores": sum(1 for v in vectors if v['tipo_usuario'] != 'paciente')
                    }
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "vectors": [],
            "total": 0
        }


@router.get("/user-vectors/{user_id}")
async def get_user_vectors(
    user_id: str,
    include_neighbors: bool = Query(True, description="Incluir vectores semánticamente cercanos")
) -> Dict[str, Any]:
    """
    Obtiene todos los vectores de un usuario específico y opcionalmente sus vecinos semánticos.
    Para iluminar vectores relacionados al hacer clic.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Vectores del usuario
                cur.execute("""
                    SELECT 
                        id,
                        resumen,
                        categoria,
                        fecha_evento,
                        timestamp,
                        embedding
                    FROM memoria_episodica
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                """, (user_id,))
                
                user_vectors = cur.fetchall()
                
                if not user_vectors:
                    return {
                        "success": True,
                        "user_vectors": [],
                        "neighbor_vectors": [],
                        "total": 0
                    }
                
                user_ids = [str(v['id']) for v in user_vectors]
                
                neighbor_ids = []
                if include_neighbors and user_vectors:
                    # Buscar vecinos semánticos del primer vector del usuario
                    first_embedding = user_vectors[0]['embedding']
                    if first_embedding:
                        cur.execute("""
                            SELECT id
                            FROM memoria_episodica
                            WHERE user_id != %s
                            ORDER BY embedding <=> %s
                            LIMIT 10
                        """, (user_id, first_embedding))
                        neighbor_ids = [str(r['id']) for r in cur.fetchall()]
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "user_vectors": user_ids,
                    "neighbor_vectors": neighbor_ids,
                    "total": len(user_ids)
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "user_vectors": [],
            "neighbor_vectors": []
        }


@router.get("/conversation-vectors")
async def get_conversation_vectors(
    limit: int = Query(200, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Obtiene datos de conversaciones ÚNICAS para visualización 3D.
    Agrupa por thread_id y obtiene el blob más grande (con más mensajes) de cada uno.
    NO incluye datos mock ni placeholder - solo datos reales de la base de datos.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Obtener el blob más grande de cada thread_id (contiene más mensajes)
                cur.execute("""
                    WITH ranked_blobs AS (
                        SELECT 
                            cb.thread_id,
                            cb.channel,
                            cb.version,
                            cb.blob,
                            LENGTH(cb.blob) as blob_size,
                            c.metadata,
                            c.checkpoint_id,
                            ROW_NUMBER() OVER (
                                PARTITION BY cb.thread_id 
                                ORDER BY LENGTH(cb.blob) DESC
                            ) as rn
                        FROM checkpoint_blobs cb
                        LEFT JOIN checkpoints c ON cb.thread_id = c.thread_id 
                            AND cb.version = c.checkpoint_id
                        WHERE cb.channel = 'messages'
                    )
                    SELECT thread_id, channel, version, blob, blob_size, metadata, checkpoint_id
                    FROM ranked_blobs
                    WHERE rn = 1
                    ORDER BY thread_id
                    LIMIT %s
                """, (limit,))
                
                conversations = cur.fetchall()
                
                if not conversations:
                    return {
                        "success": True,
                        "vectors": [],
                        "total": 0,
                        "message": "No hay conversaciones en la base de datos"
                    }
                
                vectors = []
                import math
                
                for idx, conv in enumerate(conversations):
                    thread_id = conv['thread_id']
                    
                    # Generar posición 3D basada en hash del thread_id completo
                    thread_hash = hash(thread_id)
                    
                    # Distribuir en espiral 3D única para cada thread
                    angle = (idx / max(len(conversations), 1)) * 4 * math.pi
                    radius = 20 + ((thread_hash % 5)) * 10
                    
                    x = radius * math.cos(angle)
                    y = ((thread_hash >> 8) % 100) - 50  # Variación vertical basada en hash
                    z = radius * math.sin(angle)
                    
                    # Extraer metadatos reales
                    metadata = conv.get('metadata', {}) or {}
                    step = metadata.get('step', -1) if isinstance(metadata, dict) else -1
                    
                    # Decodificar mensajes del blob
                    messages = []
                    last_message = ""
                    message_count = 0
                    
                    if conv.get('blob') and MSGPACK_AVAILABLE:
                        try:
                            blob_data = bytes(conv['blob']) if not isinstance(conv['blob'], bytes) else conv['blob']
                            messages = decode_msgpack_messages(blob_data)
                            message_count = len(messages)
                            
                            # Obtener el último mensaje como preview
                            if messages:
                                for msg in reversed(messages):
                                    if msg.get('content') and msg.get('type') != 'error':
                                        last_message = msg['content']
                                        break
                        except Exception as e:
                            messages = [{"type": "error", "content": f"Error decodificando: {str(e)[:50]}"}]
                    
                    # Crear preview del mensaje - NO usar texto placeholder si no hay mensaje
                    if last_message:
                        preview = last_message[:80] + ('...' if len(last_message) > 80 else '')
                    else:
                        preview = "[Sin mensajes decodificados]"
                    
                    # Usar thread_id completo como ID único
                    vector_id = thread_id
                    
                    vectors.append({
                        "id": vector_id,
                        "vector_number": idx + 1,
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "z": round(z, 2),
                        "label": preview,
                        "message_preview": last_message[:300] if last_message else "[Sin contenido - blob vacío o formato no reconocido]",
                        "message_count": message_count,
                        "messages": messages[:20],  # Hasta 20 mensajes
                        "metadata": json.dumps({
                            "thread_id": thread_id,
                            "channel": conv['channel'],
                            "blob_size": conv['blob_size'],
                            "step": step,
                            "checkpoint_id": conv.get('checkpoint_id', '') or conv.get('version', ''),
                            "message_count": message_count
                        })
                    })
                
                return {
                    "success": True,
                    "vectors": vectors,
                    "total": len(vectors),
                    "table": "checkpoint_blobs",
                    "is_real_data": True,
                    "note": "Datos reales de conversaciones - 1 vector por thread_id único"
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "vectors": [],
            "total": 0
        }

