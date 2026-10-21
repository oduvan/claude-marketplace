# lyabah-shop: database schema

The Postgres database `lyabah_shop` on the shared server, behind shop.lyabah.com.
The migrations in `internal/db/migrations/` create it; this page explains what
the data means.

## Before you write a query

- **Times** are `timestamptz`, in UTC. An order's `day` is its date in
  `Europe/Kyiv`, so it can differ from `created_at::date`.
- **Money** is in cents, as `bigint`: `1250` is 12.50 UAH.
- **Deleted products stay.** A product someone deleted has `deleted_at` set;
  filter on `deleted_at IS NULL` to count products for sale. Orders keep
  pointing at deleted products.
- **Empty text is `''`**, not NULL, except where a column says otherwise.
- `customers.password_hash` is a secret: never select it.
- **Changing data** goes through the shop's API, never SQL:
  `find_api_endpoints` with the column, e.g. `lyabah_shop.orders.status`,
  finds the call to prepare.

## Products

**`products`**: one row per thing for sale. `slug` is its URL on the site and
never changes after the first sale. `price` is the current price; what a
customer paid is in `order_items.price`.

**`product_images`**: the images of a product, in the order the page shows
them (`position`, from 0).

## Orders

**`orders`**: one row per checkout.

- `status`: `new` (paid, not packed) → `sent` → `delivered`; or `new` →
  `cancelled`. Only `cancelled` orders are refunded.
- `total` is the sum of its items when the order was placed; later price
  changes do not touch it.

**`order_items`**: one row per product in an order, with the `quantity` and
the `price` of one item at the time.

## Useful questions

```sql
-- Revenue by day, in shop time, without cancelled orders.
SELECT day, sum(total) / 100.0 AS uah FROM orders
WHERE status <> 'cancelled' GROUP BY day ORDER BY day DESC LIMIT 30;

-- Products for sale that nobody bought in the last 90 days.
SELECT p.slug FROM products p
WHERE p.deleted_at IS NULL AND NOT EXISTS (
  SELECT 1 FROM order_items i JOIN orders o ON o.id = i.order_id
  WHERE i.product_id = p.id AND o.created_at > now() - interval '90 days');
```
