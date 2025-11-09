# mcp_servers/inventory_tools.py
"""Dynamic inventory management tools (data loaded from JSON)."""

import json
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP()

# ========================
# 数据文件路径
# ========================
DATA_FILE = Path(__file__).parent / "inventory_data.json"

# ========================
# 读取库存数据
# ========================
def load_inventory():
    """从 JSON 文件加载库存数据"""
    if not DATA_FILE.exists():
        return {"NAME_TO_ID": {}, "INVENTORY": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_inventory(data):
    """将库存数据写回 JSON 文件"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 初始化库存
data = load_inventory()
NAME_TO_ID = data.get("NAME_TO_ID", {})
INVENTORY = data.get("INVENTORY", {})

# ========================
# 工具函数
# ========================
def resolve_product_id(pid_or_name: str):
    """支持用产品名或ID查询"""
    if pid_or_name in INVENTORY:
        return pid_or_name
    elif pid_or_name in NAME_TO_ID:
        return NAME_TO_ID[pid_or_name]
    else:
        return None


@mcp.tool(description="Query inventory info by product ID or name")
def check_inventory(product_id: str = Field(description="Product ID or name")) -> dict:
    pid = resolve_product_id(product_id)
    if not pid:
        return {"error": f"Product ID or name {product_id} does not exist."}

    inventory_info = INVENTORY[pid].copy()
    # 添加库存状态
    if inventory_info["available_stock"] == 0:
        inventory_info["stock_status"] = "Out of Stock"
    elif inventory_info["available_stock"] <= inventory_info["low_stock_threshold"]:
        inventory_info["stock_status"] = "Low Stock Warning"
    else:
        inventory_info["stock_status"] = "Sufficient Stock"

    return inventory_info


@mcp.tool(description="Check if enough stock exists for an order")
def check_stock_availability(
    product_id: str = Field(description="Product ID or name"),
    quantity: int = Field(description="Required quantity"),
) -> dict:
    pid = resolve_product_id(product_id)
    if not pid:
        return {"error": f"Product ID or name {product_id} does not exist."}

    inventory = INVENTORY[pid]
    available_stock = inventory["available_stock"]

    if quantity <= available_stock:
        return {
            "available": True,
            "requested_quantity": quantity,
            "available_stock": available_stock,
            "message": f"Sufficient stock to fulfill {quantity} units.",
        }
    else:
        return {
            "available": False,
            "requested_quantity": quantity,
            "available_stock": available_stock,
            "shortage": quantity - available_stock,
            "message": f"Insufficient stock: requested {quantity}, only {available_stock} available.",
        }


@mcp.tool(description="Release reserved stock after order cancellation")
def release_reserved_stock(
    product_id: str = Field(description="Product ID or name"),
    quantity: int = Field(description="Quantity to release"),
    order_id: str = Field(description="Order ID"),
) -> dict:
    pid = resolve_product_id(product_id)
    if not pid:
        return {"success": False, "message": "Product does not exist."}

    inventory = INVENTORY[pid]
    if quantity > inventory["reserved_stock"]:
        return {
            "success": False,
            "message": f"Insufficient reserved stock to release {quantity} units.",
        }

    inventory["reserved_stock"] -= quantity
    inventory["available_stock"] += quantity
    save_inventory({"NAME_TO_ID": NAME_TO_ID, "INVENTORY": INVENTORY})

    return {
        "success": True,
        "message": f"Released {quantity} units of {inventory['product_name']} for order {order_id}.",
        "available_stock": inventory["available_stock"],
    }


@mcp.tool(description="List products with low stock")
def get_low_stock_products() -> list:
    low_stock_items = []
    for pid, inv in INVENTORY.items():
        if inv["available_stock"] <= inv["low_stock_threshold"]:
            low_stock_items.append({
                "product_id": pid,
                "product_name": inv["product_name"],
                "available_stock": inv["available_stock"],
                "low_stock_threshold": inv["low_stock_threshold"],
                "urgency": "Critical" if inv["available_stock"] == 0 else "Warning",
            })

    return low_stock_items or [{"message": "No products with low stock."}]


@mcp.tool(description="Query stock in a specific warehouse")
def get_inventory_by_warehouse(
    warehouse: str = Field(description="Warehouse name"),
) -> dict:
    result = {}
    for pid, inv in INVENTORY.items():
        if warehouse in inv["warehouse_locations"]:
            result[pid] = {
                "product_name": inv["product_name"],
                "stock": inv["warehouse_locations"][warehouse],
                "total_available": inv["available_stock"],
            }
    return {
        "warehouse": warehouse,
        "products": result,
        "query_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@mcp.tool(description="Get automatic restock suggestions")
def get_restock_suggestions() -> list:
    suggestions = []
    for pid, inv in INVENTORY.items():
        if inv["available_stock"] <= inv["low_stock_threshold"]:
            need = inv["low_stock_threshold"] * 3 - inv["total_stock"]
            suggestions.append({
                "product_id": pid,
                "product_name": inv["product_name"],
                "current_stock": inv["available_stock"],
                "suggested_restock": max(need, 0),
                "supplier": inv["supplier"],
                "priority": "High" if inv["available_stock"] <= inv["low_stock_threshold"] // 2 else "Medium",
                "last_restock": inv["last_restock_date"],
            })
    return suggestions or [{"message": "Stock levels are sufficient."}]


if __name__ == "__main__":
    mcp.run()
