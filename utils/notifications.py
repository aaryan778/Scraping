"""
Notification system for error alerts and monitoring
Supports console, file logging, and future Slack integration
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class NotificationService:
    """Service for sending notifications about errors and events"""

    def __init__(self):
        """Initialize notification service"""
        self.enabled = os.getenv("ENABLE_NOTIFICATIONS", "true").lower() == "true"
        self.slack_webhook = os.getenv("NOTIFICATION_SLACK_WEBHOOK", "")
        self.email = os.getenv("NOTIFICATION_EMAIL", "")

        # Notification toggles
        self.notify_scrape_failure = os.getenv("NOTIFY_ON_SCRAPE_FAILURE", "true").lower() == "true"
        self.notify_db_error = os.getenv("NOTIFY_ON_DB_ERROR", "true").lower() == "true"
        self.notify_validation_errors = os.getenv("NOTIFY_ON_VALIDATION_ERRORS", "true").lower() == "true"

        # Setup logger
        self._setup_logger()

        if self.enabled:
            logger.info("✅ Notification service enabled")
        else:
            logger.info("⚠️ Notification service disabled")

    def _setup_logger(self):
        """Configure loguru logger"""
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"
        log_file_path = os.getenv("LOG_FILE_PATH", "logs/app.log")
        log_rotation = os.getenv("LOG_ROTATION", "10 MB")
        log_retention = os.getenv("LOG_RETENTION", "30 days")

        # Remove default handler
        logger.remove()

        # Add console handler with colors
        logger.add(
            lambda msg: print(msg, end=""),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True
        )

        # Add file handler if enabled
        if log_to_file:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            logger.add(
                log_file_path,
                rotation=log_rotation,
                retention=log_retention,
                level=log_level,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
            )

    def notify_error(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        critical: bool = False
    ):
        """
        Send error notification

        Args:
            error_type: Type of error (scrape_failure, db_error, validation_error)
            message: Error message
            details: Additional error details
            critical: Whether this is a critical error
        """
        if not self.enabled:
            return

        # Check if we should notify for this error type
        should_notify = False
        if error_type == "scrape_failure" and self.notify_scrape_failure:
            should_notify = True
        elif error_type == "db_error" and self.notify_db_error:
            should_notify = True
        elif error_type == "validation_error" and self.notify_validation_errors:
            should_notify = True

        if not should_notify:
            return

        # Log the error
        log_message = f"[{error_type.upper()}] {message}"
        if details:
            log_message += f"\nDetails: {details}"

        if critical:
            logger.critical(log_message)
        else:
            logger.error(log_message)

        # Send to Slack if configured (future implementation)
        if self.slack_webhook:
            self._send_to_slack(error_type, message, details, critical)

    def notify_success(self, event: str, message: str, stats: Optional[Dict[str, Any]] = None):
        """
        Send success notification

        Args:
            event: Event name
            message: Success message
            stats: Statistics about the event
        """
        if not self.enabled:
            return

        log_message = f"✅ [{event.upper()}] {message}"
        if stats:
            log_message += f"\nStats: {stats}"

        logger.success(log_message)

    def notify_warning(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Send warning notification

        Args:
            message: Warning message
            details: Additional details
        """
        if not self.enabled:
            return

        log_message = f"⚠️ {message}"
        if details:
            log_message += f"\nDetails: {details}"

        logger.warning(log_message)

    def _send_to_slack(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]],
        critical: bool
    ):
        """
        Send notification to Slack (future implementation)

        Args:
            error_type: Type of error
            message: Error message
            details: Error details
            critical: Is critical error
        """
        # TODO: Implement Slack webhook integration
        # For now, just log that we would send to Slack
        logger.debug(f"Would send to Slack: {error_type} - {message}")

    def log_scraping_activity(
        self,
        job_title: str,
        country: str,
        jobs_found: int,
        duration: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Log scraping activity

        Args:
            job_title: Job title searched
            country: Country searched
            jobs_found: Number of jobs found
            duration: Duration in seconds
            success: Whether scraping was successful
            error: Error message if failed
        """
        if success:
            logger.info(
                f"🔍 Scraped {jobs_found} jobs for '{job_title}' in {country} "
                f"(took {duration:.2f}s)"
            )
        else:
            self.notify_error(
                "scrape_failure",
                f"Failed to scrape '{job_title}' in {country}",
                {"error": error, "duration": duration}
            )

    def log_validation_failure(
        self,
        job_data: Dict[str, Any],
        validation_errors: list,
        save_to_file: bool = True
    ):
        """
        Log validation failure

        Args:
            job_data: Job data that failed validation
            validation_errors: List of validation errors
            save_to_file: Whether to save to validation log file
        """
        error_msg = f"Validation failed for job: {job_data.get('title', 'Unknown')}"

        if save_to_file:
            # Save to validation failures log
            validation_log_path = "logs/validation_failures.log"
            os.makedirs(os.path.dirname(validation_log_path), exist_ok=True)

            with open(validation_log_path, "a") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Timestamp: {datetime.utcnow().isoformat()}\n")
                f.write(f"Job Title: {job_data.get('title', 'Unknown')}\n")
                f.write(f"Company: {job_data.get('company', 'Unknown')}\n")
                f.write(f"Errors: {validation_errors}\n")
                f.write(f"Full Data: {job_data}\n")

        self.notify_error(
            "validation_error",
            error_msg,
            {"errors": validation_errors, "job_id": job_data.get("job_id")}
        )


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create global notification service"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def notify_error(error_type: str, message: str, details: Optional[Dict[str, Any]] = None, critical: bool = False):
    """Convenience function to send error notification"""
    service = get_notification_service()
    service.notify_error(error_type, message, details, critical)


def notify_success(event: str, message: str, stats: Optional[Dict[str, Any]] = None):
    """Convenience function to send success notification"""
    service = get_notification_service()
    service.notify_success(event, message, stats)


def notify_warning(message: str, details: Optional[Dict[str, Any]] = None):
    """Convenience function to send warning notification"""
    service = get_notification_service()
    service.notify_warning(message, details)


if __name__ == "__main__":
    # Test notifications
    service = get_notification_service()

    # Test error
    service.notify_error(
        "scrape_failure",
        "Failed to scrape jobs from Google",
        {"url": "https://google.com/jobs", "status_code": 403}
    )

    # Test success
    service.notify_success(
        "scraping_complete",
        "Successfully scraped all jobs",
        {"total_jobs": 234, "duration": 120.5}
    )

    # Test warning
    service.notify_warning(
        "Rate limit approaching",
        {"requests_remaining": 10}
    )
