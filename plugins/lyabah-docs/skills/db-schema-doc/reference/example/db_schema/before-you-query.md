# lyabah-shop: before you query

Part of [the database map](../db_schema.md).

- **Times** are `timestamptz`, in UTC. An order's `day` is its date in
  `Europe/Kyiv`, so it can differ from `created_at::date`.
- **Money** is in cents, as `bigint`: `1250` is 12.50 UAH.
- **Deleted products stay.** A product someone deleted has `deleted_at` set;
  filter on `deleted_at IS NULL` to count products for sale.
- **Empty text is `''`**, not NULL, except where an article says otherwise.
- `customers.password_hash` is a secret: never select it.
