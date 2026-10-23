import argparse
import asyncio
from scripts.verify_catalog import verify_entities


def parse_args():
    parser = argparse.ArgumentParser(description="Mark career(s) as verified (alias to verify_catalog)")
    parser.add_argument("--reviewer", required=True, help="Reviewer name or identifier")
    parser.add_argument("--code", help="Career code to verify")
    parser.add_argument("--id", help="Career UUID to verify")
    parser.add_argument("--all", action="store_true", help="Verify all draft careers")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        verify_entities(
            entity_type="career",
            reviewer=args.reviewer,
            code=args.code,
            entity_id=args.id,
            verify_all=args.all,
        )
    )
