-- ============================================================
-- Nimbus Analytics — SaaS demo database schema
-- ============================================================

DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS churn_events;
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS usage_events;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS plans;
DROP TABLE IF EXISTS customers;

-- Customer accounts (B2B — each customer is a company)
CREATE TABLE customers (
    customer_id      INTEGER PRIMARY KEY,
    company_name     VARCHAR NOT NULL,
    industry         VARCHAR NOT NULL,
    employee_count   INTEGER NOT NULL,
    country          VARCHAR NOT NULL,
    region           VARCHAR NOT NULL,           -- NAM, EMEA, APAC, LATAM
    signup_date      DATE NOT NULL,
    acquisition_channel VARCHAR NOT NULL         -- organic, paid_search, content, referral, outbound
);

-- Plan tiers offered
CREATE TABLE plans (
    plan_id          INTEGER PRIMARY KEY,
    plan_name        VARCHAR NOT NULL,
    tier             VARCHAR NOT NULL,           -- free, starter, pro, enterprise
    monthly_price    DECIMAL(10, 2) NOT NULL,
    seat_limit       INTEGER
);

-- Subscriptions (each row = a plan period; customers can upgrade/downgrade)
CREATE TABLE subscriptions (
    subscription_id  INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL,
    plan_id          INTEGER NOT NULL,
    start_date       DATE NOT NULL,
    end_date         DATE,                       -- NULL if still active
    seats            INTEGER NOT NULL,
    mrr              DECIMAL(10, 2) NOT NULL,    -- monthly recurring revenue for this subscription period
    status           VARCHAR NOT NULL,           -- active, churned, upgraded, downgraded
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (plan_id) REFERENCES plans(plan_id)
);

-- Product usage events (daily aggregates per customer)
CREATE TABLE usage_events (
    event_id         INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL,
    event_date       DATE NOT NULL,
    event_type       VARCHAR NOT NULL,           -- login, dashboard_view, report_export, api_call, integration_used
    event_count      INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Support tickets
CREATE TABLE support_tickets (
    ticket_id        INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL,
    created_date     DATE NOT NULL,
    resolved_date    DATE,
    priority         VARCHAR NOT NULL,           -- low, medium, high, critical
    category         VARCHAR NOT NULL,           -- billing, bug, feature_request, onboarding, integration, other
    csat_score       INTEGER,                    -- 1-5, NULL if not resolved or no response
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Churn events
CREATE TABLE churn_events (
    churn_id         INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL,
    churn_date       DATE NOT NULL,
    reason_category  VARCHAR NOT NULL,           -- price, missing_features, competitor, low_usage, bad_support, business_closure, other
    mrr_lost         DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Invoices (monthly billing)
CREATE TABLE invoices (
    invoice_id       INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL,
    subscription_id  INTEGER NOT NULL,
    invoice_date     DATE NOT NULL,
    amount           DECIMAL(10, 2) NOT NULL,
    status           VARCHAR NOT NULL,           -- paid, pending, failed, refunded
    paid_date        DATE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id)
);

-- Helpful indexes for the agent's queries
CREATE INDEX idx_customers_region ON customers(region);
CREATE INDEX idx_customers_signup ON customers(signup_date);
CREATE INDEX idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX idx_subscriptions_dates ON subscriptions(start_date, end_date);
CREATE INDEX idx_usage_customer_date ON usage_events(customer_id, event_date);
CREATE INDEX idx_tickets_customer ON support_tickets(customer_id);
CREATE INDEX idx_tickets_date ON support_tickets(created_date);
CREATE INDEX idx_churn_date ON churn_events(churn_date);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
