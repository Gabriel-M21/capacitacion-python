"""
Script de demostración - Módulo 4: Objetos y modelos de datos
Demuestra dataclasses, Pydantic y conversión entre capas
"""

from decimal import Decimal

from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus
from order_management.mappers.order_mapper import OrderMapper
from order_management.schemas.schemas import CustomerIn, OrderIn, OrderItemIn


def demo_value_objects() -> None:
    """Demuestra Value Objects inmutables."""
    print("=" * 70)
    print("1. VALUE OBJECTS (Inmutables)")
    print("=" * 70)

    # Money
    print("\na) Money:")
    price1 = Money.from_float(100.50)
    price2 = Money.from_float(50.25)
    print(f"   Price 1: {price1}")
    print(f"   Price 2: {price2}")
    print(f"   Suma: {price1 + price2}")
    print(f"   Resta: {price1 - price2}")
    print(f"   Multiplicar x2: {price1 * 2}")
    print(f"   Comparación: {price1} > {price2} = {price1 > price2}")

    # Email
    print("\nb) Email:")
    email = Email("juan.perez@example.com")
    print(f"   Email: {email}")
    print(f"   Dominio: {email.domain}")

    try:
        Email("correo-invalido")
    except ValueError as e:
        print(f"   ✓ Validación de email funciona: {e}")

    # OrderId
    print("\nc) OrderId:")
    order_id = OrderId.generate(1)
    print(f"   Generado: {order_id}")

    try:
        OrderId("INVALID-ID")
    except ValueError as e:
        print(f"   ✓ Validación de ID funciona: {e}")

    # OrderStatus
    print("\nd) OrderStatus con transiciones:")
    status = OrderStatus.PENDING
    print(f"   Estado inicial: {status.value}")
    print(f"   ¿Puede ir a CONFIRMED? {status.can_transition_to(OrderStatus.CONFIRMED)}")
    print(f"   ¿Puede ir a SHIPPED? {status.can_transition_to(OrderStatus.SHIPPED)}")


def demo_entities() -> None:
    """Demuestra entidades con comportamiento."""
    print("\n" + "=" * 70)
    print("2. ENTIDADES DE DOMINIO (dataclasses)")
    print("=" * 70)

    # OrderItem
    print("\na) OrderItem con cálculos derivados:")
    item1 = OrderItem(
        product_name="Laptop Dell XPS 15",
        quantity=1,
        unit_price=Money.from_float(1299.99),
    )
    item2 = OrderItem(
        product_name="Mouse Logitech",
        quantity=2,
        unit_price=Money.from_float(29.99),
    )
    print(f"   {item1}")
    print(f"   {item2}")

    # Customer
    print("\nb) Customer:")
    customer = Customer(
        name="Juan Pérez", email=Email("juan.perez@example.com"), phone="+52 55 1234 5678"
    )
    print(f"   {customer}")

    # Order
    print("\nc) Order con comportamiento:")
    order = Order(order_id=OrderId.generate(1), customer=customer, items=[item1, item2])
    print(f"   {order}")
    print(f"   Total: {order.total}")
    print(f"   Item count: {order.item_count}")
    print(f"   Product count: {order.product_count}")

    # Agregar item
    print("\nd) Agregar item a la orden:")
    item3 = OrderItem(
        product_name="Teclado mecánico",
        quantity=1,
        unit_price=Money.from_float(129.99),
    )
    order.add_item(item3)
    print(f"   Nuevo total: {order.total}")

    # Aplicar descuento
    print("\ne) Aplicar descuento del 10%:")
    discounted = order.apply_discount(Decimal("10"))
    print(f"   Total original: {order.total}")
    print(f"   Total con descuento: {discounted}")

    # Cambiar estado
    print("\nf) Cambiar estado de la orden:")
    print(f"   Estado actual: {order.status.value}")
    order.change_status(OrderStatus.CONFIRMED)
    print(f"   Nuevo estado: {order.status.value}")

    try:
        order.change_status(OrderStatus.DELIVERED)  # Transición inválida
    except ValueError as e:
        print(f"   ✓ Validación de transición funciona: {e}")

    # Comparación de órdenes
    print("\ng) Comparación de órdenes (por total):")
    order2 = Order(
        order_id=OrderId.generate(2),
        customer=customer,
        items=[
            OrderItem(
                product_name="Monitor 4K",
                quantity=1,
                unit_price=Money.from_float(599.00),
            )
        ],
    )
    print(f"   Order 1 total: {order.total}")
    print(f"   Order 2 total: {order2.total}")
    print(f"   Order 1 > Order 2: {order > order2}")

    # Igualdad y hash
    print("\nh) Igualdad y hash (basados en order_id):")
    orders_set = {order, order2, order}  # order duplicado
    print(f"   Set de órdenes (sin duplicados): {len(orders_set)} órdenes")


def demo_pydantic_schemas() -> None:
    """Demuestra schemas Pydantic para validación."""
    print("\n" + "=" * 70)
    print("3. SCHEMAS PYDANTIC (Validación y Serialización)")
    print("=" * 70)

    # Crear orden desde JSON (validación automática)
    print("\na) Validación de entrada con Pydantic:")
    order_data = {
        "customer": {
            "name": "María García",
            "email": "maria.garcia@example.com",
            "phone": "+34 91 123 4567",
        },
        "items": [
            {"product_name": "iPhone 15 Pro", "quantity": 1, "unit_price": 999.99},
            {"product_name": "AirPods Pro", "quantity": 1, "unit_price": 249.99},
        ],
        "notes": "Entrega urgente",
    }

    order_in = OrderIn(**order_data)
    print(f"   ✓ Orden validada: {order_in.customer.name}")
    print(f"   ✓ Items: {len(order_in.items)}")

    # Validación de errores
    print("\nb) Validación de errores:")
    try:
        OrderIn(
            customer=CustomerIn(
                name="", email="correo-invalido", phone=None  # Nombre vacío  # Email inválido
            ),
            items=[],  # Sin items
        )
    except Exception as e:
        print("   ✓ Validación detectó errores:")
        print(f"      {type(e).__name__}: {str(e)[:100]}...")

    # Serialización a JSON
    print("\nc) Serialización a JSON:")
    json_str = order_in.model_dump_json(indent=2)
    print(f"   JSON generado ({len(json_str)} caracteres):")
    print("   " + json_str[:150] + "...")


def demo_conversion() -> None:
    """Demuestra conversión entre Domain y API."""
    print("\n" + "=" * 70)
    print("4. CONVERSIÓN ENTRE DOMAIN Y API (Mappers)")
    print("=" * 70)

    # API → Domain
    print("\na) Conversión API → Domain:")
    order_in = OrderIn(
        customer=CustomerIn(name="Carlos López", email="carlos.lopez@example.com", phone=None),
        items=[
            OrderItemIn(product_name="MacBook Pro", quantity=1, unit_price=Decimal("2499.00")),
            OrderItemIn(product_name="Magic Mouse", quantity=1, unit_price=Decimal("79.00")),
        ],
        notes="Factura a nombre de empresa",
    )

    order_domain = OrderMapper.to_domain_order(order_in, OrderId.generate(100))
    print(f"   ✓ Convertido a Domain: {order_domain}")
    print(f"   ✓ Total calculado: {order_domain.total}")

    # Domain → API
    print("\nb) Conversión Domain → API:")
    order_out = OrderMapper.to_api_order(order_domain)
    print("   ✓ Convertido a API Schema:")
    print(f"      order_id: {order_out.order_id}")
    print(f"      customer: {order_out.customer.name}")
    print(f"      total: ${order_out.total}")
    print(f"      item_count: {order_out.item_count}")

    # Serializar a JSON
    print("\nc) Serialización final a JSON:")
    json_output = order_out.model_dump_json(indent=2)
    print("   " + json_output[:200] + "...")


def demo_dunder_methods() -> None:
    """Demuestra métodos especiales (dunder methods)."""
    print("\n" + "=" * 70)
    print("5. DUNDER METHODS (__str__, __repr__, __eq__, etc.)")
    print("=" * 70)

    customer = Customer(name="Test User", email=Email("test@example.com"))
    item = OrderItem(product_name="Test Product", quantity=1, unit_price=Money.from_float(100))
    order = Order(order_id=OrderId.generate(999), customer=customer, items=[item])

    print("\na) __str__ (representación legible):")
    print(f"   {str(order)}")

    print("\nb) __repr__ (representación para debugging):")
    print(f"   {repr(order)}")

    print("\nc) __eq__ (igualdad basada en order_id):")
    order2 = Order(order_id=OrderId.generate(999), customer=customer, items=[item])
    order3 = Order(order_id=OrderId.generate(888), customer=customer, items=[item])
    print(f"   order == order2 (mismo ID): {order == order2}")
    print(f"   order == order3 (diferente ID): {order == order3}")

    print("\nd) __hash__ (para usar en sets/dicts):")
    orders_dict = {order: "Primera", order2: "Segunda", order3: "Tercera"}
    print(f"   Dict de órdenes: {len(orders_dict)} entradas (order y order2 colisionan)")

    print("\ne) __lt__, __le__ (comparaciones para ordenamiento):")
    orders = [order3, order, order2]
    sorted_orders = sorted(orders)
    print("   Ordenadas por total:")
    for o in sorted_orders:
        print(f"      {o.order_id}: {o.total}")


def main() -> None:
    """Función principal."""
    print("\n" + "=" * 70)
    print("MÓDULO 4: OBJETOS Y MODELOS DE DATOS")
    print("Dataclasses, Pydantic y Value Objects")
    print("=" * 70)

    demo_value_objects()
    demo_entities()
    demo_pydantic_schemas()
    demo_conversion()
    demo_dunder_methods()

    print("\n" + "=" * 70)
    print("✓ DEMOSTRACIÓN COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
