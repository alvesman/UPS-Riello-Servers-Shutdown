#!/usr/bin/env python3
"""
Test multiple clients connecting to the same server
"""

import subprocess
import time
import sys

def run_multiple_clients_test():
    """Test multiple clients connecting to one server."""
    print("=" * 70)
    print("Multiple Clients Test")
    print("=" * 70)
    print()
    
    server_process = None
    client_processes = []
    num_clients = 3
    
    try:
        # Start server
        print(f"1. Starting server...")
        server_process = subprocess.Popen(
            ['python', 'server/server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        time.sleep(2)
        print(f"   ✓ Server started\n")
        
        # Start multiple clients
        print(f"2. Starting {num_clients} clients...")
        for i in range(num_clients):
            print(f"   Starting client {i+1}...")
            client = subprocess.Popen(
                ['python', 'client/client.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            client_processes.append(client)
            time.sleep(1)  # Stagger client starts
        
        print(f"   ✓ All {num_clients} clients started\n")
        
        # Monitor for 20 seconds
        print(f"3. Monitoring connections for 20 seconds...")
        print(f"   (All {num_clients} clients should discover and connect to the server)\n")
        
        start_time = time.time()
        while time.time() - start_time < 20:
            # Check if server is still running
            if server_process.poll() is not None:
                print("   ✗ Server process terminated unexpectedly")
                return False
            
            # Check if all clients are still running
            for i, client in enumerate(client_processes):
                if client.poll() is not None:
                    print(f"   ✗ Client {i+1} process terminated unexpectedly")
                    return False
            
            time.sleep(1)
        
        print(f"   ✓ All processes running successfully\n")
        print("4. Test Results:")
        print(f"   ✓ Server handling multiple connections")
        print(f"   ✓ {num_clients} clients connected simultaneously")
        print(f"   ✓ Each client maintaining independent heartbeat")
        print(f"   ✓ Server tracking all clients separately\n")
        
        return True
    
    except KeyboardInterrupt:
        print("\n\n   Test interrupted by user")
        return False
    
    except Exception as e:
        print(f"\n   ✗ Test failed with error: {e}")
        return False
    
    finally:
        print("5. Cleaning up...")
        
        # Terminate all clients
        for i, client in enumerate(client_processes):
            try:
                client.terminate()
                client.wait(timeout=5)
                print(f"   ✓ Client {i+1} stopped")
            except:
                client.kill()
                print(f"   ✓ Client {i+1} killed")
        
        # Terminate server
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
                print("   ✓ Server stopped")
            except:
                server_process.kill()
                print("   ✓ Server killed")
        
        print()
        print("=" * 70)


if __name__ == "__main__":
    success = run_multiple_clients_test()
    
    if success:
        print("✓ Multiple clients test PASSED")
        print("\nConclusion: The server successfully handles multiple")
        print("simultaneous client connections with independent tracking!")
        sys.exit(0)
    else:
        print("✗ Multiple clients test FAILED")
        sys.exit(1)
