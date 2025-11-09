#!/usr/bin/env python3
"""
Server Control Script - Send messages to connected clients
"""

import socket
import json
import sys


def send_command_to_server(command: dict, server_host='localhost', server_port=5226):
    """Send a command to the server for broadcasting to clients."""
    # Note: This is a simplified version. In production, you would implement
    # a proper control protocol. For now, this serves as an example.
    print(f"Command format example: {json.dumps(command, indent=2)}")
    print("\nTo send messages to clients, you can extend the server with")
    print("a control interface (e.g., REST API, CLI commands, etc.)")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("UPS Server Control")
        print("=" * 50)
        print("\nUsage examples:")
        print("  1. Shutdown command:")
        print("     python server_control.py shutdown 'Power failure detected'")
        print()
        print("  2. Custom command:")
        print("     python server_control.py command 'restart_service'")
        print()
        print("\nNote: In Phase 1, message sending is demonstrated through")
        print("the server's internal methods. Future phases can add a")
        print("control interface for external commands.")
        return
    
    command_type = sys.argv[1]
    
    if command_type == 'shutdown':
        reason = sys.argv[2] if len(sys.argv) > 2 else 'Manual shutdown'
        command = {
            'type': 'shutdown',
            'reason': reason
        }
        send_command_to_server(command)
    
    elif command_type == 'command':
        cmd = sys.argv[2] if len(sys.argv) > 2 else 'test'
        command = {
            'type': 'command',
            'command': cmd
        }
        send_command_to_server(command)
    
    else:
        print(f"Unknown command type: {command_type}")
        print("Supported types: shutdown, command")


if __name__ == "__main__":
    main()
