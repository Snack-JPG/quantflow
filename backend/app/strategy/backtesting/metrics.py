"""
Performance metrics calculator for backtesting results.
"""
import numpy as np
from typing import List, Tuple, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import math

from ..models import Position, PerformanceMetrics, BacktestConfig


class MetricsCalculator:
    """Calculate comprehensive performance metrics from backtest results."""

    def __init__(self):
        self.daily_returns: List[float] = []

    def calculate(
        self,
        positions: List[Position],
        equity_curve: List[Tuple[datetime, Decimal]],
        config: BacktestConfig
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics.

        Args:
            positions: List of all positions (closed and open)
            equity_curve: Equity value over time
            config: Backtest configuration

        Returns:
            Comprehensive performance metrics
        """
        # Filter closed positions only
        closed_positions = [p for p in positions if p.status.value == "closed"]

        if not closed_positions:
            # No trades executed, return empty metrics
            return self._empty_metrics()

        # Calculate returns
        self.daily_returns = self._calculate_daily_returns(equity_curve)
        total_return = self._calculate_total_return(equity_curve)
        total_pnl = sum(p.pnl for p in closed_positions if p.pnl)

        # Risk-adjusted returns
        sharpe = self._calculate_sharpe_ratio(self.daily_returns, config.risk_free_rate)
        sortino = self._calculate_sortino_ratio(self.daily_returns, config.risk_free_rate)

        # Risk metrics
        max_dd, max_dd_duration = self._calculate_max_drawdown(equity_curve)
        volatility = self._calculate_volatility(self.daily_returns)
        downside_dev = self._calculate_downside_deviation(self.daily_returns)
        var_95, cvar_95 = self._calculate_var_cvar(self.daily_returns, 0.95)

        # Trade statistics
        winning_trades = [p for p in closed_positions if p.pnl and p.pnl > 0]
        losing_trades = [p for p in closed_positions if p.pnl and p.pnl <= 0]

        total_trades = len(closed_positions)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        # Profit factor
        gross_profit = sum(p.pnl for p in winning_trades if p.pnl)
        gross_loss = abs(sum(p.pnl for p in losing_trades if p.pnl))
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        # Average trade metrics
        avg_win = gross_profit / len(winning_trades) if winning_trades else Decimal('0')
        avg_loss = gross_loss / len(losing_trades) if losing_trades else Decimal('0')
        avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else Decimal('0')

        # Best and worst trades
        best_trade = max(closed_positions, key=lambda p: p.pnl if p.pnl else 0)
        worst_trade = min(closed_positions, key=lambda p: p.pnl if p.pnl else 0)

        # Duration metrics
        holding_periods = [
            p.exit_time - p.entry_time
            for p in closed_positions
            if p.exit_time
        ]

        avg_holding = (
            sum(holding_periods, timedelta()) / len(holding_periods)
            if holding_periods else timedelta()
        )
        max_holding = max(holding_periods) if holding_periods else timedelta()
        min_holding = min(holding_periods) if holding_periods else timedelta()

        # Activity metrics
        duration = equity_curve[-1][0] - equity_curve[0][0]
        days = duration.days if duration.days > 0 else 1
        trades_per_day = total_trades / days

        # Calculate exposure (time in market)
        exposure_pct = self._calculate_exposure(positions, equity_curve)

        # Additional metrics
        calmar = self._calculate_calmar_ratio(total_return, max_dd)
        recovery_factor = float(total_pnl / (equity_curve[0][1] * Decimal(str(max_dd/100)))) if max_dd > 0 else 0
        expectancy = avg_trade_pnl

        # Kelly Criterion
        kelly = self._calculate_kelly_criterion(win_rate/100, profit_factor)

        return PerformanceMetrics(
            total_return=total_return,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            volatility=volatility,
            downside_deviation=downside_dev,
            var_95=var_95,
            cvar_95=cvar_95,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_trade_pnl=avg_trade_pnl,
            best_trade_pnl=best_trade.pnl if best_trade.pnl else Decimal('0'),
            worst_trade_pnl=worst_trade.pnl if worst_trade.pnl else Decimal('0'),
            avg_holding_period=avg_holding,
            max_holding_period=max_holding,
            min_holding_period=min_holding,
            trades_per_day=trades_per_day,
            exposure_pct=exposure_pct,
            recovery_factor=recovery_factor,
            expectancy=expectancy,
            kelly_criterion=kelly
        )

    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics when no trades executed."""
        return PerformanceMetrics(
            total_return=0.0,
            total_pnl=Decimal('0'),
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=timedelta(),
            volatility=0.0,
            downside_deviation=0.0,
            var_95=0.0,
            cvar_95=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_win=Decimal('0'),
            avg_loss=Decimal('0'),
            avg_trade_pnl=Decimal('0'),
            best_trade_pnl=Decimal('0'),
            worst_trade_pnl=Decimal('0'),
            avg_holding_period=timedelta(),
            max_holding_period=timedelta(),
            min_holding_period=timedelta(),
            trades_per_day=0.0,
            exposure_pct=0.0,
            recovery_factor=0.0,
            expectancy=Decimal('0'),
            kelly_criterion=0.0
        )

    def _calculate_daily_returns(
        self,
        equity_curve: List[Tuple[datetime, Decimal]]
    ) -> List[float]:
        """Calculate daily returns from equity curve."""
        if len(equity_curve) < 2:
            return []

        daily_returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i-1][1]
            curr_equity = equity_curve[i][1]
            if prev_equity > 0:
                ret = float((curr_equity - prev_equity) / prev_equity)
                daily_returns.append(ret)

        return daily_returns

    def _calculate_total_return(
        self,
        equity_curve: List[Tuple[datetime, Decimal]]
    ) -> float:
        """Calculate total return percentage."""
        if len(equity_curve) < 2:
            return 0.0

        initial = equity_curve[0][1]
        final = equity_curve[-1][1]

        if initial == 0:
            return 0.0

        return float((final - initial) / initial * 100)

    def _calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float
    ) -> float:
        """
        Calculate Sharpe ratio (annualized).

        Sharpe = (Return - Risk Free Rate) / Volatility
        """
        if not returns or len(returns) < 2:
            return 0.0

        # Convert to numpy for calculations
        returns_arr = np.array(returns)

        # Annualize metrics (assuming daily returns)
        annual_return = np.mean(returns_arr) * 252
        annual_vol = np.std(returns_arr) * np.sqrt(252)

        if annual_vol == 0:
            return 0.0

        return (annual_return - risk_free_rate) / annual_vol

    def _calculate_sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: float
    ) -> float:
        """
        Calculate Sortino ratio (uses downside deviation).

        Sortino = (Return - Risk Free Rate) / Downside Deviation
        """
        if not returns or len(returns) < 2:
            return 0.0

        returns_arr = np.array(returns)

        # Annualize return
        annual_return = np.mean(returns_arr) * 252

        # Calculate downside deviation (only negative returns)
        downside_returns = returns_arr[returns_arr < 0]
        if len(downside_returns) == 0:
            return float('inf')  # No downside risk

        downside_dev = np.std(downside_returns) * np.sqrt(252)

        if downside_dev == 0:
            return 0.0

        return (annual_return - risk_free_rate) / downside_dev

    def _calculate_calmar_ratio(
        self,
        total_return: float,
        max_drawdown: float
    ) -> float:
        """
        Calculate Calmar ratio.

        Calmar = Annual Return / Max Drawdown
        """
        if max_drawdown == 0:
            return 0.0

        # Assume total_return is already annualized or for the full period
        return abs(total_return / max_drawdown)

    def _calculate_max_drawdown(
        self,
        equity_curve: List[Tuple[datetime, Decimal]]
    ) -> Tuple[float, timedelta]:
        """
        Calculate maximum drawdown and duration.

        Returns:
            (max_drawdown_pct, max_duration)
        """
        if len(equity_curve) < 2:
            return 0.0, timedelta()

        equity_values = [float(eq) for _, eq in equity_curve]
        timestamps = [ts for ts, _ in equity_curve]

        # Calculate running maximum
        running_max = np.maximum.accumulate(equity_values)

        # Calculate drawdowns
        drawdowns = (equity_values - running_max) / running_max * 100

        # Find maximum drawdown
        max_dd = abs(min(drawdowns))

        # Find drawdown duration
        max_duration = timedelta()
        current_dd_start = None

        for i, dd in enumerate(drawdowns):
            if dd < 0 and current_dd_start is None:
                # Drawdown started
                current_dd_start = i
            elif dd == 0 and current_dd_start is not None:
                # Drawdown ended
                duration = timestamps[i] - timestamps[current_dd_start]
                max_duration = max(max_duration, duration)
                current_dd_start = None

        # Check if still in drawdown at end
        if current_dd_start is not None:
            duration = timestamps[-1] - timestamps[current_dd_start]
            max_duration = max(max_duration, duration)

        return max_dd, max_duration

    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate annualized volatility."""
        if not returns:
            return 0.0

        return np.std(returns) * np.sqrt(252) * 100  # Annualized, as percentage

    def _calculate_downside_deviation(self, returns: List[float]) -> float:
        """Calculate annualized downside deviation."""
        if not returns:
            return 0.0

        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return 0.0

        return np.std(negative_returns) * np.sqrt(252) * 100

    def _calculate_var_cvar(
        self,
        returns: List[float],
        confidence: float
    ) -> Tuple[float, float]:
        """
        Calculate Value at Risk and Conditional VaR.

        Args:
            returns: Daily returns
            confidence: Confidence level (e.g., 0.95)

        Returns:
            (VaR, CVaR) as percentages
        """
        if not returns:
            return 0.0, 0.0

        returns_arr = np.array(returns)
        var_percentile = (1 - confidence) * 100
        var = np.percentile(returns_arr, var_percentile) * 100

        # CVaR is the average of returns worse than VaR
        worse_returns = returns_arr[returns_arr <= var/100]
        cvar = np.mean(worse_returns) * 100 if len(worse_returns) > 0 else var

        return abs(var), abs(cvar)

    def _calculate_exposure(
        self,
        positions: List[Position],
        equity_curve: List[Tuple[datetime, Decimal]]
    ) -> float:
        """Calculate percentage of time with open positions."""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        total_duration = equity_curve[-1][0] - equity_curve[0][0]
        if total_duration.total_seconds() == 0:
            return 0.0

        # Calculate time in market
        time_in_market = timedelta()
        for position in positions:
            if position.exit_time:
                duration = position.exit_time - position.entry_time
            else:
                # Still open
                duration = equity_curve[-1][0] - position.entry_time
            time_in_market += duration

        return (time_in_market.total_seconds() / total_duration.total_seconds()) * 100

    def _calculate_kelly_criterion(
        self,
        win_rate: float,
        profit_factor: float
    ) -> float:
        """
        Calculate Kelly criterion for optimal position sizing.

        Kelly % = (p * b - q) / b
        where:
            p = probability of winning
            q = probability of losing (1 - p)
            b = ratio of win to loss
        """
        if profit_factor <= 1 or win_rate <= 0:
            return 0.0

        p = win_rate  # Already as decimal (0-1)
        q = 1 - p
        b = profit_factor

        kelly_pct = (p * b - q) / b

        # Cap at 25% for safety
        return min(max(0, kelly_pct * 100), 25.0)