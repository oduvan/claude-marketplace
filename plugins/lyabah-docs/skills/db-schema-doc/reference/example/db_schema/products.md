# lyabah-shop: products

Part of [the database map](../db_schema.md); read [Before you query](before-you-query.md) first.

**`products`**: one row per thing for sale. `slug` is its URL on the site and
never changes after the first sale. `price` is the current price; what a
customer paid is in `order_items.price`.

**`product_images`**: the images of a product, in the order the page shows
them (`position`, from 0).

Products are changed through [the products article](../api/products.yaml.md).

## Useful questions

```sql
-- What is for sale, cheapest first (what the API's product list showed).
SELECT slug, title, price / 100.0 AS uah FROM products
WHERE deleted_at IS NULL ORDER BY price;

-- Products for sale that nobody bought in the last 90 days.
SELECT p.slug FROM products p
WHERE p.deleted_at IS NULL AND NOT EXISTS (
  SELECT 1 FROM order_items i JOIN orders o ON o.id = i.order_id
  WHERE i.product_id = p.id AND o.created_at > now() - interval '90 days');
```
