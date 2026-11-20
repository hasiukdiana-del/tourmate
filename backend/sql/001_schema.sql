-- TourMate: фізична модель БД (PostgreSQL 16)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS cube;
CREATE EXTENSION IF NOT EXISTS earthdistance;

CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(254) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          VARCHAR(16) NOT NULL DEFAULT 'tourist'
                  CHECK (role IN ('tourist', 'author', 'admin')),
    locale        CHAR(2) NOT NULL DEFAULT 'uk',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cities (
    city_id      SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    country_code CHAR(2) NOT NULL,
    UNIQUE (name, country_code)
);

CREATE TABLE categories (
    category_id SMALLSERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    name   VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE places (
    place_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id     INT NOT NULL REFERENCES cities ON DELETE RESTRICT,
    category_id SMALLINT NOT NULL REFERENCES categories ON DELETE RESTRICT,
    author_id   UUID REFERENCES users ON DELETE SET NULL,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    lat         NUMERIC(9,6) NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lon         NUMERIC(9,6) NOT NULL CHECK (lon BETWEEN -180 AND 180),
    status      VARCHAR(16) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX places_geo_idx  ON places USING gist (ll_to_earth(lat::float8, lon::float8));
CREATE INDEX places_city_idx ON places (city_id, status);

CREATE TABLE opening_hours (
    place_id UUID NOT NULL REFERENCES places ON DELETE CASCADE,
    weekday  SMALLINT NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    opens    TIME NOT NULL,
    closes   TIME NOT NULL CHECK (closes > opens),
    PRIMARY KEY (place_id, weekday)
);

CREATE TABLE place_tags (
    place_id UUID NOT NULL REFERENCES places ON DELETE CASCADE,
    tag_id   INT  NOT NULL REFERENCES tags ON DELETE CASCADE,
    PRIMARY KEY (place_id, tag_id)
);

CREATE TABLE content (
    content_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id   UUID NOT NULL REFERENCES places ON DELETE CASCADE,
    type       VARCHAR(16) NOT NULL CHECK (type IN ('article', 'photo', 'audio')),
    language   CHAR(2) NOT NULL,
    title      VARCHAR(200) NOT NULL,
    body       TEXT,
    media_url  TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_interests (
    user_id UUID NOT NULL REFERENCES users ON DELETE CASCADE,
    tag_id  INT  NOT NULL REFERENCES tags ON DELETE CASCADE,
    weight  REAL NOT NULL DEFAULT 1.0 CHECK (weight BETWEEN 0 AND 1),
    PRIMARY KEY (user_id, tag_id)
);

CREATE TABLE interactions (
    interaction_id BIGSERIAL PRIMARY KEY,
    user_id    UUID NOT NULL REFERENCES users ON DELETE CASCADE,
    place_id   UUID NOT NULL REFERENCES places ON DELETE CASCADE,
    type       VARCHAR(8) NOT NULL CHECK (type IN ('view', 'rate', 'save')),
    rating     SMALLINT CHECK (rating BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((type = 'rate') = (rating IS NOT NULL))
);
CREATE INDEX interactions_user_idx ON interactions (user_id, created_at DESC);

CREATE TABLE routes (
    route_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users ON DELETE CASCADE,
    start_lat    NUMERIC(9,6) NOT NULL,
    start_lon    NUMERIC(9,6) NOT NULL,
    duration_min INT NOT NULL CHECK (duration_min > 0),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE route_stops (
    route_id UUID NOT NULL REFERENCES routes ON DELETE CASCADE,
    position SMALLINT NOT NULL CHECK (position > 0),
    place_id UUID NOT NULL REFERENCES places ON DELETE CASCADE,
    PRIMARY KEY (route_id, position),
    UNIQUE (route_id, place_id)
);
