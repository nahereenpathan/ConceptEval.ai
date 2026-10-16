"""
Import Comprehensive Catalog script
Imports validated problems from comprehensive_catalog.json into the active database
using the robust Content Import Pipeline.
"""

import asyncio
import json
import os
import sys

# Ensure apps/api and apps/execution-runner are on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.content_import.pipeline import import_problem_dataset
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.problem import ContentImportRequest


async def main():
    catalog_path = os.path.join(os.path.dirname(__file__), "..", "app", "content_import", "comprehensive_catalog.json")
    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    import_req = ContentImportRequest(**data)

    async with AsyncSessionLocal() as session:
        # Find teacher user
        stmt = select(User).where(User.email == "teacher@codeedu.org")
        teacher = (await session.execute(stmt)).scalar_one_or_none()
        if not teacher:
            stmt = select(User)
            teacher = (await session.execute(stmt)).scalars().first()
        if not teacher:
            print("ERROR: No teacher user found in database.")
            return

        report = await import_problem_dataset(session, import_req, teacher.id)
        print("=== COMPREHENSIVE CONTENT IMPORT REPORT ===")
        print(f"Audit ID           : {report.audit_id}")
        print(f"Source             : {report.source_name}")
        print(f"License            : {report.license_type}")
        print(f"Total Processed    : {report.total_processed}")
        print(f"Imported Count     : {report.imported_count}")
        print(f"Skipped Duplicates : {report.skipped_duplicates}")
        print(f"Imported Slugs     : {len(report.imported_slugs)}")
        print(f"Skipped Slugs      : {report.skipped_slugs}")
        if report.errors:
            print(f"Errors: {report.errors}")


if __name__ == "__main__":
    asyncio.run(main())
