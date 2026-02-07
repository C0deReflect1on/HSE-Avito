CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    is_verified_seller BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id BIGINT PRIMARY KEY,
    seller_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL,
    images_qty INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS items_seller_id_idx ON items (seller_id);
