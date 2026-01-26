from langgraph.graph import END
from datetime import datetime
import pendulum
from langchain_core.messages import ToolMessage, HumanMessage,AnyMessage
from typing import Annotated
from langgraph.graph.message import add_messages
from typing import TypedDict
from .tool import calendar_tools,create_event_tool,list_events_tool,delete_event_tool,postpone_event_tool
from langgraph.graph import StateGraph,MessagesState, START
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json

# Importar sistema de memoria
from .memory import (
    get_memory_store,
    get_user_preferences,
    update_semantic_memory,
    log_episode,
    get_relevant_episodes,
    get_agent_instructions,
)

load_dotenv()  # this will load variables from .env into environment

import os
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
print("DEEPSEEK_API_KEY:", DEEPSEEK_API_KEY[:10] if DEEPSEEK_API_KEY else "None", "...")  # for debug
llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=DEEPSEEK_API_KEY,
    openai_api_base="https://api.deepseek.com/v1",
    temperature=0.7,
    timeout=20.0,  # ⚠️ Timeout de 20 segundos
    max_retries=0  # ✅ Reintentos los maneja LangGraph
)

# Inicializar memory store
memory_store = get_memory_store()



import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.stream.reconfigure(encoding='utf-8')
logger = logging.getLogger(__name__)

llm 

model_with_tools = llm.bind_tools(calendar_tools)


class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

def should_continue(state):
    try:
        messages = state["messages"]
        last_message = messages[-1]
        if getattr(last_message, "tool_calls", None):
            logger.info("Tool calls detected, continuing to tools node.")
            return "tools"
        logger.info("No tool calls detected, ending graph.")
        return END
    except Exception as e:
        logger.error(f"Error in should_continue: {e}")
        return END


def call_model(state):
    try:
        messages = state["messages"]
        user_id = state.get("user_id", "default_user")
        logger.info(f"Received {len(messages)} messages for user {user_id}.")

        # Find the latest ToolMessage
        latest_tool_message = next((msg for msg in reversed(messages) if isinstance(msg, ToolMessage)), None)
        latest_human_message = next((msg for msg in reversed(messages) if isinstance(msg, HumanMessage)), None)

        if latest_tool_message:
            logger.info("Latest message is a ToolMessage, invoking LLM for final response.")
            
            # Obtener instrucciones procedimentales
            system_instructions = get_agent_instructions(memory_store)
            
            prompt = (
                f"{system_instructions}\n\n"
                f"Give final response based on this tool message: {latest_tool_message}. "
                f"And also consider the user's original message: {latest_human_message}. "
                "This response created by you will be final and will be prompted to user."
            )
            response = llm.invoke(prompt)
            logger.info("LLM response received for tool message.")
            return {"messages": [response]}

        # Obtener contexto de memoria para enriquecer la respuesta
        try:
            # 1. Obtener preferencias semánticas
            preferences = get_user_preferences(memory_store, user_id)
            timezone_pref = preferences.get("user_preferences", {}).get("timezone", "America/Tijuana")
            
            # 2. Buscar episodios relevantes
            relevant_episodes = get_relevant_episodes(state, memory_store, user_id, limit=3)
            
            # 3. Obtener instrucciones procedimentales
            system_instructions = get_agent_instructions(memory_store)
            
            # Formatear contexto de episodios
            episodes_context = ""
            if relevant_episodes:
                episodes_context = "\n\nEXPERIENCIAS PASADAS RELEVANTES:\n"
                for ep in relevant_episodes[:2]:  # Solo 2 más relevantes
                    episodes_context += f"- {ep.get('action', 'unknown')}: {ep.get('context', {}).get('user_request', 'N/A')}\n"
            
            # Formatear preferencias
            prefs_context = f"\n\nPREFERENCIAS DEL USUARIO:\n- Zona horaria preferida: {timezone_pref}\n"
            preferred_times = preferences.get("user_preferences", {}).get("preferred_meeting_times", [])
            if preferred_times:
                prefs_context += f"- Horarios preferidos: {', '.join(preferred_times)}\n"
            
            logger.info(f"Memoria cargada: {len(relevant_episodes)} episodios, preferencias recuperadas")
            
        except Exception as mem_error:
            logger.warning(f"Error cargando memoria, continuando sin ella: {mem_error}")
            system_instructions = get_agent_instructions(memory_store)
            episodes_context = ""
            prefs_context = ""
            timezone_pref = "America/Tijuana"

        # Add current time information for the LLM
        current_time = pendulum.now(timezone_pref)
        current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        time_prompt = (
            f"The current date and time is {current_time_str}. "
            "Please consider this information when generating your response."
        )

        # Construir mensaje enriquecido con memoria
        enriched_system_message = f"{system_instructions}{prefs_context}{episodes_context}\n\n{time_prompt}"
        
        # Preparar mensajes con contexto enriquecido
        enriched_messages = [{"role": "system", "content": enriched_system_message}] + messages

        response = model_with_tools.invoke(enriched_messages)
        logger.info("Model with tools invoked successfully with memory context.")
        return {"messages": [response]}

    except Exception as e:
        logger.error(f"Error in call_model: {e}")
        error_message = {
            "role": "assistant",
            "content": "Sorry, an error occurred while processing your request. Please try again later."
        }
        return {"messages": [error_message]}


def tool_dispatch_node(state):
    try:
        messages = state["messages"]
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", [])
        new_messages = []
        user_id = state.get("user_id", "default_user")

        tool_map = {
            "create_event_tool": create_event_tool,
            "list_events_tool": list_events_tool,
            "postpone_event_tool": postpone_event_tool,
            "delete_event_tool": delete_event_tool,
        }

        for call in tool_calls:
            tool_name = call["name"]
            args = call["args"]
            logger.info(f"Invoking tool: {tool_name} with args: {args}")
            tool_func = tool_map.get(tool_name)
            if not tool_func:
                logger.warning(f"Tool {tool_name} not found in tool_map.")
                continue
            try:
                result = tool_func.invoke(args)
                new_messages.append(
                    ToolMessage(content=result, name=tool_name, tool_call_id=call["id"])
                )
                logger.info(f"Tool {tool_name} executed successfully.")
                
                # Registrar episodio en memoria episódica
                try:
                    log_episode(
                        state=state,
                        store=memory_store,
                        user_id=user_id,
                        action_type=tool_name,
                        additional_context={"args": args, "result": str(result)[:200]}
                    )
                except Exception as mem_error:
                    logger.warning(f"Error logging episode: {mem_error}")
                
            except Exception as tool_error:
                logger.error(f"Error executing tool {tool_name}: {tool_error}")
                error_msg = ToolMessage(
                    content=f"Error executing tool {tool_name}: {tool_error}",
                    name=tool_name,
                    tool_call_id=call["id"]
                )
                new_messages.append(error_msg)

        logger.info(f"Tool dispatch node returning {len(new_messages)} messages.")
        return {"messages": new_messages}

    except Exception as e:
        logger.error(f"Error in tool_dispatch_node: {e}")
        error_msg = ToolMessage(
            content="An error occurred while dispatching tools.",
            name="tool_dispatch_node",
            tool_call_id=None
        )
        return {"messages": [error_msg]}




builder = StateGraph(MessagesState)
builder.add_node("call_model", call_model)
builder.add_node("tools", tool_dispatch_node)
builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", should_continue, ["tools", END])
builder.add_edge("tools", "call_model")

# Compilar grafo con soporte de memoria
graph = builder.compile()


if __name__ == "__main__":
    try:
        logger.info("Starting graph invocation with test message.")
        result = graph.invoke({
            "messages": [
                {"role": "user", "content": "book a meeting tommorow 9 am"}
            ],
            "user_id": "test_user"
        })
        logger.info(f"Graph invocation result: {result}")
        print(result)
    except Exception as e:
        logger.error(f"Error during graph invocation: {e}")
        print(f"Error during graph invocation: {e}")
        print(f"Error during graph invocation: {e}")
