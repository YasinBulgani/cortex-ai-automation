#!/usr/bin/env python3
"""Seed script for populating Neurex database with factory-generated test data.

Usage:
    python backend/scripts/seed_factories.py  # Default: 5 projects, 10 users
    python backend/scripts/seed_factories.py --projects 10 --users 20
    python backend/scripts/seed_factories.py --cleanup  # Clear all seeded data

This script uses factory_boy factories to generate realistic test data for:
  - Users (with roles and teams)
  - Organizations & Teams
  - Test Projects with suites, cases, and plans
  - Test Runs with results
  - Defects linked to test results

WARNING: Use only in development/staging. Do NOT run against production.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    from tests.factories import (
        UserFactory,
        OrganizationFactory,
        TeamFactory,
        TestManagementProjectFactory,
        TestCaseFactory,
        TestRunFactory,
        TestResultFactory,
        DefectFactory,
        AutomationRunFactory,
        create_complete_project_hierarchy,
        create_test_run_with_results,
    )
except ImportError as e:
    print(f"ERROR: Failed to import factories. Did you run `pip install factory-boy`?\n{e}")
    sys.exit(1)

from app.config import settings

logger = logging.getLogger(__name__)


def get_db_engine():
    """Create SQLAlchemy engine from settings."""
    db_url = (
        f"postgresql+psycopg2://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}"
        f"@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"
    )
    return create_engine(db_url, echo=False)


def seed_users(session, count: int = 10):
    """Create test users with various roles."""
    logger.info(f"Creating {count} users...")
    users = []
    for i in range(count):
        user = UserFactory.create(
            session=session,
            email=f"tester{i}@neurex.local",
            full_name=f"Test User {i}",
            department=["QA", "Dev", "DevOps", "Product"][i % 4],
        )
        users.append(user)
        logger.debug(f"  Created user: {user.email}")
    return users


def seed_organizations_and_teams(session, org_count: int = 2, teams_per_org: int = 3):
    """Create organizations and teams."""
    logger.info(f"Creating {org_count} organizations...")
    orgs = []
    for i in range(org_count):
        org = OrganizationFactory.create(
            session=session,
            name=f"Test Org {i}",
            slug=f"test-org-{i}",
        )
        for j in range(teams_per_org):
            team = TeamFactory.create(
                session=session,
                organization_id=org.id,
                name=f"Team {j}",
            )
            logger.debug(f"  Created team: {team.name}")
        orgs.append(org)
    return orgs


def seed_projects(session, users: list, count: int = 5):
    """Create test management projects with full hierarchy."""
    logger.info(f"Creating {count} projects...")
    projects = []
    for i in range(count):
        hierarchy = create_complete_project_hierarchy(
            session=session,
            name=f"Test Project {i}",
            key=f"PROJ{i:03d}",
            description=f"Test project {i} for QA automation",
            created_by=users[i % len(users)].id if users else None,
        )
        projects.append(hierarchy["project"])
        logger.info(f"  Project: {len(hierarchy['cases'])} test cases")
    return projects


def seed_test_runs_and_results(session, projects: list, users: list, runs_per_project: int = 3):
    """Create test runs with results for each project."""
    logger.info(f"Creating test runs...")
    runs = []
    for project in projects:
        for i in range(runs_per_project):
            run_data = create_test_run_with_results(
                session=session,
                project_id=project.id,
                name=f"Run {i+1}",
                assigned_tester_id=users[i % len(users)].id if users else None,
                num_cases=5,
            )
            runs.append(run_data["run"])
    return runs


def seed_defects(session, projects: list, users: list, defects_per_project: int = 3):
    """Create defects linked to test results."""
    logger.info(f"Creating defects...")
    defects = []
    for project in projects:
        for i in range(defects_per_project):
            defect = DefectFactory.create(
                session=session,
                project_id=project.id,
                title=f"Defect {i+1}",
                severity=["low", "medium", "high"][i % 3],
                assigned_to_id=users[i % len(users)].id if users else None,
            )
            defects.append(defect)
    return defects


def cleanup_seeded_data(session):
    """Delete all seeded data."""
    logger.warning("Cleaning up seeded data...")
    tables_to_clear = [
        "test_management_results",
        "test_management_runs",
        "test_management_defects",
        "sd_automation_runs",
        "test_management_cases",
        "test_management_folders",
        "test_management_suites",
        "test_management_projects",
        "sd_team_members",
        "sd_teams",
        "sd_organizations",
        "sd_users",
    ]
    for table in tables_to_clear:
        try:
            session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            session.commit()
            logger.info(f"  Cleared {table}")
        except Exception as e:
            logger.warning(f"  Failed to clear {table}: {e}")
    logger.info("Cleanup complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Seed Neurex database with factory-generated test data"
    )
    parser.add_argument(
        "--projects",
        type=int,
        default=5,
        help="Number of test projects to create (default: 5)",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Number of users to create (default: 10)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete all seeded data and exit",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        engine = get_db_engine()
        Session = sessionmaker(bind=engine)
        session = Session()

        if args.cleanup:
            cleanup_seeded_data(session)
            return 0

        logger.info("=" * 60)
        logger.info("Neurex Database Seeder")
        logger.info("=" * 60)

        users = seed_users(session, count=args.users)
        orgs = seed_organizations_and_teams(session)
        projects = seed_projects(session, users, count=args.projects)
        runs = seed_test_runs_and_results(session, projects, users)
        defects = seed_defects(session, projects, users)

        logger.info("=" * 60)
        logger.info("Seeding Complete!")
        logger.info(f"  Users: {len(users)}")
        logger.info(f"  Organizations: {len(orgs)}")
        logger.info(f"  Projects: {len(projects)}")
        logger.info(f"  Test Runs: {len(runs)}")
        logger.info(f"  Defects: {len(defects)}")
        logger.info("=" * 60)

        session.close()
        return 0

    except Exception as e:
        logger.error(f"Seeding failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
