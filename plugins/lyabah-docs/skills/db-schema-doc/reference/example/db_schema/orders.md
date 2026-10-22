# lyabah-shop: orders

Part of [the database map](../db_schema.md); read [Before you query](before-you-query.md) first.

**`orders`**: one row per checkout.

- `status`: `new` (paid, not packed) → `sent` → `delivered`; or `new` →
  `cancelled`. Only `cancelled` orders are refunded.
- `total` is the sum of its items when the order was placed; later price
  changes do not touch it.

**`order_items`**: one row per product in an order, with the `quantity` and
the `price` of one item at the time.

An order's status is changed through [the orders article](../api/orders.yaml.md);
orders themselves are created only by the checkout.

## Useful questions

```sql
-- Revenue by day, in shop time, without cancelled orders.
SELECT day, sum(total) / 100.0 AS uah FROM orders
WHERE status <> 'cancelled' GROUP BY day ORDER BY day DESC LIMIT 30;

-- One order with its items.
SELECT o.id, o.status, o.total / 100.0 AS uah, p.slug, i.quantity, i.price / 100.0 AS item_uah
FROM orders o JOIN order_items i ON i.order_id = o.id JOIN products p ON p.id = i.product_id
WHERE o.id = 1042;
```
