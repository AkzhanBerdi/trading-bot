from datetime import datetime

import pytz


class MarketTimer:
    def __init__(self):
        self.high_activity_periods = [
            (0, 4),  # Asia session (00:00-04:00 UTC)
            (8, 16),  # US/EU overlap (08:00-16:00 UTC)
        ]

    def get_trading_intensity(self) -> float:
        """Adjust trading frequency based on market hours"""
        utc_hour = datetime.now(pytz.UTC).hour

        # Check if current hour is in high activity period
        for start_hour, end_hour in self.high_activity_periods:
            if start_hour <= utc_hour <= end_hour:
                return 1.0  # Normal frequency

        return 0.5  # Reduced frequency during low volume

    def get_optimal_sleep_time(self, base_sleep_time: float = 15.0) -> float:
        """Calculate optimal sleep time based on market activity"""
        intensity = self.get_trading_intensity()
        return base_sleep_time / intensity

    def get_market_session_info(self) -> dict:
        """Get current market session information"""
        utc_hour = datetime.now(pytz.UTC).hour

        if 0 <= utc_hour <= 4:
            session = "ASIA"
            activity = "HIGH"
        elif 8 <= utc_hour <= 16:
            session = "US_EU_OVERLAP"
            activity = "HIGH"
        elif 17 <= utc_hour <= 23:
            session = "US_AFTERNOON"
            activity = "MEDIUM"
        else:
            session = "OFF_HOURS"
            activity = "LOW"

        return {
            "session": session,
            "activity_level": activity,
            "trading_intensity": self.get_trading_intensity(),
            "utc_hour": utc_hour,
        }
