# mcp_servers/delivery_tools.py
"""Delivery management tools with persistent storage."""

import json
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP()
DATA_FILE = "orders.json"

# --------------------------
# 数据加载 & 保存
# --------------------------
def load_orders():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_orders(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# 初始化加载
ORDERS = load_orders()

# --------------------------
# 工具函数定义
# --------------------------
@mcp.tool(description="Get delivery info by order ID")
def get_delivery_info(order_id: str = Field(description="Order ID")) -> dict:
    """Retrieve order details."""
    if order_id in ORDERS:
        return ORDERS[order_id]
    return {"error": f"Order ID {order_id} not found."}


@mcp.tool(description="Add a new delivery order")
def add_delivery_info(
    order_id: str = Field(description="Order ID"),
    delivery_method: str = Field(description="Delivery method"),
    delivery_address: str = Field(description="Delivery address"),
    delivery_phone: str = Field(description="Phone number"),
    estimated_delivery: str = Field(description="Estimated delivery (YYYY-MM-DD HH:MM:SS)"),
):
    """Add a new delivery record."""
    if order_id in ORDERS:
        return {"error": f"Order {order_id} already exists."}

    ORDERS[order_id] = {
        "order_id": order_id,
        "delivery_method": delivery_method,
        "delivery_address": delivery_address,
        "delivery_phone": delivery_phone,
        "delivery_time_slot": "09:00-18:00",
        "special_instructions": "",
        "delivery_fee": 10,
        "estimated_delivery": estimated_delivery,
        "delivery_status": "Pending",
        "created_at": datetime.now().isoformat()
    }

    save_orders(ORDERS)
    return {"message": f"Order {order_id} added successfully."}


@mcp.tool(description="Update delivery status")
def update_delivery_status(
    order_id: str = Field(description="Order ID"),
    new_status: str = Field(description="New delivery status (e.g., Delivered, In Transit)")
):
    """Update order status."""
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found."}
    ORDERS[order_id]["delivery_status"] = new_status
    ORDERS[order_id]["updated_at"] = datetime.now().isoformat()
    save_orders(ORDERS)
    return {"message": f"Order {order_id} updated to '{new_status}'."}


@mcp.tool(description="Delete an order")
def delete_order(order_id: str = Field(description="Order ID")):
    """Delete an order."""
    if order_id in ORDERS:
        del ORDERS[order_id]
        save_orders(ORDERS)
        return {"message": f"Order {order_id} deleted."}
    return {"error": f"Order {order_id} not found."}


@mcp.tool(description="List all orders")
def list_orders():
    """List all stored orders."""
    if not ORDERS:
        return {"message": "No orders found."}
    return {"orders": list(ORDERS.values())}


if __name__ == "__main__":
    mcp.run()
