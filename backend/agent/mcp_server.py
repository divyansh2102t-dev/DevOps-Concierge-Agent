#!/usr/bin/env python3
import sys
import json
import os

# Ensure the root of the workspace is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agent.tool_registry import get_tool

def log(msg):
    # Print to stderr so we don't interfere with stdout JSON-RPC communication
    sys.stderr.write(f"[MCP Server Log] {msg}\n")
    sys.stderr.flush()

def respond(response_obj):
    sys.stdout.write(json.dumps(response_obj) + "\n")
    sys.stdout.flush()

def main():
    log("DevOps Concierge MCP Server starting...")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            log(f"Received: {line}")
            
            try:
                request = json.loads(line)
            except Exception as e:
                # Invalid JSON
                respond({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    },
                    "id": None
                })
                continue
            
            req_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})
            
            if method == "initialize":
                respond({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "devops-concierge-mcp",
                            "version": "1.0.0"
                        }
                    }
                })
                
            elif method == "tools/list":
                respond({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "check_credentials",
                                "description": "Query the status of local credentials and API keys (such as GITHUB_TOKEN, VERCEL_TOKEN, RENDER_TOKEN, and NEON_API_KEY). Returns a summary of which keys are configured and which are missing, without exposing their actual secret values.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {}
                                }
                            },
                            {
                                "name": "select_database",
                                "description": "Analyze project requirements and recommend the best database. Returns scored recommendations.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "requirements_text": {
                                            "type": "string",
                                            "description": "Text describing the project requirements"
                                        }
                                    },
                                    "required": ["requirements_text"]
                                }
                            }
                        ]
                    }
                })
                
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                log(f"Calling tool: {tool_name} with args: {arguments}")
                
                if tool_name not in ["check_credentials", "select_database"]:
                    respond({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method/Tool '{tool_name}' not found or unsupported via this MCP Server."
                        }
                    })
                    continue
                
                tool_func = get_tool(tool_name)
                if not tool_func:
                    respond({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: tool function '{tool_name}' could not be loaded."
                        }
                    })
                    continue
                    
                try:
                    result = tool_func(**arguments)
                    
                    # Wrap in standard MCP content format
                    mcp_result = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result)
                            }
                        ]
                    }
                    
                    respond({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": mcp_result
                    })
                except Exception as e:
                    respond({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32603,
                            "message": f"Error running tool '{tool_name}': {str(e)}"
                        }
                    })
            else:
                # Unsupported method
                respond({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found."
                    }
                })
                
        except Exception as e:
            log(f"Crash error in main loop: {str(e)}")
            try:
                respond({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal MCP server crash: {str(e)}"
                    },
                    "id": None
                })
            except Exception:
                pass

if __name__ == "__main__":
    main()
