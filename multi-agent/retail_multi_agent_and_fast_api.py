from datetime import datetime
from langchain_community.utilities.sql_database import SQLDatabase
import json
import re
from typing import List, Dict, Any, Literal, TypedDict, Optional, Tuple, Set
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.types import Command
import os
from langchain.callbacks.tracers import LangChainTracer
import uuid  # put this at the top of your file if not already imported
from math import ceil
from openai import OpenAI
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# load_dotenv("./.env")
# os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# # Create the tracer
# tracer = LangChainTracer(project_name="slm_agent")

# Set up database
# database_file_path = "./inventory.db"
# db = SQLDatabase.from_uri(f"sqlite:///{database_file_path}")
# Set up database (Connecting to your local Docker MySQL)
db = SQLDatabase.from_uri("mysql+pymysql://root:root@127.0.0.1:3306/retail")
current_month_year = datetime.now().strftime("%B %Y")
# print(db.dialect)
# print(db.get_usable_table_names())
# print(db.run("PRAGMA table_info(inventory);"))
# client = OpenAI(base_url="http://34.143.134.17:8000/v1", api_key="not-needed")
client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="sk-dummy")

# Define SQL tools
def list_tables_tool() -> Dict[str, Any]:
    """
    Retrieve a schema and example rows of all usable tables in the database.
    """
    try:
        # Get all usable tables
        tables = db.get_usable_table_names()
        if not tables:
            return {"result": "No tables found in the database."}

        # Get schema info for all tables
        schema_info = db.get_table_info(tables)
        return {"result": schema_info}
    except Exception as e:
        return {"error": f"Error listing tables: {str(e)}"}


def query_checker_tool(query: str) -> Dict[str, Any]:
    """
    Validate the SQL query by running an EXPLAIN statement.
    """
    try:
        if not query or not isinstance(query, str):
            return {"error": "Invalid query: Query must be a non-empty string"}

        # Basic validation
        if ";" in query and not query.strip().endswith(";"):
            return {"error": "Invalid query: Multiple statements detected. Please submit a single SQL statement."}

        # Check for SQL injection attempts (simple check)
        if "--" in query or "/*" in query:
            return {"error": "Invalid query: Comment syntax detected. Please remove comments."}

        result = db.run(f"EXPLAIN {query}")
        return {"result": "Query is valid and can be executed safely."}
    except Exception as e:
        return {"error": f"Query validation failed: {str(e)}"}


# def db_query_tool(query: str) -> Dict[str, Any]:
#     """
#     Execute a SQL query against the database and get back the result.
#     If the query is not correct, an error message will be returned.
#     Returns results with column names in JSON format.
#     """
#     try:
#         if not query or not isinstance(query, str):
#             return {"error": "Invalid query: Query must be a non-empty string"}

#         # Basic validation
#         if ";" in query and not query.strip().endswith(";"):
#             return {"error": "Invalid query: Multiple statements detected. Please submit a single SQL statement."}
#         if "--" in query or "/*" in query:
#             return {"error": "Invalid query: Comment syntax detected. Please remove comments."}

#         # 🛡️ SAFETY: Force a LIMIT if missing
#         lowered_query = query.lower()
#         limit_value = 40  # default limit
#         if "limit" not in lowered_query and "select" in lowered_query:
#             query = query.rstrip(";") + f" LIMIT {limit_value};"

#         # Execute the query
#         raw_result = db.run_no_throw(query)
#         if raw_result is None:
#             return {"error": "Query execution failed. Please check your syntax and try again."}

#         # Handle raw_result as string (based on your debug output)
#         if isinstance(raw_result, str):
#             # Parse the string representation of tuples
#             import re
#             import ast

#             # Extract column names from the query
#             column_names = []
#             match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
#             if match:
#                 select_part = match.group(1)
#                 # Split by commas, but be careful with function calls that contain commas
#                 columns = []
#                 bracket_level = 0
#                 current_column = ""

#                 for char in select_part:
#                     if char == ',' and bracket_level == 0:
#                         columns.append(current_column.strip())
#                         current_column = ""
#                     else:
#                         if char == '(':
#                             bracket_level += 1
#                         elif char == ')':
#                             bracket_level -= 1
#                         current_column += char

#                 if current_column.strip():
#                     columns.append(current_column.strip())

#                 # Process each column expression to get the final name
#                 for col in columns:
#                     # Check for explicit AS
#                     as_match = re.search(r'\bAS\s+([`"\'a-zA-Z0-9_]+)', col, re.IGNORECASE)
#                     if as_match:
#                         name = as_match.group(1).strip('`\'"')
#                         column_names.append(name)
#                     else:
#                         # No explicit AS - take the last segment for qualified names
#                         parts = col.strip().split('.')
#                         name = parts[-1].strip()

#                         # If it's a function call without AS, use the function name
#                         if '(' in name:
#                             func_match = re.search(r'([a-zA-Z0-9_]+)\s*\(', col, re.IGNORECASE)
#                             if func_match:
#                                 name = func_match.group(1)
#                             else:
#                                 name = re.sub(r'[^a-zA-Z0-9_]', '_', col.strip())

#                         column_names.append(name)

#             # Try to parse the string as Python literal (list of tuples)
#             try:
#                 # Check if it starts with '[(' and ends with ')]'
#                 if raw_result.startswith('[') and raw_result.endswith(']'):
#                     # Use ast.literal_eval to safely parse the string into Python objects
#                     parsed_result = ast.literal_eval(raw_result)

#                     # If we don't have column names from query, use default ones
#                     if not column_names and parsed_result and isinstance(parsed_result[0], tuple):
#                         if len(parsed_result[0]) == 6:  # If matches your example's column count
#                             column_names = ["Product_ID", "Inventory_Level", "Units_Sold", "Units_Ordered", "Discount",
#                                             "Holiday_Promotion"]
#                         else:
#                             column_names = [f"column_{i}" for i in range(len(parsed_result[0]))]

#                     # Convert tuples to dictionaries with column names
#                     result = []
#                     for row in parsed_result:
#                         row_dict = {}
#                         for i, value in enumerate(row):
#                             if i < len(column_names):
#                                 row_dict[column_names[i]] = value
#                             else:
#                                 row_dict[f"column_{i}"] = value
#                         result.append(row_dict)

#                     # 📣 BONUS: Warn if we hit the limit - only for SELECT queries
#                     if "select" in lowered_query and len(result) >= limit_value:
#                         return {
#                             "result": result,
#                             "warning": f"⚠️ Your query returned {limit_value} rows (the maximum limit). "
#                                        "Consider refining your WHERE clause or being more specific to avoid data cutoff."
#                         }

#                     return {"result": result}
#                 else:
#                     # Not a list of tuples, just return the string
#                     return {"result": raw_result}

#             except (SyntaxError, ValueError) as e:
#                 # If parsing fails, just return the string as is
#                 print(f"Failed to parse result string: {e}")
#                 return {"result": raw_result}
#         else:
#             # Not a string, just return as is
#             return {"result": raw_result}

#     except Exception as e:
#         print(f"Error in db_query_tool: {str(e)}")
#         return {"error": f"Query execution error: {str(e)}"}
def db_query_tool(query: str) -> Dict[str, Any]:
    """
    Execute a SQL query against the database and reliably return clean JSON dicts.
    """
    try:
        if not query or not isinstance(query, str):
            return {"error": "Invalid query: Query must be a non-empty string"}

        # Basic validation
        if ";" in query and not query.strip().endswith(";"):
            return {"error": "Invalid query: Multiple statements detected."}
        if "--" in query or "/*" in query:
            return {"error": "Invalid query: Comment syntax detected."}

        # 🛡️ SAFETY: Force a LIMIT if missing
        lowered_query = query.lower()
        limit_value = 50 
        if "limit" not in lowered_query and "select" in lowered_query:
            query = query.rstrip(";") + f" LIMIT {limit_value};"

        from sqlalchemy import text
        import decimal
        from datetime import date, datetime

        # Native SQLAlchemy execution for bulletproof JSON conversion
        with db._engine.connect() as conn:
            result = conn.execute(text(query))
            keys = result.keys()
            rows = [dict(zip(keys, row)) for row in result]

            # Clean up Decimals and Dates so JSON doesn't crash
            for row in rows:
                for k, v in row.items():
                    if isinstance(v, decimal.Decimal):
                        row[k] = float(v)
                    elif isinstance(v, (date, datetime)):
                        row[k] = str(v)

            # Warn if we hit the limit
            if "select" in lowered_query and len(rows) >= limit_value:
                return {
                    "result": rows,
                    "warning": f"⚠️ Query returned max limit of {limit_value} rows."
                }

            return {"result": rows}

    except Exception as e:
        print(f"Error in db_query_tool: {str(e)}")
        return {"error": f"Query execution error: {str(e)}"}


def get_function_by_name(name):
    if name == "list_tables_tool":
        return list_tables_tool
    if name == "query_checker_tool":
        return query_checker_tool
    if name == "db_query_tool":
        return db_query_tool
    return None


# Define the tools in the format Qwen2.5 expects
SQL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables_tool",
            "description": "Retrieve the table schemas in the database and sample rows for each of the tables.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_checker_tool",
            "description": "Validate the SQL query for correctness before query execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to be validated."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "db_query_tool",
            "description": "Execute an SQL query on the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to be executed on the database."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

sql_tools_by_name = {
    "list_tables_tool": list_tables_tool,
    "query_checker_tool": query_checker_tool,
    "db_query_tool": db_query_tool
}


# functions
# def try_parse_tool_calls(message_dict: dict) -> AIMessage:
#     """
#     Extracts tool calls from an OpenAI-compatible response message dictionary (vLLM).
#     """
#     content = message_dict.get("content", "").replace("<think>", "").replace("</think>", "").strip()
#     tool_calls_data = message_dict.get("tool_calls", [])

#     tool_calls = []
#     for i, tool_call in enumerate(tool_calls_data):
#         call_id = tool_call.get("id", f"call_{i}")
#         fn_data = tool_call.get("function", {})
#         fn_name = fn_data.get("name", f"unknown_tool_{i}")
#         try:
#             fn_args = json.loads(fn_data.get("arguments", "{}"))
#         except json.JSONDecodeError:
#             fn_args = {"raw_arguments": fn_data.get("arguments", "")}

#         tool_calls.append({
#             "id": call_id,
#             "name": fn_name,
#             "args": fn_args
#         })

#     return AIMessage(content=content, tool_calls=tool_calls)

def try_parse_tool_calls(message_dict: dict) -> AIMessage:
    """
    Extracts tool calls from an OpenAI-compatible response message dictionary.
    Upgraded with a Regex Net to catch raw <tool_call> XML printed by local models!
    """
    # Safely get content (handling explicit None values from the API)
    raw_content = message_dict.get("content")
    content = raw_content if raw_content is not None else ""
    content = content.replace("<think>", "").replace("</think>", "").strip()

    # Safely get tool_calls (🐛 FIX: Force explicit None values into an empty list)
    tool_calls_data = message_dict.get("tool_calls")
    if tool_calls_data is None:
        tool_calls_data = []

    # 🕸️ THE REGEX NET: Catch raw XML tool calls and convert them to standard JSON
    if not tool_calls_data and "<tool_call>" in content:
        import re
        import uuid
        matches = re.finditer(r"<tool_call>\s*({.*?})\s*</tool_call>", content, re.DOTALL)
        for match in matches:
            try:
                tool_data = json.loads(match.group(1))
                tool_calls_data.append({
                    "id": f"call_{uuid.uuid4().hex[:10]}",
                    "function": {
                        "name": tool_data.get("name", ""),
                        "arguments": json.dumps(tool_data.get("arguments", {}))
                    }
                })
                print(f"🔧 Caught and parsed raw XML tool call: {tool_data.get('name')}")
            except Exception as e:
                print(f"⚠️ Failed to parse raw tool call: {e}")
        
        # Hide the ugly XML tags from the final dashboard chat window
        content = re.sub(r"<tool_call>\s*({.*?})\s*</tool_call>", "", content, flags=re.DOTALL).strip()

    tool_calls = []
    for i, tool_call in enumerate(tool_calls_data):
        call_id = tool_call.get("id", f"call_{i}")
        fn_data = tool_call.get("function", {})
        fn_name = fn_data.get("name", f"unknown_tool_{i}")
        try:
            fn_args = json.loads(fn_data.get("arguments", "{}"))
        except json.JSONDecodeError:
            fn_args = {"raw_arguments": fn_data.get("arguments", "")}

        tool_calls.append({
            "id": call_id,
            "name": fn_name,
            "args": fn_args
        })

    return AIMessage(content=content, tool_calls=tool_calls)

def safe_json_parse(raw_str: str) -> dict:
    """
    Extract and parse the first valid JSON object from a string.
    Assumes the string starts with '{"' and ends with '}' before any non-JSON content.
    """
    brace_count = 0
    start_index = None

    for i, char in enumerate(raw_str):
        if char == '{':
            if start_index is None:
                start_index = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_index is not None:
                json_str = raw_str[start_index:i + 1]
                return json.loads(json_str)

    raise ValueError("Valid JSON object not found in string.")


class ExtendedMessagesState(MessagesState):
    sql_data: dict = {}


def build_agent(TOOLS, tools_by_name, agent):
    # LLM Call for LangGraph integration
    # LLM Call for LangGraph integration
    def llm_call(state: ExtendedMessagesState):
        """LLM decides whether to call a tool or not"""
        messages = state["messages"]
        last_message = messages[-1]

        tool_agent_map = {
            "get_inventory_data_tool": "inventory_management_agent",
            "get_sales_data_tool": "sales_analyst_agent",
        }

        # Flagging whether inventory or sales agent is requesting data from the sql agent
        if isinstance(last_message, ToolMessage) and last_message.name in tool_agent_map:
            agent_name = agent
            try:
                # 🛡️ SAFETY NET: Strip /no_think before parsing so json.loads() doesn't crash
                clean_content = last_message.content.split("/no_think")[0].strip()
                tool_content = json.loads(clean_content)
                instruction_text = tool_content.get("requested", clean_content)
            except Exception as e:
                print(f"JSON Parse error caught: {e}")
                # Fallback to just stripping the tag
                instruction_text = last_message.content.split("/no_think")[0].strip()

            # 🛡️ SAFETY NET: Return ONLY the new message. LangGraph automatically appends it.
            return {
                "messages": [
                    AIMessage(
                        content=instruction_text,
                        additional_kwargs={"agent_name": agent_name, "request_data": True}
                    )
                ]
            }

        # If last message is from db_query_tool, return the sql query result without sql agent checking
        if agent == 'sql_agent' and isinstance(last_message, ToolMessage) and last_message.name == 'db_query_tool':
            try:
                # 🛡️ SAFETY NET: Strip /no_think here as well just to be safe
                raw_content = last_message.content.split("/no_think")[0].strip()

                if isinstance(raw_content, str):
                    tool_result = safe_json_parse(raw_content)
                elif isinstance(raw_content, dict):
                    tool_result = raw_content
                else:
                    raise ValueError("Unexpected ToolMessage content type")

                if "error" not in tool_result:
                    # Safely convert result to a string for AIMessage
                    result_str = json.dumps(tool_result["result"], ensure_ascii=False)

                    # When the sql_query_result is empty
                    if result_str == '""':
                        result_str = json.dumps({"status": "no_data"}, ensure_ascii=False)

                    # 🛡️ SAFETY NET: Return ONLY the new message.
                    return {
                        "messages": [
                            AIMessage(
                                content=result_str,
                                additional_kwargs={"agent_name": agent}
                            )
                        ]
                    }
            except Exception as e:
                print(f"Failed to parse db_query_tool result: {e}")

        # Convert LangGraph message format to the format expected by Qwen
        converted_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                converted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    converted_messages.append({
                        "role": "assistant",
                        "content": msg.content,
                        "tool_calls": [{
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"])  # Must be a JSON string
                            }
                        } for i, tc in enumerate(msg.tool_calls)]
                    })
                else:
                    converted_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                converted_messages.append({
                    "role": "tool",
                    "tool_call_id": getattr(msg, "tool_call_id", f"call_{uuid.uuid4().hex[:10]}"),
                    "name": msg.name,
                    "content": msg.content,
                })
        # 🛡️ SAFETY NET: Sliding Window Memory (Prevent Context Explosions)
        # Always keep the System Prompt (index 0), but restrict history to the last 10 messages
        if len(converted_messages) > 11:
            converted_messages = [converted_messages[0]] + converted_messages[-10:]

        max_tokens = 1500
        
        # using vLLM
        response = client.chat.completions.create(
            model="Qwen/Qwen3-4B",
            messages=converted_messages,
            tools=TOOLS,
            tool_choice="auto",  # Let model decide if tool should be called
            max_tokens=max_tokens,
            temperature=0.7,
        )
        
        # Use the new parser
        ai_message = try_parse_tool_calls(response.choices[0].message.model_dump())

        return {"messages": [ai_message]}
        """LLM decides whether to call a tool or not"""
        messages = state["messages"]

        last_message = messages[-1]
        # In the llm_call function

        tool_agent_map = {
            "get_inventory_data_tool": "inventory_management_agent",
            "get_sales_data_tool": "sales_analyst_agent",
        }

        # flagging whether is inventory or sales agent requesting data from the sql agent
        if isinstance(last_message, ToolMessage) and last_message.name in tool_agent_map:
            agent_name = agent
            try:
                tool_content = json.loads(last_message.content)
                instruction_text = tool_content.get("requested", last_message.content)
            except json.JSONDecodeError:
                instruction_text = last_message.content

            return {
                "messages": messages + [
                    AIMessage(
                        content=instruction_text,
                        additional_kwargs={"agent_name": agent_name, "request_data": True, }
                    )
                ]
            }
        # if last message is from db_query_tool, we just return the sql query result, no need to let the sql agent check
        if agent == 'sql_agent' and isinstance(last_message, ToolMessage) and last_message.name == 'db_query_tool':
            try:
                raw_content = last_message.content

                if isinstance(raw_content, str):
                    tool_result = safe_json_parse(raw_content)
                elif isinstance(raw_content, dict):
                    tool_result = raw_content
                else:
                    raise ValueError("Unexpected ToolMessage content type")

                if "error" not in tool_result:
                    # Safely convert result to a string for AIMessage
                    result_str = json.dumps(tool_result["result"], ensure_ascii=False)

                    # when the sql_query_result is empty
                    if result_str == '""':
                        result_str = json.dumps({"status": "no_data"}, ensure_ascii=False)

                    return {
                        "messages": messages + [
                            AIMessage(
                                content=result_str,
                                additional_kwargs={"agent_name": agent}
                            )
                        ]
                    }
            except Exception as e:
                print(f"Failed to parse db_query_tool result: {e}")

        # Convert LangGraph message format to the format expected by Qwen
        converted_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                converted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    converted_messages.append({
                        "role": "assistant",
                        "content": msg.content,
                        "tool_calls": [{
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"])  # Must be a JSON string
                            }
                        } for i, tc in enumerate(msg.tool_calls)]
                    })
                else:
                    converted_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                converted_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,  # 🐛 ADDED THIS LINE
                    "name": msg.name,
                    "content": msg.content,
                })

        max_tokens = 1500
        # if agent == "sql_agent":  #increase the output tokens for sql agent
        #     max_tokens = 10000
        # using vLLM
        response = client.chat.completions.create(
            model="Qwen/Qwen3-4B",
            messages=converted_messages,
            tools=TOOLS,
            tool_choice="auto",  # Let model decide if tool should be called
            max_tokens=max_tokens,
            temperature=0.7,
        )
        # Use the new parser
        ai_message = try_parse_tool_calls(response.choices[0].message.model_dump())

        return {"messages": [ai_message]}

    def process_tool_args(args, tool_results):
        """Process tool arguments, resolving any variable references."""
        if not isinstance(args, dict):
            return args

        processed_args = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # This is a variable reference
                var_name = value[2:-2]  # Remove {{ and }}
                if var_name in tool_results:
                    processed_args[key] = tool_results[var_name]
                else:
                    # Try to handle tool_output_function_name_result pattern
                    parts = var_name.split('_')
                    if len(parts) >= 4 and parts[0] == "tool" and parts[1] == "output" and parts[-1] == "result":
                        tool_name = '_'.join(parts[2:-1])
                        if f"{tool_name}_result" in tool_results:
                            processed_args[key] = tool_results[f"{tool_name}_result"]
                        else:
                            # If we can't resolve, keep as is (will likely cause an error)
                            processed_args[key] = value
                    else:
                        processed_args[key] = value
            else:
                processed_args[key] = value
        return processed_args

    def tool_node(state: ExtendedMessagesState):
        """Performs the tool calls sequentially, resolving dependencies between them."""
        result = []
        tool_results = {}  # Store results for variable resolution

        for tool_call in state["messages"][-1].tool_calls:
            # Process args to resolve any variable references
            processed_args = process_tool_args(tool_call["args"], tool_results)

            # Execute the tool
            tool = tools_by_name[tool_call["name"]]
            if tool_call["name"] == "list_tables_tool":
                observation = tool()
            elif tool_call["name"] == "summarize_sales_tool":
                observation = tool(state)
            elif tool_call["name"] == "analyze_inventory_levels_tool":
                observation = tool(state)
            else:
                # For other tools that require the query parameter
                observation = tool(**processed_args)

            # Store the result for potential future use
            for key, value in observation.items():
                tool_results[f"{tool_call['name']}_{key}"] = value

            # Create tool message
            result.append(
                ToolMessage(
                    content=json.dumps(observation) + "/no_think",
                    tool_call_id=tool_call["id"],
                    name=tool_call["name"]
                )
            )

        return {"messages": result}

    # Conditional edge function
    def should_continue(state: ExtendedMessagesState) -> str:
        """Decide if we should continue the loop or stop"""
        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM makes a tool call, then perform an action
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "Tools"

        # Otherwise, we stop (reply to the user)
        return END

    # Build workflow
    agent_builder = StateGraph(ExtendedMessagesState)

    # Add nodes
    agent_builder.add_node("Agent", llm_call)
    agent_builder.add_node("Tools", tool_node)

    # Add edges to connect nodes
    agent_builder.add_edge(START, "Agent")
    agent_builder.add_conditional_edges(
        "Agent",
        should_continue,
        {
            "Tools": "Tools",
            END: END,
        },
    )
    agent_builder.add_edge("Tools", "Agent")

    # Compile the agent
    return agent_builder.compile()


# Compile the agent
sql_agent = build_agent(SQL_TOOLS, sql_tools_by_name, "sql_agent")

# Inventory Tools
INVENTORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory_data_tool",
            "description": "Fetch inventory data for a specific store and time. Use this when required fields are missing, incorrect, or not yet provided. You MUST explain exactly what is wrong or missing in the previous data (e.g., missing fields, wrong date).",
            "parameters": {
                "type": "object",
                "properties": {
                    "instructions": {
                        "type": "string",
                        "description": "Clearly describe what inventory data and fields are needed. If this is a retry, include a brief explanation of what was incorrect or incomplete in the previous data (e.g., 'Units_Sold field was missing', or 'Date returned was not the end of January 2022')."
                    }
                },
                "required": ["instructions"]
            }
        }
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "analyze_inventory_levels_tool",
    #         "description": "Use LLM to assess multiple products for restocking needs.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "product_data_list": {
    #                     "type": "array",
    #                     "items": {
    #                         "type": "object",
    #                         "properties": {
    #                             "product_id": {"type": "string"},
    #                             "inventory_level": {"type": "integer"},
    #                             "average_units_sold": {"type": "integer"},
    #                         },
    #                         "required": [
    #                             "product_id", "inventory_level", "average_units_sold",
    #                         ]
    #                     },
    #                     "description": "List of structured product-level inventory data."
    #                 }
    #             },
    #             "required": ["product_data_list"]
    #         }
    #     }
    # },
    {
        "type": "function",
        "function": {
            "name": "analyze_inventory_levels_tool",
            "description": "Use LLM to assess multiple products for restocking needs based on inventory data available in state. No parameters required — the function will automatically use the latest inventory data.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_restock_plan_tool",
            "description": "Use LLM to produce a final restock plan from prior analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "inventory_analysis": {
                        "type": "string",
                        "description": "LLM-based reasoning that determines if restocking is needed"
                    }
                },
                "required": ["inventory_analysis"]
            }
        }
    }
]


def get_inventory_data_tool(instructions: str) -> Any:
    """
    Request inventory data from the SQL agent using natural language instructions.

    Args:
        instructions (str): Instructions describing the required inventory data,
                                 e.g., "Get inventory_level and units_sold for store S001
                                 from Jan 2023 to Mar 2023."

    Returns:
        Command: Used to return control to the Supervisor agent.

    """
    # You can return something more realistic once you connect to SQL agent
    return {
        "status": "waiting_for_sql_agent_response",
        "requested": instructions
    }


def analyze_inventory_levels_tool(state: dict) -> dict:
    """
    Analyzes inventory levels using True Reorder Point (ROP) mathematics.
    ROP = Safety Stock + (Average Daily Demand * Lead Time Days)
    """
    sql_data_obj = state.get('sql_data', {})
    if not sql_data_obj or not sql_data_obj.get('data'):
        return {
            "result": "No inventory data available. Please call the `get_inventory_data_tool`.",
            "error": "missing_data"
        }
        
    inventory_data = sql_data_obj.get('data', [])
    analyzed_products = []
    
    for product in inventory_data:
        product_id = product.get("product_id") or product.get("Product_ID")
        inventory_level = product.get("inventory_level") or product.get("Inventory_Level") or 0
        demand = product.get("monthly_demand") or product.get("Monthly_Demand") or 0
        safety_stock = product.get("safety_stock") or product.get("Safety_Stock") or 0
        lead_time = product.get("lead_time_days") or product.get("Lead_Time_Days") or 0
        
        try:
            demand_ceil = ceil(float(demand))
            inv_level = float(inventory_level)
            s_stock = float(safety_stock)
            l_time = float(lead_time)
        except (ValueError, TypeError):
            continue

        # 🧮 TRUE ROP MATH
        daily_demand = demand_ceil / 30.0
        lead_time_demand = daily_demand * l_time
        rop = ceil(s_stock + lead_time_demand)
        
        # Calculate how many days until we hit absolute zero
        days_remaining = (inv_level / daily_demand) if daily_demand > 0 else 999
        
        # Flag if we are below ROP (Need to order NOW to prevent dipping into safety stock)
        is_critical = inv_level <= rop
        
        # If critical, order enough to cover lead time + safety stock + 1 full month of buffer
        target_stock = rop + demand_ceil
        restock_qty = max(0, ceil(target_stock - inv_level)) if is_critical else 0
        
        analyzed_products.append({
            "product_id": product_id,
            "inv_level": inv_level,
            "demand": demand_ceil,
            "rop": rop,
            "safety_stock": s_stock,
            "days_remaining": days_remaining,
            "is_critical": is_critical,
            "restock_qty": restock_qty
        })

    # Sort so the most critical items (fewest days remaining) are at the top
    analyzed_products.sort(key=lambda x: x["days_remaining"])
    
    analysis_results = []
    for p in analyzed_products:
        status = "CRITICAL SHORTAGE ALARM" if p['is_critical'] else "HEALTHY"
        result = f"""
        Product ID: {p['product_id']}
        Current Inventory: {p['inv_level']}
        Monthly Demand: {p['demand']}
        Safety Stock: {p['safety_stock']}
        Reorder Point (ROP): {p['rop']}
        Days of Stock Remaining: {p['days_remaining']:.1f} days
        Status: {status}
        Recommended Restock Qty: {p['restock_qty']}
        """
        analysis_results.append(result.strip())

    return {"result": analysis_results}


def generate_restock_plan_tool(inventory_analysis: str) -> dict:
    """
    Uses an LLM to generate a structured restock plan from a reasoning summary.

    Args:
        inventory_analysis (str): LLM analysis output showing which products need restocking and why.

    Returns:
        str: A list of products with recommended restock quantities and justification.
    """
    prompt = f"""
    You are the Chief Supply Chain Analyst presenting to the Executive Board.

    Based on the True Reorder Point (ROP) analysis provided below, generate a professional Restock Plan.

    **CRITICAL RULES**:
    1. ONLY recommend restocking for items where "Status: CRITICAL SHORTAGE ALARM" or where the Recommended Restock Qty is greater than 0.
    2. If all items are healthy, clearly state that no procurement is necessary and list the days of stock remaining for the top items.
    3. You MUST ALWAYS output the Markdown table.

    Analysis Data (Sorted by critical need):
    {inventory_analysis}

    Respond in **Markdown** using EXACTLY this format:

    ### Executive Supply Chain Overview
    [Write 2-3 sentences summarizing the warehouse health. Highlight any products that have breached their Reorder Point and explain how the lead time impacts production.]

    ### Procurement Action Plan

    | Product ID | Current Stock | Reorder Point (ROP) | Recommended Order Qty | Procurement Justification |
    |------------|---------------|---------------------|-----------------------|---------------------------|
    | {{product_id}} | {{inv_level}} | {{rop}} | {{restock_qty}} | Stock has breached ROP. Order {{restock_qty}} units immediately. At current demand, we only have {{days_remaining}} days of stock left, factoring in lead time. |
    """

    msgs = [
        {"role": "user", "content": "/no_think" + prompt}
    ]

    response = client.chat.completions.create(
        model="Qwen/Qwen3-4B",
        messages=msgs,
        max_tokens=500,
        temperature=0.7,
    )

    return {"result": response.choices[0].message.content.replace("<think>", "").replace("</think>", "").strip()}


inventory_tools_by_name = {
    "get_inventory_data_tool": get_inventory_data_tool,
    "analyze_inventory_levels_tool": analyze_inventory_levels_tool,
    "generate_restock_plan_tool": generate_restock_plan_tool,
}

# Compile the agent
inventory_agent = build_agent(INVENTORY_TOOLS, inventory_tools_by_name, "inventory_management_agent")

# SALES TOOLS
SALES_ANALYST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_data_tool",
            "description": "Fetch detailed sales data for specific stores, products, or time periods. Use this when you do not yet have the required data to perform a sales analysis or summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instructions": {
                        "type": "string",
                        "description": "Clearly specify what sales data is needed. Example: 'Get total revenue and units sold for store S001 for Oct 2021.'",
                    }
                },
                "required": ["instructions"]
            }
        }
    },
    # testing new summarize_sales_tool where currently we do not need to pass the sql_data that causes long tool call construction time
    {
        "type": "function",
        "function": {
            "name": "summarize_sales_tool",
            "description": "Use LLM to summarize recent sales performance and trends based on the SQL data stored in the current state. No parameters needed - will automatically use the most recent sales data from state. ONLY call this when these fields are in the recent data:`Product_ID` or `Category`, `Units_Sold`, `Revenue`, and `Date` ",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "summarize_sales_tool",
    #         "description": "Use LLM to summarize recent sales performance and trends based on the provided structured data from the previous get_sales_data_tool",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "sales_data": {
    #                     "type": "array",
    #                     "items": {
    #                         "type": "object",
    #                         "properties": {
    #                             "product_id": {"type": "string"},
    #                             "category": {"type": "string"},
    #                             "store_id": {"type": "string"},
    #                             "units_sold": {"type": "integer"},
    #                             "revenue": {"type": "number"},
    #                             "date": {"type": "string"},
    #                         },
    #                         "required": ["units_sold", "revenue", "date"]
    #                     },
    #                     "description": "List of sales data entries with basic metrics.Only those properties that are not required, ONLY pass them when there are actual values associated. DO NOT make up values. Make sure the arguments are in lower case letters"
    #                 }
    #             },
    #             "required": ["sales_data"]
    #         }
    #     }
    # }
]


def get_sales_data_tool(instructions: str) -> dict:
    return {
        "status": "waiting_for_sql_agent_response",
        "requested": instructions
    }


# new summarize_sales_tool where we dont accept sql_data through the parameters
def summarize_sales_tool(state: dict) -> dict:
    """
    Summarize sales data from the state without requiring parameters.
    Args:
        state: The current state containing sql_data
    Returns:
        dict: Summary result from LLM
    """
    # Get SQL data from state
    sql_data_obj = state.get('sql_data', {})
    # Check if we have data and if it's intended for summarization
    if not sql_data_obj or not sql_data_obj.get('data'):
        return {
            "result": "No sales data available in state for summarization.  Please generate tool call for `get_sales_data_tool`",
            "error": "missing_data"
        }

    sales_data = sql_data_obj.get('data', [])

    # Check if data is intended for this operation
    # intended_for = sql_data_obj.get('intended_for')
    # if intended_for and intended_for not in ['sales_analyst_agent']:
    #     return {
    #         "result": f"Sales data is intended for {intended_for}, not for summarization.",
    #         "error": "data_not_intended"
    #     }

    # check whether the necessary fields are available
    if all(
            # any(k in record for k in ["Month", "date", "Date"]) and
            any(k in record for k in ["Units_Sold", "units_sold", "Total_Units_Sold"]) or
            any(k in record for k in ["Revenue", "revenue", "Total_Revenue"]) and
            (
                    any(k in record for k in ["Product_ID", "product_id"]) or
                    any(k in record for k in ["Category", "category"]) or
                    any(k in record for k in ["Store_ID", "store_id"])
            )
            for record in sales_data
    ):
        # Pre-process and sort the data to help the LLM
        # Group by month for clearer analysis
        monthly_data = {}
        for record in sales_data:
            # Handle different date field names (Month, date, etc.)
            month = record.get('Month') or record.get('date') or record.get('Date', 'N/A')
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(record)

        # Sort each month's data by units sold (descending)
        for month in monthly_data:
            monthly_data[month].sort(
                key=lambda x: x.get('Units_Sold') or x.get('units_sold', 0),
                reverse=True
            )

        # Create structured summary for prompt
        monthly_summaries = []
        for month, records in monthly_data.items():
            # Handle different field name variations
            total_units = sum(
                r.get('Units_Sold') or r.get('units_sold', 0)
                for r in records
            )
            # 🐛 FIX: Safely cast to float in case SQL returns strings/Decimals
            total_revenue = sum(
                float(r.get('Revenue') or r.get('revenue', 0) or r.get('Total_Revenue', 0) or 0)
                for r in records
            )

            monthly_summaries.append(f"\n=== {month} ===")
            monthly_summaries.append(f"Total Units Sold: {total_units}")
            monthly_summaries.append(f"Total Revenue: ${total_revenue:,.2f}")

            monthly_summaries.append("\nTOP 5 BY UNITS SOLD:")
            for i, record in enumerate(records[:5]):
                store_id = record.get('Store_ID') or record.get('store_id', '')
                product_id = record.get('Product_ID') or record.get('product_id', '')
                category = record.get('Category') or record.get('category', '')
                units = record.get('Units_Sold') or record.get('units_sold', 0) or record.get('Total_Units_Sold', 0)
                revenue = record.get('Revenue') or record.get('revenue', 0) or record.get('Total_Revenue', 0) or 0

                monthly_summaries.append(
                    f"{i + 1}. {store_id} {product_id} {category}: {units} units, ${revenue:.2f} revenue"
                )

            # Add all records for context
            monthly_summaries.append("\nALL RECORDS:")
            for record in records:
                product_id = record.get('Product_ID') or record.get('product_id', '')
                category = record.get('Category') or record.get('category', '')
                units = record.get('Units_Sold') or record.get('units_sold', 0) or record.get('Total_Units_Sold', 0)
                revenue = record.get('Revenue') or record.get('revenue', 0) or record.get('Total_Revenue', 0) or 0

                monthly_summaries.append(
                    f"  {product_id} {category}: {units} units, ${revenue:.2f}"
                )
        print("$$$$$monthly summaries: " + str(monthly_summaries))
        prompt = f"""
    You are a retail sales analyst.
    
    Write a **brief and concise** summary of the following pre-sorted sales data.
    Make sure the analysis focuses on the time period specified.
    Keep it **under 8 bullet points**. Focus on **key highlights** only.
    
    The data is already sorted by units sold (highest first) for each month.
    
    Focus your analysis on:
    - Total units sold
    - Total revenue
    - Top-selling products (by units sold)
    - Revenue per unit anomalies
    - Any unusual patterns
    - Any other interesting analysis
    
    
    Sales Data (Pre-sorted by Units Sold):
    {''.join(monthly_summaries)}
    """

        msgs = [
            {"role": "user", "content": prompt + "/no_think"}
        ]

        try:
            response = client.chat.completions.create(
                model="Qwen/Qwen3-4B",
                messages=msgs,
                max_tokens=500,
                temperature=0.7,
            )

            return {
                "result": response.choices[0].message.content.replace("<think>", "").replace("</think>", "").strip(),
                "record_count": len(sales_data),
                "months_analyzed": list(monthly_data.keys())
            }

        except Exception as e:
            return {
                "result": f"Error generating summary: {str(e)}",
                "error": "llm_error"
            }
    else:
        return {
            "result": "No sales data available in state for analyzing inventory levels.  Please generate tool call for `get_sales_data_tool`. Make sure these fields: `Product_ID` or `Category`, `Units_Sold`, `Revenue`, and `Date` are present",
            "error": "missing_data"
        }


sales_analyst_tools_by_name = {
    "get_sales_data_tool": get_sales_data_tool,
    "summarize_sales_tool": summarize_sales_tool,
}

# Compile the agent
sales_agent = build_agent(SALES_ANALYST_TOOLS, sales_analyst_tools_by_name, "sales_analyst_agent")

# Trying to build supervisor multi agent architecture
# define tools to allow the supervisor to transfer to sub agents for task delegation
SUPERVISOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "transfer_to_inventory_agent",
            "description": "Transfer task to the inventory management agent for determining restock needs, predicting future stock requirements, and generating restock plans.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Instruction of task needed to be done from the supervisor agent to the inventory management agent"
                    }
                },
                "required": ["instructions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_sales_agent",
            "description": "Transfer task to the sales analyst agent for analyzing sales data, summarizing performance, or identifying sales trends and anomalies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Instruction of task needed to be done from the supervisor agent to the sales analyst agent"
                    }
                },
                "required": ["instructions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_sql_agent",
            "description": "Transfer task to the SQL agent for retrieving data from the inventory database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_requirements": {
                        "type": "string",
                        "description": "Description of the data needed from the database"
                    }
                },
                "required": ["data_requirements"]
            }
        }
    },
]


# Add this to your SupervisorState type definition
class SupervisorState(TypedDict):
    messages: list
    last_sql_requester: Optional[str]
    pending_agents: list
    completed_agents: Set[str]
    sql_data: dict


def supervisor_node(state: SupervisorState) -> Command[
    Literal["SQL_AGENT", "INVENTORY_MANAGEMENT_AGENT", "SALES_ANALYST_AGENT", END]]:
    messages = state["messages"]
    completed_agents = state.get("completed_agents", set())
    # Convert LangGraph message format to OpenAI/vLLM format
    converted_messages = [
        {
            "role": "system",
            "content": f"""
You are the Supervisor Agent in a multi-agent system for inventory management and sales analysis.
Your roles are to coordinate communication between sub-agents to ensure all tasks are fully completed and also communicate with the users.
You must NEVER analyze, interpret, summarize, or produce findings yourself.

Available Sub-Agents:
- SQL Agent → Fetches raw data (inventory, sales, product) from databases. Never interprets.
- Inventory Management Agent → Creates restock plans based on inventory data.
- Sales Analyst Agent → Generates trends, and insights based on sales data.

CRITICAL RULES:
- Do not generate any insights or conclusions.
- Only pass messages between agents.
- Ensure all parts of the user's request are fulfilled before responding.
- If the user asks about anything unrelated to retail, inventory or sales (e.g., weather, sports, general questions), respond: "I only supports inventory and sales related inquiries. Please rephrase your question or contact the relevant team for other topics."

RESTOCK-ONLY QUERIES - STRICT RULE:
If the user query is EXCLUSIVELY about restocking, restock plans, or inventory replenishment (e.g., "What is the restock plan for X?", "What should be restocked at store Y?", "Do we need to restock product Z?"):
- ONLY involve the Inventory Management Agent
- DO NOT call transfer_to_sales_agent at ANY point during the process
- DO NOT perform any validation or follow-up that involves the Sales Analyst Agent
- Once the Inventory Management Agent provides the restock plan, and it pass the correctness_check, that is the FINAL answer.

Task Routing Rules:
1. For PURE restocking questions:
   → ONLY call `transfer_to_inventory_agent(data)`
   → Once inventory_management_agent responds with restock plan → DONE
   → DO NOT call any other agents

2. For sales analysis questions (e.g., "How did product Y perform?", "What are the sales trends?"):
   → ONLY call `transfer_to_sales_agent(data)`
   → Once sales_analyst_agent responds with analysis → DONE

3. For COMBINED questions (asking for both restock AND sales analysis):
   → Call both agents as needed
   → Wait for both responses before final answer
   
4. For questions regarding sales data or inventory data retrieval only (eg."Help me retrieve the products with less than 100 items in stock for Store S001 during the end of {current_month_year}.")
   -> Call `transfer_to_sql_agent(data_requirements)`
   -> Return the data back to user when the SQL Agent returns valid data.
   
4. When a sub-agent requests additional data:
   → Extract their data requirements
   → Use `transfer_to_sql_agent(data_requirements)` to fetch it
   → Route raw SQL results back to the requesting sub-agent

5. Data flow rules:
   → NEVER interpret or alter SQL results yourself
   → Always pass raw data between agents
   → Only route to agents that are actually needed for the specific query type

COMPLETION CRITERIA - WHEN TO STOP CALLING AGENTS:
A response is COMPLETE and requires NO further agent calls when:
- Inventory Management Agent provides a restock plan with specific recommendations (restock/no restock + quantities)
- Sales Analyst Agent provides analysis with insights, trends, or ROI data
- Any agent provides a comprehensive answer that fully addresses the user's question

DO NOT re-call agents if they have already provided:
- Complete restock recommendations with justification
- Comprehensive sales analysis with conclusions
- Any response that directly answers the user's question

VALIDATION PROCESS:
- For restock-only queries: NO validation needed after inventory agent responds
- For sales-only queries: NO validation needed after sales agent responds
- For mixed queries: Ensure both aspects are covered before responding
- NEVER re-call an agent that has already provided a complete response

FINAL RESPONSE RULES:
- If an agent provides a complete answer → Return it to the user immediately
- DO NOT perform "correctness checks" or "follow-ups" after complete responses
- DO NOT re-route completed tasks to the same agent
- Only call additional agents if the original response is genuinely incomplete or requests more data

Available Tool Calls:
- transfer_to_inventory_agent(data)
- transfer_to_sales_agent(data)
- transfer_to_sql_agent(data_requirements)

Remember: 
-Once an agent provides a complete response that answers the user's most recent query, you MUST STOP calling agents and return the final answer.
-If you need to make tool call, please call the tool using <tool_call>...</tool_call>
-When the user refers to 'current month', interpret it as {current_month_year} and include that exact month explicitly in any instructions to sub-agents.

/no_think
"""
        }
    ]
    for msg in messages:
        role_name = msg.additional_kwargs.get("agent_name", "assistant")
        if isinstance(msg, HumanMessage):
            converted_messages.append({"role": "user", "content": msg.content + "/no_think"})
        elif isinstance(msg, AIMessage):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                converted_messages.append({
                    "role": "assistant",
                    "name": role_name,
                    "content": f"from {role_name}:  " + msg.content,
                    "tool_calls": [{
                        "id": tc.get("id", f"call_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"])  # Must be a JSON string
                        }
                    } for i, tc in enumerate(msg.tool_calls)]
                })
            else:
                converted_messages.append({
                    "role": "assistant",
                    "name": role_name,
                    "content": f"from {role_name}:  " + msg.content
                })
                # converted_messages.append(AIMessage(content=f"from {role_name}:/n" + msg.content))
        elif isinstance(msg, ToolMessage):
            converted_messages.append({
                "role": "tool",
                "tool_call_id": getattr(msg, "tool_call_id", f"call_{uuid.uuid4().hex[:10]}"), # 🐛 ADDED THIS LINE (with safety fallback)
                "name": msg.name,
                "content": f"from {role_name}:  " + msg.content,
            })
    last_message = messages[-1]

    # agents mapping based on their names
    agent_names_map = {
        "sql_agent": "SQL_AGENT",
        "inventory_management_agent": "INVENTORY_MANAGEMENT_AGENT",
        "sales_analyst_agent": "SALES_ANALYST_AGENT",
        "supervisor_agent": "SUPERVISOR_AGENT",
    }
    return_response = False
    # Extract the original user query
    user_query = None
    for msg in reversed(messages):  # get the most recent user's query
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break
    # Check if last message is from sql agent
    if isinstance(last_message, AIMessage) and last_message.additional_kwargs.get("agent_name") == "sql_agent":
        # validate the response from the sql agent
        # if the sql agent could not retrieve the data inform the user that the data does not exist
        # Check if the message content includes a no_data status
        try:
            parsed_content = json.loads(last_message.content)
            if isinstance(parsed_content, dict) and parsed_content.get("status") == "no_data":
                # End the graph execution with a final message to the user
                final_message = AIMessage(
                    content=parsed_content.get("message", "Requested data is not available."),
                    additional_kwargs={"agent_name": "supervisor_agent"}
                )
                return Command(
                    goto=END,
                    update={"messages": messages + [final_message]}
                )
        except json.JSONDecodeError:
            pass  # If not JSON, continue as usual

        # reflect on the response returned by the agent
        is_correct, reflection_output = check_agent_response(messages, "sql_agent")
        if reflection_output:
            messages.append(AIMessage(content=reflection_output, additional_kwargs={"agent_name": "supervisor_agent"}))

        if not is_correct:
            follow_up = parse_required_follow_up(reflection_output)
            next_agent = agent_names_map[follow_up] if follow_up != 'none' else agent_names_map['supervisor_agent']
            return Command(goto=next_agent, update={"messages": messages})

        if state.get("last_sql_requester") == "inventory_management_agent":
            # we redirect to the inventory management_agent with the data fetched
            return Command(goto="INVENTORY_MANAGEMENT_AGENT", update={"messages": messages, "last_sql_requester": None})
        elif state.get("last_sql_requester") == "sales_analyst_agent":
            # we redirect to the inventory management_agent with the data fetched
            return Command(goto="SALES_ANALYST_AGENT", update={"messages": messages, "last_sql_requester": None})

    elif isinstance(last_message, AIMessage) and last_message.additional_kwargs.get(
            "agent_name") == "inventory_management_agent":
        if last_message.additional_kwargs.get("request_data"):
            # Immediately create a tool call to SQL agent
            data_requirements = last_message.content  # assume LLM response includes data need
            tool_call = {
                "name": "transfer_to_sql_agent",
                "args": {"data_requirements": data_requirements},
                "type": "tool_call",
                "id": str(uuid.uuid4())
            }
            new_message = AIMessage(content="", tool_calls=[tool_call],
                                    additional_kwargs={"agent_name": "supervisor_agent"})
            messages.append(new_message)
            return Command(goto="SQL_AGENT",
                           update={"messages": messages,
                                   "last_sql_requester": "inventory_management_agent"})
        else:
            # Mark inventory agent as completed
            completed_agents.add("inventory_management_agent")
            # reflect on the response returned by the agent
            is_correct, reflection_output = check_agent_response(messages, "inventory_management_agent")
            if reflection_output:
                messages.append(
                    AIMessage(content=reflection_output, additional_kwargs={"agent_name": "supervisor_agent"}))

            if not is_correct:
                # Remove from completed if incorrect
                completed_agents.discard("inventory_management_agent")
                follow_up = parse_required_follow_up(reflection_output)
                next_agent = agent_names_map[follow_up] if follow_up != 'none' else agent_names_map['supervisor_agent']
                return Command(goto=next_agent, update={"messages": messages})
            else:
                # We consider the inventory management agent finished its work when it pass the check from supervisor agent
                if any(keyword in user_query.lower() for keyword in
                       ["restock", "inventory", "replenish"]) and "sales" not in user_query.lower():
                    return_response = True  # no need to call the llm again to prevent the supervisor agent from calling the inventory_management_agent again even though it already return the final answer and it passed the check from the supervisor.


    elif isinstance(last_message, AIMessage) and last_message.additional_kwargs.get(
            "agent_name") == "sales_analyst_agent":
        if last_message.additional_kwargs.get("request_data"):
            # Immediately create a tool call to SQL agent
            data_requirements = last_message.content  # assume LLM response includes data need
            tool_call = {
                "name": "transfer_to_sql_agent",
                "args": {"data_requirements": data_requirements},
                "type": "tool_call",
                "id": str(uuid.uuid4())
            }

            messages.append(
                AIMessage(content="", tool_calls=[tool_call], additional_kwargs={"agent_name": "supervisor_agent"})
            )
            return Command(goto="SQL_AGENT",
                           update={"messages": messages, "last_sql_requester": "sales_analyst_agent"})
        else:
            # Mark sales agent as completed
            completed_agents.add("sales_analyst_agent")
            # reflect on the response returned by the agent
            is_correct, reflection_output = check_agent_response(messages, "sales_analyst_agent")
            if reflection_output:
                messages.append(
                    AIMessage(content=reflection_output, additional_kwargs={"agent_name": "supervisor_agent"}))
            if not is_correct:
                # Remove from completed if incorrect
                completed_agents.discard("inventory_management_agent")
                follow_up = parse_required_follow_up(reflection_output)
                next_agent = agent_names_map[follow_up] if follow_up != 'none' else agent_names_map['supervisor_agent']
                return Command(goto=next_agent, update={"messages": messages})
            else:
                # We consider the sales analyst agent finished its work when it pass the check from supervisor agent
                if any(keyword in user_query.lower() for keyword in ["sales"]) and not any(
                        banned in user_query.lower() for banned in ["restock", "inventory", "replenish"]):
                    return_response = True  # no need to call the llm again to prevent the supervisor agent from calling the inventory_management_agent again even though it already return the final answer and it passed the check from the supervisor.

    # If no new tool calls, but we still have pending agents to dispatch
    if state.get("pending_agents"):
        next_agent = state["pending_agents"].pop(0)
        return Command(
            goto=next_agent,
            update={
                "messages": messages + [AIMessage(content=last_message.content, tool_calls=last_message.tool_calls,
                                                  additional_kwargs={"agent_name": "supervisor_agent"}
                                                  )],
                "pending_agents": state["pending_agents"]
            }
        )
    if not return_response:
        stream = client.chat.completions.create(
            model="Qwen/Qwen3-4B",
            messages=converted_messages,
            tools=SUPERVISOR_TOOLS,
            tool_choice="auto",
            max_tokens=500,
            temperature=0.7,
            stream=True  # Enable streaming
        )

        # Initialize accumulators
        collected_content = ""
        collected_tool_calls = []

        print("🤖 Agent responding: ", end='', flush=True)

        for chunk in stream:
            delta = chunk.choices[0].delta
            # Stream content
            if delta.content:
                print(delta.content, end='', flush=True)
                collected_content += delta.content
            # Handle tool call deltas
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    index = tool_call_delta.index if hasattr(tool_call_delta, 'index') else 0
                    # Ensure the tool_calls list has a slot for this index
                    while len(collected_tool_calls) <= index:
                        collected_tool_calls.append({
                            'id': '',
                            'type': 'function',
                            'function': {
                                'name': '',
                                'arguments': ''
                            }
                        })
                    # Update the specific tool call at this index
                    tc = collected_tool_calls[index]
                    if tool_call_delta.id:
                        tc['id'] = tool_call_delta.id
                    if tool_call_delta.type:
                        tc['type'] = tool_call_delta.type
                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            tc['function']['name'] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            # Make sure arguments field is a string before appending
                            if tc['function']['arguments'] is None:
                                tc['function']['arguments'] = ''
                            tc['function']['arguments'] += tool_call_delta.function.arguments

        # print("\n")  # New line after streaming

        # Print parsed tool calls
        # if collected_tool_calls:
        #     for i, tool_call in enumerate(collected_tool_calls):
        #         func = tool_call['function']
        #         if func['name']:
        #             print(f" 🔧 Calling {func['name']}")
        #             try:
        #                 args = json.loads(func['arguments'])
        #                 if 'instruction' in args:
        #                     print(f"      Instruction: {args['instruction']}")
        #                 elif 'query' in args:
        #                     print(f"      Query: {args['query']}")
        #             except Exception as e:
        #                 print(f"      Arguments (raw): {func['arguments']}")

        # Parse into AI message format
        final_message = {
            "content": collected_content,
            "tool_calls": collected_tool_calls if collected_tool_calls else []
        }

        ai_message = try_parse_tool_calls(final_message)

        # Assume try_parse_tool_calls returns a list, get the last one
        last_message = ai_message[-1] if isinstance(ai_message, list) else ai_message

        # trying to handle multiple tool calls
        # If tool_calls exist, store pending agents and dispatch the first one
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            messages.append(AIMessage(
                content=last_message.content,
                tool_calls=last_message.tool_calls,
                additional_kwargs={"agent_name": "supervisor_agent"}
            ))

            # Queue up unique agents based on tool call names
            agent_map = {
                "transfer_to_sql_agent": "SQL_AGENT",
                "transfer_to_inventory_agent": "INVENTORY_MANAGEMENT_AGENT",
                "transfer_to_sales_agent": "SALES_ANALYST_AGENT"
            }

            pending_agents = []
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                if tool_name in agent_map:
                    agent = agent_map[tool_name]
                    if agent not in pending_agents:
                        pending_agents.append(agent)

            # Pop the first agent to dispatch now, keep the rest in state
            next_agent = pending_agents.pop(0)

            return Command(
                goto=next_agent,
                update={
                    "messages": messages,
                    "pending_agents": pending_agents
                }
            )

    # When there is no tool call detected
    # check whether the second last message is from the user, and the supervisor agent did not make any tool call therefore this mean we dont need to go until summarization just return them back.

    if len(messages) >= 1 and isinstance(messages[-1], HumanMessage):
        # Return the response from the llm
        messages.append(
            AIMessage(
                content=collected_content.replace("<think>", "").replace("</think>", "").strip(),
                additional_kwargs={"agent_name": "supervisor_agent"}))

        # Finish execution
        return Command(goto=END, update={"messages": messages})

    # Find all important responses from agents in the conversation
    # 🐛 FIX: Only summarize agent responses from the CURRENT conversational turn
    agent_responses = []
    last_human_idx = 0
    
    # Find the index of the most recent user question
    for i, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            last_human_idx = i

    # Only extract AI responses that happened AFTER the user's question
    for msg in messages[last_human_idx:]:
        if isinstance(msg, AIMessage) and msg.content and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
            agent_responses.append(msg.content)

    #  include the agent_responses in the prompt
    agent_responses_text = "\n\n".join(agent_responses)

    # print("####USER QUERY: " + user_query)

    summary_prompt = f"""Return the answer for user question: "{user_query}"
    Agent responses:
    {agent_responses_text}

    Important Guidelines for Summarization:
    - Do not fabricate or assume any values. If the sales analyst agent (or any other agent) omits key data, do not invent or estimate these figures under any circumstances.
    - If the user asks a hypothetical "What If" question (e.g., "At what percentage of demand do we need to restock?"), DO NOT invent math examples. State clearly: "Restock thresholds are calculated per-product based on their specific Lead Time and Safety Stock. Please specify a product ID to simulate a demand increase."
    - STRICT RULE: You are a professional executive assistant. DO NOT output any internal thought processes. DO NOT output <think> tags. Do not explain your methodology. 

    Provide a concise answer (MUST be under 100 words) with:
    - Direct answer to the user's question
    - No background explanations

    If no relevant data found, ask user to provide more details.
    """
    msgs = [
        {"role": "user", "content": summary_prompt + "/no_think"}
    ]

    response = client.chat.completions.create(
        model="Qwen/Qwen3-4B",
        messages=msgs,
        max_tokens=2500,
        temperature=0.1,
    )
    # Add summary response to messages
    messages.append(
        AIMessage(content=response.choices[0].message.content.replace("<think>", "").replace("</think>", "").strip(),
                  additional_kwargs={"agent_name": "supervisor_agent"}))

    # Finish execution with final summarized response
    return Command(goto=END, update={"messages": messages})


# reflect on the responses return by the agents
def check_agent_response(messages: list, agent_name: str) -> Tuple[bool, Optional[str]]:
    # Extract user query
    user_query = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break
            
    # Collect up to the last 2 responses to save tokens
    agent_responses = []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            agent_responses.append(f"from {msg.additional_kwargs.get('agent_name', 'unknown')}: {msg.content}")
        if len(agent_responses) == 2:
            break
            
    if not agent_responses or not user_query:
        return True, None 

    agent_responses_text = "\n\n".join(reversed(agent_responses))

    reflection_prompt = f"""
    You are the Supervisor. Verify if the agents are completing their tasks correctly.
    
    User query: "{user_query}"
    
    Sub-Agents:
    - sql_agent → Fetches data.
    - inventory_management_agent → Plans restocks.
    - sales_analyst_agent → Analyzes sales.

    CRITICAL RULES:
    1. If the SQL agent returns ANY data array (even if it seems weird), ACCEPT IT. Do not reject data.
    2. If an agent is "waiting_for_sql_agent_response", ACCEPT IT.
    3. You are strictly forbidden from writing explanations, feedback, or analysis. 
    
    You MUST respond ONLY with these exact two lines, and absolutely nothing else:
    - correctness_check: [yes/no]
    - required_follow_up: [agent_name or none]

    Agent Responses:
    {agent_responses_text}
    """

    reflection_response = client.chat.completions.create(
        model="Qwen/Qwen3-4B",
        messages=[{"role": "user", "content": reflection_prompt.strip() + "\n/no_think"}],
        max_tokens=50, # 🛡️ FORCED TOKEN LIMIT so it physically cannot write an essay
        temperature=0.1,
    )

    reflection_output = reflection_response.choices[0].message.content.replace("<think>", "").replace("</think>", "").strip()
    
    if "- correctness_check: no" in reflection_output.lower():
        return False, reflection_output
    return True, reflection_output


def parse_required_follow_up(reflection_output):
    """Parse the required_follow_up agent name from reflection_output string cleanly."""
    try:
        lines = reflection_output.strip().split('\n')
        for line in lines:
            if 'required_follow_up:' in line.lower():
                agent_name = line.split(':', 1)[1].strip().lower()
                # Remove brackets or random punctuation
                agent_name = agent_name.replace('[', '').replace(']', '').strip()
                return agent_name if agent_name != 'none' else 'none'
        return 'none'
    except Exception:
        return 'none'


def sql_agent_node(state: SupervisorState) -> Command[Literal["SUPERVISOR_AGENT"]]:
    messages = state["messages"]

    # Extract data requirements from most recent supervisor message with tool call
    data_requirements = None
    for msg in reversed(messages):
        if (isinstance(msg, AIMessage) and msg.additional_kwargs.get("agent_name") == "supervisor_agent"
                and hasattr(msg, 'tool_calls') and msg.tool_calls):
            for tool_call in msg.tool_calls:
                if tool_call["name"] == "transfer_to_sql_agent" and "data_requirements" in tool_call["args"]:
                    data_requirements = tool_call["args"]["data_requirements"]
                    break
            if data_requirements:
                break

    sql_system_prompt = SystemMessage(content=f"""
    You are a MySQL data retrieval specialist that returns exactly the data requested.

    Process:
    1. Extract and list all specific fields mentioned in the request.
    2. MUST use list_tables_tool to identify which tables contain these fields.
    3. Write the SELECT query.
    4. IMMEDIATELY execute the query using `db_query_tool`. (Do NOT use `query_checker_tool`).

    Response format:
    - Output the query result as a **JSON array of objects**, where each object is a row.
    - DO NOT use Markdown tables or plain text. Return ONLY structured JSON.

    Critical rules:
    - NEVER omit any requested field.
    - ONLY query the `inventory` table. NEVER query a table named `inventory_data`.
    - When the user refers to '{current_month_year}', format it as '2026-04' in the query using: `WHERE DATE_FORMAT(Date, '%Y-%m') = '2026-04'`.
    - DO NOT use AVG on a single date's data.
    - MySQL ONLY_FULL_GROUP_BY Rule: Every column in your SELECT clause MUST be wrapped in an aggregation function (like SUM or MAX) OR it MUST be listed in the GROUP BY clause.
    
    - If the Sales Analyst Agent asks for Units Sold/Revenue for one or more full months:
      1. ALWAYS use aggregation functions: `SUM(Units_Sold) AS Units_Sold` and `SUM(Units_Sold * Price * (1 - Discount/100)) AS Revenue`
      2. ALWAYS Refer this exact example:
         ```sql
            SELECT
              Store_ID,
              Product_ID,
              Category,
              DATE_FORMAT(Date, '%Y-%m') AS Month,
              SUM(Units_Sold) AS Units_Sold,
              SUM(Units_Sold * Price * (1 - Discount/100)) AS Revenue
            FROM inventory
            WHERE Store_ID = 'S004'
              AND DATE_FORMAT(Date, '%Y-%m') = '2026-04'
            GROUP BY Store_ID, Product_ID, Category, DATE_FORMAT(Date, '%Y-%m');
         ```

    - If the Inventory Management Agent requests inventory data to plan restocks:
      1. You need the current inventory, total demand (sales) for that month, safety stock, and lead time.
      2. You MUST wrap the static numbers (Inventory_Level, Safety_Stock, Lead_Time_Days) in MAX() to satisfy MySQL grouping rules.
      3. MUST copy this EXACT single-query example to avoid Error 1055:
      ```sql
        SELECT 
            Product_ID, 
            Category, 
            MAX(Inventory_Level) AS Inventory_Level, 
            MAX(Safety_Stock) AS Safety_Stock, 
            MAX(Lead_Time_Days) AS Lead_Time_Days, 
            SUM(Units_Sold) AS Monthly_Demand 
        FROM inventory 
        WHERE DATE_FORMAT(Date, '%Y-%m') = '2026-04' 
        GROUP BY Product_ID, Category;
      ```

    Checklist before final output:
    ✅ Query includes ALL requested fields (including Category if asked)
    ✅ MySQL Grouping Rules are satisfied (un-grouped columns use MAX or SUM)
    ✅ Output is structured JSON with no markdown or commentary

    /no_think
    """)

    # Create messages for SQL agent by filtering out supervisor system message and simplifying AI messages
    sql_messages = [sql_system_prompt]

    # Extract the last 4 AI and human messages
    last_messages = [
        msg for msg in messages
        if isinstance(msg, AIMessage) or isinstance(msg, ToolMessage) or isinstance(msg, HumanMessage)
    ]
    last_four_messages = last_messages[-4:]

    for msg in last_four_messages:
        if msg.content:
            if isinstance(msg, HumanMessage):
                sql_messages.append({
                    "role": "user",
                    "name": "user",
                    "content": msg.content
                })
            else:
                role_name = msg.additional_kwargs.get("agent_name", msg.name or "assistant")
                sql_messages.append({
                    "role": "assistant",
                    "name": role_name,
                    "content": msg.content
                })
    # include the data requirement from the supervisor agent
    if data_requirements:
        sql_messages.append({
            "role": "assistant",
            "name": "supervisor_agent",
            "content": data_requirements
        })
    # Now invoke the SQL agent with the properly prepared messages
    result = sql_agent.invoke({"messages": sql_messages})

    # Take the final message from the SQL agent and append it to the original message history
    sql_response = result["messages"][-1]

    # Create a tagged AIMessage with agent_name = "sql_agent"
    tagged_response = AIMessage(
        content=sql_response.content,
        additional_kwargs={"agent_name": "sql_agent", "intended_for": state.get("last_sql_requester")}
    )

    # store into a list specifically for storing the sql data retrieved by sql agent
    # Usage
    if is_valid_json(sql_response.content):
        raw_data = json.loads(sql_response.content)
        sql_data = {
            'data': raw_data,
            'intended_for': state.get("last_sql_requester"),
            'record_count': len(raw_data) if isinstance(raw_data, list) else 1
        }
        return Command(
            goto="SUPERVISOR_AGENT",
            update={"messages": messages + [tagged_response], "sql_data": sql_data}
        )
    else:
        return Command(
            goto="SUPERVISOR_AGENT",
            update={"messages": messages + [tagged_response]}
        )


def is_valid_json(json_str):
    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def inventory_management_agent_node(state: SupervisorState) -> Command[Literal["SUPERVISOR_AGENT"]]:
    messages = state["messages"]

    # Extract instruction from most recent supervisor message with tool call
    instruction = None
    for msg in reversed(messages):
        if (isinstance(msg, AIMessage) and msg.additional_kwargs.get("agent_name") == "supervisor_agent"
                and hasattr(msg, 'tool_calls') and msg.tool_calls):
            for tool_call in msg.tool_calls:
                if tool_call["name"] == "transfer_to_inventory_agent" and "instruction" in tool_call["args"]:
                    instruction = tool_call["args"]["instruction"]
                    break
            if instruction:
                break

    # Insert system prompt for inventory logic
    system_prompt = SystemMessage(content=f"""
    You are the Inventory Management Agent.

    Your role is to determine restocking needs and create restock plans strictly based on provided inventory and sales data.

    Your workflow:

    1. **Check for completeness**:
       - Look through all previous messages to determine if the SQL agent has already provided inventory data. If NO data, call `get_inventory_data_tool`.
       - The data is considered complete ONLY if it contains ALL of these fields: `Product_ID`, `Inventory_Level`, `Monthly_Demand`, `Safety_Stock`, and `Lead_Time_Days`.

    2. **If data is missing or incorrect**:
       - If data is missing required fields or appears invalid, call the `get_inventory_data_tool` with a specific request.
       - You must also explicitly state **why** the existing data is incorrect or incomplete — mention the missing or invalid fields in your tool call message.
       - Do NOT merely describe what you need. Always use a tool call and justify it.

    3. **Once data is received from the SQL agent**:
       - MUST IMMEDIATELY make tool call to `analyze_inventory_levels_tool` using the received data.
       - This step is mandatory after you detect a full dataset from the SQL agent.

    4. **Generate a restock plan**:
       - Before generating the restock plan, it is a must to call `analyze_inventory_levels_tool` to get the inventory analysis.
       - Based on the results of the analysis, call `generate_restock_plan_tool`(ONLY call this when there are generated results for inventory analysis).
       - The restock plan should only include products marked as needing restock, with explanations and suggested quantities based solely on the data.
       - If all the products does not need restocking, just return back the response.

    Rules:
    - Do NOT re-request data if it already exists.
    - Do NOT analyze, summarize, or interpret the meaning of the data yourself — always use tools.
    - Do NOT return restock plan without calling `generate_restock_plan_tool`
    - NEVER fabricate or infer missing values.
    - Focus only on actionable, factual decisions.
    - For user queries about specific restocks, only request data for the last day of the month.
    - MUST put your tool call inside <tool_call></tool_call>
    - When the agent or user refers to 'current month', interpret it as {current_month_year}.
    /no_think
    """)

    # Convert LangGraph messages to LLM-compatible format
    converted_messages = [system_prompt]
    for msg in messages:
        if isinstance(msg, SystemMessage):
            # Skip supervisor system message
            continue
        elif isinstance(msg, AIMessage):
            role_name = msg.additional_kwargs.get("agent_name", "assistant")

            # Filter out irrelevant SQL messages
            if role_name == "sql_agent":
                intended_for = msg.additional_kwargs.get("intended_for")
                if intended_for and intended_for != "inventory_management_agent":
                    continue  # Skip this SQL message if it's not for the sales analyst
            if role_name == "sales_analyst_agent":
                continue  # skip messages from inventory management agent

            if msg.content:
                converted_messages.append({
                    "role": "assistant",
                    "name": role_name,
                    "content": msg.content
                })
        else:
            # Add all other messages as is
            converted_messages.append(msg)

    if instruction:
        converted_messages.append({
            "role": "assistant",
            "name": "supervisor_agent",
            "content": instruction
        })
    sql_data = state.get("sql_data", {})
    # Now invoke the inventory agent with the properly prepared messages
    result = inventory_agent.invoke({"messages": converted_messages, "sql_data": sql_data})

    # Take the final message from the SQL agent and append it to the original message history
    inventory_response = result["messages"][-1]

    tagged_response = AIMessage(
        content=inventory_response.content,
        additional_kwargs={**inventory_response.additional_kwargs, "agent_name": "inventory_management_agent"}
    )

    return Command(
        goto="SUPERVISOR_AGENT",
        update={"messages": messages + [tagged_response]}
    )


def sales_analyst_agent_node(state: SupervisorState) -> Command[Literal["SUPERVISOR_AGENT"]]:
    messages = state["messages"]
    # Extract instruction from most recent supervisor message with tool call
    instruction = None
    for msg in reversed(messages):
        if (isinstance(msg, AIMessage) and msg.additional_kwargs.get("agent_name") == "supervisor_agent"
                and hasattr(msg, 'tool_calls') and msg.tool_calls):
            for tool_call in msg.tool_calls:
                if tool_call["name"] == "transfer_to_sales_agent" and "instruction" in tool_call["args"]:
                    instruction = tool_call["args"]["instruction"]
                    break
            if instruction:
                break
    system_prompt = SystemMessage(content=f"""
     You are the Sales Analyst Agent.

     Your role is to provide clear and insightful summaries of recent sales performance strictly based on raw sales data.

     Your workflow:

     1. **Check for existing sales data**:
        - Look through previous messages from the SQL agent. If NO data from SQL agent, you MUST call `get_sales_data_tool`.
        - If the user or another agent asks for "top", "most", "highest", or any ranked/aggregated result, ensure you request the data sorted — e.g., descending by Units_Sold or Revenue.
        - You must NOT use data from Inventory Management Agent or Supervisor Agent.
        - Data is considered valid only if all records include values for: `Product_ID` or `Category`, `Units_Sold`, `Revenue`, and `Date/Month`.

     2. **Determine the appropriate date range** based on the user query:

        - ✅ If the user query is asking for **sales trends, comparisons, or performance changes over time**, you MUST retrieve:
          - BOTH the requested month AND the preceding month (e.g., if asked for April, fetch March AND April).
          - You MUST explicitly instruct the SQL agent to group the data by `Product_ID` and `Month`.
          - You MUST explicitly ask for `Product_ID`, `Category`, `Units_Sold`, and `Revenue`.
          - Example triggers: "How did sales change?", "Compare December to November", "give me a sales trend"

        - ✅ If the user is asking for **a specific metric or extreme value limited to one month** (e.g., “What category had the most sales in December?”), you MUST:
          - Retrieve data for **only the requested month**.
          - You MUST explicitly ask the SQL agent to include `Product_ID`, `Category`, `Units_Sold`, and `Revenue`.

     3. **If data is missing or incomplete**:
        - MUST Call `get_sales_data_tool` with a **clear instruction** explaining EXACTLY which columns you need.
        - NEVER ask the SQL agent to "summarize" or "analyze" - it can only fetch raw database rows! 
        - Example of a GOOD trend request: "Get Units_Sold and Revenue grouped by Product_ID, Category, and Month for March 2026 and April 2026."

     4. **Once valid data is available**:
        - Call `summarize_sales_tool` ONLY when these fields are in the recent data:`Product_ID` or `Category`, `Units_Sold`, `Revenue`, and `Date/Month` ,else DO NOT call `summarize_sales_tool` and you are allow to analyze the sales data when necessary without that tool.

     Rules:
     - NEVER fabricate or guess any data.
     - NEVER perform your own calculations or logic-based interpretations.
     - You are not allowed to say you "will" or "need to" call a tool. You MUST actually emit the <tool_call>...</tool_call> JSON block.
     - When the agent or user refers to 'current month', interpret it as {current_month_year}.
     - STRICT GAG ORDER: You are a Sales Analyst. You MUST NEVER mention restocking, inventory levels, or restock plans in your output. If the user asks about restocking, ignore it completely and ONLY output sales metrics.

     /no_think
     """)

    # Prepare messages
    converted_messages = [system_prompt]
    for msg in messages:
        if isinstance(msg, SystemMessage):
            continue

        elif isinstance(msg, AIMessage):
            role_name = msg.additional_kwargs.get("agent_name", "assistant")

            # Filter out irrelevant SQL messages
            if role_name == "sql_agent":
                intended_for = msg.additional_kwargs.get("intended_for")
                if intended_for and intended_for != "sales_analyst_agent":
                    continue  # Skip this SQL message if it's not for the sales analyst
            if role_name == "inventory_management_agent":
                continue  # skip messages from inventory management agent

            if msg.content:
                converted_messages.append({
                    "role": "assistant",
                    "name": role_name,
                    "content": msg.content
                })

        else:
            # Human messages or others
            converted_messages.append(msg)

    if instruction:
        converted_messages.append({
            "role": "assistant",
            "name": "supervisor_agent",
            "content": instruction
        })
    sql_data = state.get("sql_data", {})

    # Run the sales analyst agent with converted messages
    result = sales_agent.invoke({"messages": converted_messages, "sql_data": sql_data})

    # Get the latest response
    sales_response = result["messages"][-1]
    tagged_response = AIMessage(
        content=sales_response.content,
        additional_kwargs={**sales_response.additional_kwargs, "agent_name": "sales_analyst_agent"}
    )

    return Command(
        goto="SUPERVISOR_AGENT",
        update={"messages": messages + [tagged_response]}
    )


multi_agent_builder = StateGraph(SupervisorState)
multi_agent_builder.add_node("SUPERVISOR_AGENT", supervisor_node)
multi_agent_builder.add_node("SQL_AGENT", sql_agent_node)
multi_agent_builder.add_node("INVENTORY_MANAGEMENT_AGENT", inventory_management_agent_node)
multi_agent_builder.add_node("SALES_ANALYST_AGENT", sales_analyst_agent_node)

multi_agent_builder.add_edge(START, "SUPERVISOR_AGENT")

multi_agent = multi_agent_builder.compile()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import List, Tuple, AsyncGenerator, Union
import html
from contextlib import asynccontextmanager

# In-memory store (replace with Redis in production)
conversation_store: Dict[str, List] = {}
# Track active streams
active_streams = {}  # {session_id: asyncio.Event}
# Track cancellation events
cancellation_events = {}  # {session_id: asyncio.Event}
active_tasks = {}  # {session_id: (task, cancel_event)}


# Helper function to extract (agent_name, tool_call) tuples from chunk data
def extract_tool_calls_from_chunk(chunk_data) -> List[Tuple[str, object]]:
    """
    Extracts tool calls from a chunk, handling both dict and object types.
    Returns list of (agent_name, tool_call).
    """
    tool_calls = []
    # Access 'update' safely
    update = chunk_data.get("update") if isinstance(chunk_data, dict) else getattr(chunk_data, "update", None)
    if not update:
        return []

    # Access messages safely
    messages = update.get("messages") if isinstance(update, dict) else getattr(update, "messages", [])

    for msg in messages:
        additional = getattr(msg, "additional_kwargs", {}) or {}
        raw_name = additional.get("agent_name") or getattr(msg, "name", None) or "UNKNOWN"
        agent_name = raw_name.strip().upper()

        # Tool calls can be in .tool_calls attr or additional kwargs
        tool_calls_list = getattr(msg, "tool_calls", []) or additional.get("tool_calls", [])
        for tool_call in tool_calls_list:
            tool_calls.append((agent_name, tool_call))

    return tool_calls


# Helper generator to format and yield tool calls for SSE
def format_and_yield_tool_call(agent_name: str, tool_call: object) -> List[str]:
    """Format tool call with proper styling and return as list of SSE chunks."""
    tool_call_id = getattr(tool_call, "id", str(tool_call))
    content = str(tool_call)

    formatted_tool = f"<div style='margin: 12px 0; padding: 12px; background: #1a1a1a; border-radius: 4px; font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif; box-shadow: 0 1px 2px rgba(0,0,0,0.1);'><div style='display: flex; align-items: center; gap: 8px; margin-bottom: 8px; color: #ffffff; font-weight: 600; font-size: 14px;'><svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z'></path></svg>Tool Call</div><div style='background: #252526; padding: 10px; border-radius: 4px; font-size: 14px; line-height: 1.5;'><div style='margin-bottom: 6px;'><span style='color: #9cdcfe; font-weight: 500;'>🔧 Tool:</span><br><span style='color: #ce9178;'>{html.escape(str(tool_call.get('name', 'Unknown')))}</span></div><div><span style='color: #9cdcfe; font-weight: 500;'>🗂️ Arguments:</span><br><pre style='margin: 5px 0 0; padding: 8px; background: #1e1e1e; border-radius: 3px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; color: #d4d4d4; font-family: \"Consolas\", monospace; font-size: 14px;'>{html.escape(str(tool_call.get('args', 'None')).replace("/no_think", ""))}</pre></div></div></div>"

    return [f"data: {formatted_tool}\n\n"]


# Format data results from the sql_agent
def format_sql_results(content: str) -> str:
    """Formats SQL query results into a readable table, showing all data."""
    try:
        import json
        data = json.loads(content)
        if not isinstance(data, list) or not data: return content

        # Get columns in original order from first item
        columns = list(data[0].keys()) if data else []

        # Numeric columns detection
        numeric_columns = [col for col in columns if any(isinstance(item.get(col), (int, float)) for item in data)]

        # Generate summaries
        numeric_summaries = []
        for col in numeric_columns:
            values = [item.get(col, 0) for item in data if col in item]
            if values:
                total = sum(values)
                avg = total / len(values)
                numeric_summaries.append(
                    f"<div><span style='color: #9cdcfe;'>{col}:</span> Total={total:,.2f}, Avg={avg:,.2f}</div>")

        # Generate full table with all rows
        headers = "".join(
            f"<th style='padding: 8px; text-align: {'right' if col in numeric_columns else 'left'};'>{col}</th>" for col
            in columns)
        rows = "".join(f"<tr style='border-bottom: 1px solid #333;'>" + "".join(
            f"<td style='padding: 6px 8px; text-align: {'right' if col in numeric_columns else 'left'};'>{item.get(col, '') if not isinstance(item.get(col), (int, float)) else f'{item.get(col):,.2f}' if isinstance(item.get(col), float) else f'{item.get(col):,}'}</td>"
            for col in columns) + "</tr>" for item in data)

        return f"<div style='margin: 15px 0; padding: 15px; background: #1e1e1e; border-radius: 5px; font-family: monospace;'><div style='margin-bottom: 15px;font-weight: bold;'>📊 Query Results ({len(data)} rows)</div>{f'<div style=\"margin-bottom: 15px; font-size: 14px;\">' + ''.join(numeric_summaries) + '</div>' if numeric_summaries else ''}<div style='max-height: 213px; overflow-y: auto; border: 1px solid #333; border-radius: 3px;'><table style='width: 100%; border-collapse: collapse; font-size: 14px;'><thead><tr style='background: #252526; position: sticky; top: 0;'>{headers}</tr></thead><tbody>{rows}</tbody></table></div></div>"
    except Exception:
        return content


# format response from inventory_management_agent or sales_analyst agent when they are waiting data from sql_agent
def format_waiting_response(agent_name: str, content: str) -> str:
    """Formats waiting responses from inventory/sales agents."""
    try:
        # Handle the "/no_think" suffix if present
        json_str = content.split('/no_think')[0].strip()
        data = json.loads(json_str)
        status = data.get("status", "")
        requested = data.get("requested", "")
        if status == "waiting_for_sql_agent_response":
            return f"<div style='margin: 15px 0; padding: 15px; background: #1e1e1e;  border-radius: 4px; font-family: monospace;'><div style='display: flex; align-items: center; gap: 8px; margin-bottom: 8px;'><span style='font-weight: 600;'>⏳ Waiting for SQL data</span></div><div style='background: #252526; padding: 10px; border-radius: 4px;'><div style='color: #9cdcfe; margin-bottom: 5px;'>Requested Data:</div><div style='color: #d4d4d4;'>{requested}</div></div></div>"
        return content
    except Exception:
        return content


# Main async generator function for streaming multi-agent responses
async def generate_agent_responses(
        session_id: str,
        user_message: str,
        cancellation_event: asyncio.Event
) -> AsyncGenerator[str, None]:
    """
    Modified version with proper cancellation support
    """
    try:
        # Initialize conversation
        if session_id not in conversation_store:
            conversation_store[session_id] = []
        conversation_store[session_id].append({"role": "user", "content": user_message})

        # Prepare messages
        recent_messages = conversation_store[session_id][-15:]
        messages = []
        for msg in recent_messages:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("agent") != "SQL_AGENT":
                messages.append(AIMessage(content=msg["content"]))

        agent_buffers = {}
        tool_call_ids = set()
        last_streaming_agent = None
        agent_header_shown = set()
        seen_message_ids = {}

        async for event in multi_agent.astream_events(
                {"messages": messages},
                {"recursion_limit": 100},
                version="v1"
        ):
            # Check for cancellation before processing each event
            if cancellation_event.is_set():
                yield "data: [CANCELLED]\n\n"
                raise asyncio.CancelledError()

            event_type = event.get("event")
            event_name = event.get("name", "")

            if event_type == "on_chain_stream" and "AGENT" in event_name:
                chunk = event.get("data", {}).get("chunk", {})

                # Process tool calls
                for agent_name, tool_call in extract_tool_calls_from_chunk(chunk):
                    if cancellation_event.is_set():
                        yield "data: [CANCELLED]\n\n"
                        raise asyncio.CancelledError()

                    tool_call_id = getattr(tool_call, "id", str(tool_call))
                    if tool_call_id in tool_call_ids:
                        continue
                    tool_call_ids.add(tool_call_id)

                    if last_streaming_agent != agent_name:
                        if last_streaming_agent is not None:
                            yield f"data: <hr style='margin: 15px 0; border: none; border-top: 1px solid #ddd;'>\n\n"
                        yield f"data: <div class='header-{agent_name.lower().replace('_', '-')}' style='margin: 10px 0; padding: 8px; background: #111111; border-left: 3px solid #007acc; border-radius: 3px;'><strong>🤖 {agent_name}</strong></div>\n\n"
                        last_streaming_agent = agent_name
                        agent_header_shown.add(agent_name)

                    for sse_chunk in format_and_yield_tool_call(agent_name, tool_call):
                        if cancellation_event.is_set():
                            yield "data: [CANCELLED]\n\n"
                            raise asyncio.CancelledError()
                        yield sse_chunk

                # Process messages
                update = chunk.get("update") if isinstance(chunk, dict) else getattr(chunk, "update", None)
                messages_list = update.get("messages") if isinstance(update, dict) else getattr(update, "messages", [])

                new_agent_messages = []
                latest_content = conversation_store[session_id][-1]["content"] if conversation_store[session_id] else ""

                for msg in messages_list:
                    if cancellation_event.is_set():
                        yield "data: [CANCELLED]\n\n"
                        raise asyncio.CancelledError()

                    if (getattr(msg, "type", "") == "ai" and
                            msg.content and
                            msg.content.strip() != latest_content):

                        msg_content = msg.content.strip()
                        additional = getattr(msg, "additional_kwargs", {}) or {}
                        raw_name = additional.get("agent_name") or getattr(msg, "name", None) or "Human"
                        agent_name = raw_name.strip().upper()

                        agent_msg = {
                            "role": "assistant",
                            "content": msg_content,
                            "agent": agent_name
                        }

                        if not conversation_store[session_id] or conversation_store[session_id][-1][
                            "content"] != msg_content:
                            new_agent_messages.append(agent_msg)
                            latest_content = msg_content

                if new_agent_messages:
                    conversation_store[session_id].extend(new_agent_messages)

                for msg in messages_list:
                    if cancellation_event.is_set():
                        yield "data: [CANCELLED]\n\n"
                        raise asyncio.CancelledError()

                    additional = getattr(msg, "additional_kwargs", {}) or {}
                    raw_name = additional.get("agent_name") or getattr(msg, "name", None) or "Human"
                    agent_name = raw_name.strip().upper()

                    if not hasattr(msg, "content") or not msg.content or agent_name == 'HUMAN':
                        continue

                    msg_content = msg.content.strip()
                    if not msg_content:
                        continue

                    msg_id = getattr(msg, "id", None)
                    if not msg_id:
                        msg_id = f"{agent_name}-{hash(msg_content)}"

                    if agent_name not in seen_message_ids:
                        seen_message_ids[agent_name] = set()

                    if msg_id in seen_message_ids[agent_name]:
                        continue
                    seen_message_ids[agent_name].add(msg_id)

                    if agent_name not in agent_buffers:
                        agent_buffers[agent_name] = ""

                    prev_buffer = agent_buffers[agent_name]

                    if msg_content.startswith(prev_buffer):
                        new_chars = msg_content[len(prev_buffer):]
                    else:
                        new_chars = msg_content
                        agent_buffers[agent_name] = ""

                    agent_buffers[agent_name] = msg_content
                    
                    # 🛡️ SAFETY NET: Brutally strip out any <think> tags Qwen tries to stream
                    new_chars = new_chars.replace("<think>", "").replace("</think>", "")
                    if "Let me think" in new_chars or "Okay, the user is asking" in new_chars:
                        continue # Skip rambling filler words

                    if new_chars.strip():
                        if last_streaming_agent != agent_name:
                            if last_streaming_agent is not None:
                                yield f"data: <hr style='margin: 15px 0; border: none; border-top: 1px solid #ddd;'>\n\n"
                            yield f"data: <div class='header-{agent_name.lower().replace('_', '-')}' style='margin: 10px 0; padding: 8px; background: #111111; border-left: 3px solid #007acc; border-radius: 3px;'><strong>🤖 {agent_name}</strong></div>\n\n"
                            last_streaming_agent = agent_name
                            agent_header_shown.add(agent_name)

                        if agent_name == "SQL_AGENT" and new_chars.strip().startswith("[{"):
                            formatted_content = format_sql_results(new_chars.strip())
                            yield f"data: {formatted_content}\n\n"
                        elif agent_name in ["INVENTORY_MANAGEMENT_AGENT",
                                            "SALES_ANALYST_AGENT"] and "waiting_for_sql_agent_response" in new_chars:
                            formatted_content = format_waiting_response(agent_name, new_chars.strip())
                            yield f"data: {formatted_content}\n\n"
                        else:
                            for line in new_chars.strip().splitlines():
                                yield f"data: {line}\n"
                            yield "\n"

    except asyncio.CancelledError:
        yield "data: [CANCELLED]\n\n"
        raise
    except Exception as e:
        print(f"Error in agent processing: {e}")
        yield "data: [ERROR]\n\n"
    finally:
        yield "data: [DONE]\n\n"


# @app.get("/retail-ai/stream")
# async def stream_multiagent(message: str, request: Request):
#     session_id = request.cookies.get("session_id") or str(uuid.uuid4())
#     response = StreamingResponse(
#         generate_agent_responses(session_id=session_id, user_message=message),
#         media_type="text/event-stream"
#     )
#     if not request.cookies.get("session_id"):
#         response.set_cookie(key="session_id", value=session_id)
#     return response
generator_tasks: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def cancellable_task(session_id: str):
    """Context manager for cancellable tasks"""
    cancel_event = asyncio.Event()
    task = asyncio.current_task()
    active_tasks[session_id] = (task, cancel_event)

    try:
        yield cancel_event
    except asyncio.CancelledError:
        print(f"Task cancelled for session {session_id}")
        raise
    finally:
        active_tasks.pop(session_id, None)


@app.get("/retail-ai/stream")
async def stream_multiagent(message: str, request: Request):
    session_id = request.cookies.get("session_id") or str(uuid.uuid4())

    async def event_generator():
        async with cancellable_task(session_id) as cancel_event:
            try:
                async for chunk in generate_agent_responses(session_id, message, cancel_event):
                    if cancel_event.is_set():
                        yield "data: [CANCELLED]\n\n"
                        break
                    yield chunk
            except (asyncio.CancelledError, GeneratorExit):
                # Cleanup or exit early
                yield "data: [CANCELLED]\n\n"
                return

    response = StreamingResponse(event_generator(), media_type="text/event-stream")
    if not request.cookies.get("session_id"):
        response.set_cookie(key="session_id", value=session_id)
    return response


@app.post("/retail-ai/cancel")
async def cancel_stream(request: Request):
    """Forcefully cancel the execution"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session ID provided")

    if session_id in active_tasks:
        task, cancel_event = active_tasks[session_id]
        cancel_event.set()  # Set cancellation flag
        task.cancel()  # Forcefully cancel the task
        return {"status": "execution_stopped"}
    return {"status": "no_active_task"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8181)
