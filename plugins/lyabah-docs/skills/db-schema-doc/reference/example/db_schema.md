# lyabah-shop: database

shop.lyabah.com sells prints and books online, and keeps the orders and the
customers who placed them. Its database is `lyabah_shop`.

## Articles

- [Before you query](db_schema/before-you-query.md): rules for every query - times, money, deleted rows, secrets.
- [Products](db_schema/products.md): `products`, `product_images` - what is for sale, at what price, which products nobody buys.
- [Orders](db_schema/orders.md): `orders`, `order_items` - what was sold, revenue by day, an order's status.

Data is changed through the shop's API, never with SQL: `find_api_endpoints`
with the column, e.g. `lyabah_shop.orders.status`.
