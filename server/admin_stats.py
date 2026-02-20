"""
Admin statistics tracking for usage monitoring
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


class AdminStatsTracker:
    """Track usage statistics for admin dashboard"""

    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.unique_users = set()
        self.response_times = []
        self.recent_queries = []
        self.requests_by_hour = defaultdict(int)
        self.users_by_day = defaultdict(set)
        self.login_count = 0

    def track_request(
        self,
        user_ip: str,
        query: str,
        model: str,
        response_time: float,
        status: str = "success"
    ):
        """Track a chat request"""
        self.total_requests += 1
        self.unique_users.add(user_ip)
        self.response_times.append(response_time)

        # Track by hour for trends
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        self.requests_by_hour[current_hour] += 1

        # Track users by day
        current_day = datetime.now().strftime("%Y-%m-%d")
        self.users_by_day[current_day].add(user_ip)

        # Store recent query
        query_record = {
            "timestamp": datetime.now().isoformat(),
            "user_ip": user_ip,
            "query": query[:200],  # Limit length
            "model": model,
            "response_time": response_time,
            "status": status
        }

        self.recent_queries.insert(0, query_record)

        # Keep only last 100 queries
        if len(self.recent_queries) > 100:
            self.recent_queries = self.recent_queries[:100]

    def track_login(self):
        """Track a login event"""
        self.login_count += 1

    def get_stats(self) -> Dict:
        """Get current statistics"""
        uptime = time.time() - self.start_time

        # Get today's stats
        today = datetime.now().strftime("%Y-%m-%d")
        requests_24h = sum(
            count for hour, count in self.requests_by_hour.items()
            if hour.startswith(today)
        )
        users_24h = len(self.users_by_day.get(today, set()))

        # Calculate average response time
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times
            else 0
        )

        # Calculate response time trend (simple: last 10 vs previous 10)
        response_time_trend = 0
        if len(self.response_times) >= 20:
            recent_avg = sum(self.response_times[:10]) / 10
            older_avg = sum(self.response_times[10:20]) / 10
            if older_avg > 0:
                response_time_trend = ((recent_avg - older_avg) / older_avg) * 100

        return {
            "total_requests": self.total_requests,
            "unique_users": len(self.unique_users),
            "avg_response_time": avg_response_time,
            "uptime_seconds": int(uptime),
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "requests_24h": requests_24h,
            "users_24h": users_24h,
            "response_time_trend": response_time_trend,
            "login_count": self.login_count
        }

    def get_recent_queries(self, limit: int = 50) -> List[Dict]:
        """Get recent queries"""
        return self.recent_queries[:limit]


# Global instance
stats_tracker = AdminStatsTracker()
