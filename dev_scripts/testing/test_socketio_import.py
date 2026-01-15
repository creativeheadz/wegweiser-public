#!/usr/bin/env python3
"""
Test script to verify correct socketio import
"""

import sys

def test_socketio_import():
    """Test different ways to import socketio"""
    
    print("Testing socketio imports...")
    
    # Method 1: Direct import
    try:
        import socketio
        print("✅ Direct import 'socketio' successful")
        print(f"   Module: {socketio}")
        print(f"   File: {socketio.__file__}")
        print(f"   Version: {getattr(socketio, '__version__', 'Unknown')}")
        
        # Test AsyncClient
        try:
            client = socketio.AsyncClient()
            print("✅ AsyncClient creation successful")
            return True
        except Exception as e:
            print(f"❌ AsyncClient creation failed: {e}")
            
    except ImportError as e:
        print(f"❌ Direct import failed: {e}")
    
    # Method 2: From python_socketio
    try:
        from python_socketio import socketio as sio
        print("✅ Import from python_socketio successful")
        print(f"   Module: {sio}")
        return True
    except ImportError as e:
        print(f"❌ Import from python_socketio failed: {e}")
    
    # Method 3: Check installed packages
    try:
        import pkg_resources
        installed_packages = [d.project_name for d in pkg_resources.working_set]
        socketio_packages = [p for p in installed_packages if 'socketio' in p.lower()]
        print(f"📦 Installed socketio-related packages: {socketio_packages}")
    except Exception as e:
        print(f"⚠️  Could not check installed packages: {e}")
    
    return False

if __name__ == "__main__":
    success = test_socketio_import()
    if success:
        print("\n🎉 SocketIO import test successful!")
        sys.exit(0)
    else:
        print("\n❌ SocketIO import test failed!")
        print("\n💡 Try installing with: pip install python-socketio[asyncio_client]")
        sys.exit(1)
