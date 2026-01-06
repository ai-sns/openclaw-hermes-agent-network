"""
gRPC Module for A2A Protocol

Provides gRPC interface for the A2A protocol with streaming support.
Compatible with Google A2A Protocol v0.3.

Usage:
    # Generate gRPC code from proto file:
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. a2a.proto

    # Start gRPC server:
    from agent_platform.protocols.a2a.grpc import start_grpc_server
    await start_grpc_server(port=50051)

    # Use client:
    from agent_platform.protocols.a2a.grpc import A2AGrpcClient
    async with A2AGrpcClient("localhost:50051") as client:
        response = await client.send_task(...)
"""

import os
import sys

# Try to import generated code (if available)
try:
    from . import a2a_pb2
    from . import a2a_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    a2a_pb2 = None
    a2a_pb2_grpc = None

# Import service and client
from .service import (
    A2AGrpcService,
    start_grpc_server,
    stop_grpc_server,
    get_grpc_server,
)
from .client import A2AGrpcClient

__all__ = [
    # Generated code
    "a2a_pb2",
    "a2a_pb2_grpc",
    "GRPC_AVAILABLE",
    # Service
    "A2AGrpcService",
    "start_grpc_server",
    "stop_grpc_server",
    "get_grpc_server",
    # Client
    "A2AGrpcClient",
]


def generate_grpc_code():
    """
    Generate Python code from proto file.

    Requires grpcio-tools package.
    """
    import subprocess

    proto_dir = os.path.dirname(os.path.abspath(__file__))
    proto_file = os.path.join(proto_dir, "a2a.proto")

    if not os.path.exists(proto_file):
        raise FileNotFoundError(f"Proto file not found: {proto_file}")

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{proto_dir}",
        f"--python_out={proto_dir}",
        f"--grpc_python_out={proto_dir}",
        proto_file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to generate gRPC code: {result.stderr}")

    print(f"Generated gRPC code in {proto_dir}")
    return True
