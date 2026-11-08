"""Entry point for a scheduler (cron / Windows Task Scheduler): import + report.

Exit code 0 = success, 1 = failure. That is what schedulers and monitoring check.
"""

import logging
import sys

from sales_lab.config import Settings
from sales_lab.errors import SalesLabError
from sales_lab.service import create_service

logger = logging.getLogger("run_daily")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    try:
        service = create_service(settings)
        service.import_file(settings.input_path, settings.output_dir / "rejected.csv")
        service.write_report(settings.output_dir / "category_report.csv")
    except (SalesLabError, FileNotFoundError):
        logger.exception("Daily job failed")
        return 1
    logger.info("Daily job finished successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
