#!/usr/bin/env python3
"""
Test script for Stub WebSocket functionality
Usage: python test/test_stub_websocket.py
"""

import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed


async def test_stub_websocket():
    """Test the stub WebSocket endpoint"""
    
    # WebSocket URL
    ws_url = "ws://localhost:8000/ws/v1/stub/test-connection-123"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for welcome message
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 Welcome: {welcome_data}")
            
            # Test SSH command execution
            ssh_command = {
                "type": "ssh_command",
                "server": "wdexgm1p",  # Change this to match your server
                "command": "echo 'Hello from SSH test'",
                "stop_phrase": "SSH test"
            }
            
            print(f"📤 Sending SSH command: {ssh_command}")
            await websocket.send(json.dumps(ssh_command))
            
            # Listen for responses
            response_count = 0
            max_responses = 20  # Limit to prevent infinite loop
            
            while response_count < max_responses:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    response_count += 1
                    
                    print(f"📨 Response {response_count}: {data}")
                    
                    # Check if execution completed
                    if data.get("type") == "complete":
                        print("✅ SSH command execution completed")
                        break
                    elif data.get("type") == "error":
                        print(f"❌ Error: {data.get('message')}")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
                except ConnectionClosed:
                    print("🔌 Connection closed")
                    break
            
            print("🏁 Test completed")
            
    except ConnectionRefusedError:
        print("❌ Connection refused. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Test failed: {e}")


async def test_ssh_input():
    """Test SSH input functionality"""
    
    ws_url = "ws://localhost:8000/ws/v1/stub/test-input-456"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected for input test")
            
            # Wait for welcome message
            await websocket.recv()
            
            # Test sending input without active session
            input_command = {
                "type": "ssh_input",
                "input": "ls -la\n"
            }
            
            print(f"📤 Sending SSH input: {input_command}")
            await websocket.send(json.dumps(input_command))
            
            # Should receive error since no active session
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Expected error response: {data}")
            
            if data.get("type") == "error" and "No active SSH session" in data.get("message", ""):
                print("✅ Input test passed - correctly handled no session case")
            else:
                print("❌ Input test failed - unexpected response")
                
    except Exception as e:
        print(f"❌ Input test failed: {e}")


async def main():
    """Run all tests"""
    print("🚀 Starting Stub WebSocket Tests")
    print("=" * 50)
    
    print("\n📋 Test 1: SSH Command Execution")
    await test_stub_websocket()
    
    print("\n📋 Test 2: SSH Input Handling")
    await test_ssh_input()
    
    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())