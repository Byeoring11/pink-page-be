import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.core.logger import logger
from app.infrastructures.websocketV2.connection_manager import WebSocketManager, WebSocketHandler
from app.domains.stub.services.stub_ssh_service import StubSSHService


# Global instances
ws_manager = WebSocketManager()
ws_handler = WebSocketHandler(ws_manager)
router = APIRouter()


class StubWebSocketController:
    """Controller for stub WebSocket functionality"""
    
    def __init__(self):
        self.ssh_services = {}  # connection_id -> StubSSHService
    
    async def handle_ssh_command(self, connection_id: str, data: dict):
        """Handle SSH command execution request"""
        try:
            server_name = data.get("server", "")
            command = data.get("command", "")

            # Define stop_phrase in backend (not from frontend)
            stop_phrase = "CICS_PROMPT>"  # Default stop phrase for CICS commands

            if not all([server_name, command]):
                await ws_manager.send_json(connection_id, {
                    "type": "error",
                    "message": "Missing required fields: server, command"
                })
                return
            
            # Create SSH service for this connection
            ssh_service = StubSSHService()
            self.ssh_services[connection_id] = ssh_service
            
            # Set output callback to send data to WebSocket
            async def output_callback(output: str):
                await ws_manager.send_json(connection_id, {
                    "type": "output",
                    "data": output
                })
            
            ssh_service.set_output_callback(output_callback)
            
            # Get server configuration
            try:
                host, username, password = ssh_service.get_server_config(server_name)
            except ValueError as e:
                await ws_manager.send_json(connection_id, {
                    "type": "error",
                    "message": str(e)
                })
                return
            
            # Send connection status
            await ws_manager.send_json(connection_id, {
                "type": "status",
                "message": f"Connecting to {server_name}..."
            })
            
            # Connect to SSH server
            connected = await ssh_service.connect(host, username, password)
            if not connected:
                await ws_manager.send_json(connection_id, {
                    "type": "error",
                    "message": "Failed to connect to SSH server"
                })
                return
            
            await ws_manager.send_json(connection_id, {
                "type": "status", 
                "message": "Connected! Starting interactive shell..."
            })
            
            # Start interactive shell with command
            await ssh_service.start_interactive_shell(command, stop_phrase)
            
            # Send completion status
            await ws_manager.send_json(connection_id, {
                "type": "complete",
                "message": "Command execution completed"
            })
            
        except Exception as e:
            logger.error(f"Error handling SSH command: {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": f"SSH command execution failed: {str(e)}"
            })
        finally:
            # Clean up SSH service
            if connection_id in self.ssh_services:
                await self.ssh_services[connection_id].disconnect()
                del self.ssh_services[connection_id]
    
    async def handle_ssh_input(self, connection_id: str, data: dict):
        """Handle user input to SSH session"""
        try:
            input_text = data.get("input", "")
            
            if connection_id in self.ssh_services:
                await self.ssh_services[connection_id].send_input(input_text)
            else:
                await ws_manager.send_json(connection_id, {
                    "type": "error",
                    "message": "No active SSH session"
                })
                
        except Exception as e:
            logger.error(f"Error handling SSH input: {e}")
            await ws_manager.send_json(connection_id, {
                "type": "error",
                "message": f"Failed to send input: {str(e)}"
            })
    
    async def handle_disconnect(self, connection_id: str):
        """Handle WebSocket disconnect"""
        if connection_id in self.ssh_services:
            await self.ssh_services[connection_id].disconnect()
            del self.ssh_services[connection_id]
            logger.info(f"Cleaned up SSH service for connection: {connection_id}")


# Create controller instance
stub_controller = StubWebSocketController()


# Register message handlers
@ws_handler.on_message("ssh_command")
async def handle_ssh_command(connection_id: str, data: dict):
    """Handle SSH command execution"""
    await stub_controller.handle_ssh_command(connection_id, data)


@ws_handler.on_message("ssh_input") 
async def handle_ssh_input(connection_id: str, data: dict):
    """Handle SSH input"""
    await stub_controller.handle_ssh_input(connection_id, data)


@ws_handler.on_connect("connect")
async def handle_connect(connection_id: str):
    """Handle WebSocket connection"""
    await ws_manager.send_json(connection_id, {
        "type": "welcome",
        "message": "Connected to Stub SSH WebSocket"
    })


@ws_handler.on_connect("disconnect")
async def handle_disconnect(connection_id: str):
    """Handle WebSocket disconnection"""
    await stub_controller.handle_disconnect(connection_id)


@router.websocket("/stub/{connection_id}")
async def stub_websocket_endpoint(websocket: WebSocket, connection_id: str):
    """Main WebSocket endpoint for stub functionality"""
    try:
        # Handle the WebSocket connection using our handler
        await ws_handler.handle_connection(websocket, connection_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        try:
            await websocket.close()
        except:
            pass