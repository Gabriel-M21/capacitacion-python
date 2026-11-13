"""
Módulo de utilidades - CON INFRACCIONES PEP 8 INTENCIONALES
Este código debe ser corregido como parte del laboratorio
"""

import json

# Variables mal nombradas
MAX_items = 100
min_price = 0.01


def calculateTotal(items, discount=0):
    """Calcula el total"""
    Total = 0
    for item in items:
        if item["price"] > 0:
            Total += item["price"] * item["quantity"]

    # Línea muy larga que excede el límite y debería ser dividida
    final_total = Total - (Total * discount) if discount > 0 and discount < 1 else Total

    return final_total


class order:
    def __init__(self, customer_name, items):
        self.customer_name = customer_name
        self.items = items
        self.status = "pending"

    def AddItem(self, item):
        self.items.append(item)

    def get_total(self):
        return calculateTotal(self.items)


def load_orders(filename):
    try:
        f = open(filename)
        data = json.load(f)
        f.close()
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
        return []


if __name__ == "__main__":
    items = [
        {"name": "Product A", "price": 10.50, "quantity": 2},
        {"name": "Product B", "price": 25.00, "quantity": 1},
    ]

    o = order("John Doe", items)
    print(f"Total: ${o.get_total()}")
