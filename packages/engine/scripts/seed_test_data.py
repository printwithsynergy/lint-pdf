"""Seed test tenants and data into the production database.

Usage:
    python scripts/seed_test_data.py

Requires DATABASE_URL or GROUNDED_DATABASE_URL environment variable.
Outputs test-credentials.json with tenant IDs and raw API keys.
"""

from __future__ import annotations

import json
import os
import sys
import uuid

# Add the package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from grounded.api.auth import generate_api_key, hash_api_key
from grounded.api.models import ApiKey, Tenant, TenantPlan

DATABASE_URL = os.environ.get("DATABASE_URL", os.environ.get("GROUNDED_DATABASE_URL", ""))
if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL or GROUNDED_DATABASE_URL")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

PLAN_CONFIG = {
    TenantPlan.FREE: {"rate_limit_daily": 50, "max_file_size_mb": 25},
    TenantPlan.STARTER: {"rate_limit_daily": 500, "max_file_size_mb": 250},
    TenantPlan.GROWTH: {"rate_limit_daily": 5000, "max_file_size_mb": 500},
    TenantPlan.SCALE: {"rate_limit_daily": 25000, "max_file_size_mb": 1024},
    TenantPlan.ENTERPRISE: {"rate_limit_daily": 100000, "max_file_size_mb": 2048},
}

credentials = {"admin_api_key": os.environ.get("GROUNDED_ADMIN_API_KEY", ""), "tenants": {}}

try:
    for plan, limits in PLAN_CONFIG.items():
        name = f"Test {plan.value.capitalize()} Tenant"

        # Check if already exists
        existing = db.query(Tenant).filter(Tenant.name == name).first()
        if existing:
            print(f"  Tenant '{name}' already exists (id={existing.id}), skipping.")
            # Generate a fresh key for it
            raw_key = generate_api_key()
            key_hash = hash_api_key(raw_key)
            existing.api_key_hash = key_hash
            db.commit()
            credentials["tenants"][plan.value] = {
                "id": str(existing.id),
                "name": name,
                "api_key": raw_key,
            }
            continue

        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        tenant_id = uuid.uuid4()

        tenant = Tenant(
            id=tenant_id,
            name=name,
            api_key_hash=key_hash,
            plan=plan,
            rate_limit_daily=limits["rate_limit_daily"],
            max_file_size_mb=limits["max_file_size_mb"],
            contact_email=f"test-{plan.value}@lintpdf.com",
            is_active=True,
        )
        db.add(tenant)

        # Also add to api_keys table
        api_key = ApiKey(
            tenant_id=tenant_id,
            key_hash=key_hash,
            label="seed-key",
            key_prefix=raw_key[:12],
        )
        db.add(api_key)
        db.commit()

        credentials["tenants"][plan.value] = {
            "id": str(tenant_id),
            "name": name,
            "api_key": raw_key,
        }
        print(f"  Created tenant '{name}' (id={tenant_id}, plan={plan.value})")

    db.commit()

    # Write credentials file
    out_path = os.path.join(os.path.dirname(__file__), "..", "test-credentials.json")
    with open(out_path, "w") as f:
        json.dump(credentials, f, indent=2)
    print(f"\nCredentials written to {out_path}")
    print(json.dumps(credentials, indent=2))

except Exception:
    db.rollback()
    raise
finally:
    db.close()
