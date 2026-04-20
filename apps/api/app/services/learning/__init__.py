"""Learning sub-package — autonomous exploration + page verification.

Members are intentionally loaded lazily where Playwright is involved
so that importing ``app.services.learning`` at app startup stays cheap.
"""
