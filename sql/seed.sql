CREATE TABLE IF NOT EXISTS analytics.customers (
 customer_id integer PRIMARY KEY, customer_label text NOT NULL,
 region text NOT NULL, segment text NOT NULL, signup_date date NOT NULL);
CREATE TABLE IF NOT EXISTS analytics.products (
 product_id integer PRIMARY KEY, product_label text NOT NULL,
 category text NOT NULL, price numeric(10,2) NOT NULL CHECK(price>0));
CREATE TABLE IF NOT EXISTS analytics.orders (
 order_id integer PRIMARY KEY, customer_id integer NOT NULL REFERENCES analytics.customers,
 order_date date NOT NULL, status text NOT NULL CHECK(status IN ('completed','pending','cancelled')));
CREATE TABLE IF NOT EXISTS analytics.order_items (
 order_id integer NOT NULL REFERENCES analytics.orders,
 product_id integer NOT NULL REFERENCES analytics.products,
 quantity integer NOT NULL CHECK(quantity>0), unit_price numeric(10,2) NOT NULL,
 PRIMARY KEY(order_id,product_id));
INSERT INTO analytics.customers
SELECT i, 'Customer-'||lpad(i::text,3,'0'),
 (ARRAY['North','South','East','West'])[1+(i%4)],
 (ARRAY['Consumer','Business','Enterprise'])[1+(i%3)], DATE '2023-01-01'+i*7
FROM generate_series(1,48) i ON CONFLICT DO NOTHING;
INSERT INTO analytics.products
SELECT i, 'Product-'||lpad(i::text,2,'0'),
 (ARRAY['Electronics','Office','Home'])[1+(i%3)], (15+i*7.25)::numeric(10,2)
FROM generate_series(1,12) i ON CONFLICT DO NOTHING;
INSERT INTO analytics.orders
SELECT i, 1+(i%48), DATE '2024-01-01'+((i*7)%730),
 (ARRAY['completed','completed','completed','pending','cancelled'])[1+(i%5)]
FROM generate_series(1,360) i ON CONFLICT DO NOTHING;
INSERT INTO analytics.order_items
SELECT o.order_id, p.product_id, 1+((o.order_id+j)%5), p.price
FROM analytics.orders o CROSS JOIN generate_series(0,1) j
JOIN analytics.products p ON p.product_id=1+((o.order_id+j*5)%12)
ON CONFLICT DO NOTHING;
