-- Міграція безпеки облікових записів (Лабораторні 8, 9, 10).
-- Схему Лабораторної 5 не змінено; поля додано окремо.
ALTER TABLE users
    ADD COLUMN failed_logins SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN locked_until  TIMESTAMPTZ,
    ADD COLUMN token_version INT NOT NULL DEFAULT 0;

-- Журнал подій автентифікації: вхід, помилка, блокування, вихід.
CREATE TABLE auth_events (
    event_id   BIGSERIAL PRIMARY KEY,
    user_id    UUID REFERENCES users ON DELETE SET NULL,
    email      VARCHAR(254),
    event      VARCHAR(32) NOT NULL,
    ip         VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX auth_events_user_idx ON auth_events (user_id, created_at DESC);
