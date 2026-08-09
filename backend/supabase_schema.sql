-- ============================================================
-- BDNS Supabase Database Schema
-- Run this once in Supabase SQL Editor to create/repair all
-- tables the backend (app/) already expects.
-- ============================================================

-- ─── USERS ───────────────────────────────────────────────────
create table if not exists users (
    id                uuid primary key default gen_random_uuid(),
    full_name         text not null,
    email             text not null unique,
    password_hash     text not null,
    role              text not null default 'customer',   -- 'customer' | 'admin'
    country           text,
    contact_number    text,
    date_of_birth     date,
    status            text not null default 'active',      -- 'active' | 'suspended'
    created_at        timestamptz not null default now()
);

create index if not exists idx_users_email on users (email);
create index if not exists idx_users_role  on users (role);

-- ─── DOMAINS ─────────────────────────────────────────────────
create table if not exists domains (
    id                 uuid primary key default gen_random_uuid(),
    domain_name        text not null unique,
    ip_address         text,
    owner_public_key   text,
    status             text not null default 'active',      -- 'active' | 'frozen' | 'transferred'
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now()
);

create index if not exists idx_domains_owner  on domains (owner_public_key);
create index if not exists idx_domains_status on domains (status);

-- ─── LEDGER BLOCKS (blockchain persistence) ─────────────────
create table if not exists ledger_blocks (
    id                  uuid primary key default gen_random_uuid(),
    block_index         integer not null,
    block_hash          text not null unique,
    previous_hash       text,
    transaction_type    text,
    transaction_data    jsonb,
    validator           text,
    created_at          timestamptz not null default now()
);

create index if not exists idx_ledger_blocks_index on ledger_blocks (block_index);

-- ─── AUDIT LOGS ──────────────────────────────────────────────
create table if not exists audit_logs (
    id             uuid primary key default gen_random_uuid(),
    action_type    text not null,
    details        jsonb,
    created_at     timestamptz not null default now()
);

create index if not exists idx_audit_logs_action on audit_logs (action_type);
create index if not exists idx_audit_logs_created on audit_logs (created_at desc);

-- ─── PAYMENTS ────────────────────────────────────────────────
create table if not exists payments (
    id               uuid primary key default gen_random_uuid(),
    user_email       text,
    plan             text,
    amount           numeric,
    currency         text,
    paypal_order_id  text,
    status           text,                                  -- 'COMPLETED' | 'PENDING' | ...
    created_at       timestamptz not null default now()
);

create index if not exists idx_payments_status on payments (status);
create index if not exists idx_payments_email  on payments (user_email);

-- ============================================================
-- OPTIONAL: tables to support NEW admin features (only needed
-- if you add the corresponding feature — see chat for details)
-- ============================================================

-- Admin activity log: who did what admin action, when
create table if not exists admin_activity_log (
    id            uuid primary key default gen_random_uuid(),
    admin_id      uuid references users(id),
    action        text not null,
    target_type   text,          -- e.g. 'user', 'domain', 'payment'
    target_id     text,
    details       jsonb,
    created_at    timestamptz not null default now()
);

-- Support tickets raised by customers, handled by admins
create table if not exists support_tickets (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid references users(id),
    subject       text not null,
    message       text not null,
    status        text not null default 'open',  -- 'open' | 'in_progress' | 'closed'
    priority      text not null default 'normal',
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

-- System-wide notifications shown to admins/customers
create table if not exists notifications (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid references users(id),  -- null = broadcast to everyone
    title         text not null,
    message       text not null,
    is_read       boolean not null default false,
    created_at    timestamptz not null default now()
);
