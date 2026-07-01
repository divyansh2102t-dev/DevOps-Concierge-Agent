import json

active_connections = {}


async def connect_mcp(server_url, server_type="stdio"):
    connection_id = f"mcp_{len(active_connections)}"

    if server_type == "stdio":
        import asyncio
        try:
            process = await asyncio.create_subprocess_exec(
                *server_url.split(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "devops-concierge", "version": "1.0.0"}
                }
            }

            request_bytes = json.dumps(init_request).encode() + b"\n"
            process.stdin.write(request_bytes)
            await process.stdin.drain()

            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10)
            response = json.loads(response_line.decode())

            active_connections[connection_id] = {
                "process": process,
                "type": server_type,
                "url": server_url,
                "server_info": response.get("result", {}).get("serverInfo", {})
            }

            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            process.stdin.write(json.dumps(tools_request).encode() + b"\n")
            await process.stdin.drain()
            tools_line = await asyncio.wait_for(process.stdout.readline(), timeout=10)
            tools_response = json.loads(tools_line.decode())

            return {
                "success": True,
                "connection_id": connection_id,
                "server_info": response.get("result", {}).get("serverInfo", {}),
                "tools": tools_response.get("result", {}).get("tools", [])
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif server_type in ("sse", "http"):
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    server_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "devops-concierge", "version": "1.0.0"}
                        }
                    }
                )
                data = resp.json()
                active_connections[connection_id] = {
                    "type": server_type,
                    "url": server_url,
                    "server_info": data.get("result", {}).get("serverInfo", {})
                }
                return {
                    "success": True,
                    "connection_id": connection_id,
                    "server_info": data.get("result", {}).get("serverInfo", {})
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": f"Unknown server type: {server_type}"}


async def call_mcp_tool(connection_id, tool_name, arguments):
    conn = active_connections.get(connection_id)
    if not conn:
        return {"success": False, "error": "Connection not found"}

    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments}
    }

    if conn["type"] == "stdio":
        process = conn["process"]
        process.stdin.write(json.dumps(request).encode() + b"\n")
        await process.stdin.drain()
        import asyncio
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=30)
        response = json.loads(response_line.decode())
        return {"success": True, "result": response.get("result", {})}

    elif conn["type"] in ("sse", "http"):
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(conn["url"], json=request)
            return {"success": True, "result": resp.json().get("result", {})}

    return {"success": False, "error": "Unknown connection type"}


def list_connections():
    return {
        cid: {"type": c["type"], "url": c["url"], "server_info": c.get("server_info", {})}
        for cid, c in active_connections.items()
    }
