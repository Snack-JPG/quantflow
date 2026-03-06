"""
Walk-forward optimization for strategy parameter tuning.
"""
from typing import List, Dict, Any, Tuple, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import itertools
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

from .engine import BacktestEngine, DataFeed
from ..base import Strategy
from ..models import BacktestConfig, BacktestResult


@dataclass
class OptimizationWindow:
    """Single optimization window for walk-forward analysis."""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    window_id: int


@dataclass
class ParameterRange:
    """Parameter range for optimization."""
    name: str
    min_value: Any
    max_value: Any
    step: Any
    values: Optional[List[Any]] = None

    def get_values(self) -> List[Any]:
        """Get all parameter values to test."""
        if self.values:
            return self.values

        # Generate range based on type
        if isinstance(self.min_value, int):
            return list(range(self.min_value, self.max_value + 1, self.step))
        elif isinstance(self.min_value, float):
            values = []
            current = self.min_value
            while current <= self.max_value:
                values.append(current)
                current += self.step
            return values
        else:
            return [self.min_value, self.max_value]


@dataclass
class OptimizationResult:
    """Results from optimization run."""
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Tuple[Dict[str, Any], float]]
    window_results: List[Dict[str, Any]]  # Results per window
    out_of_sample_performance: Optional[BacktestResult] = None


class WalkForwardOptimizer:
    """
    Walk-forward optimization for robust parameter selection.

    This implements rolling window optimization where:
    1. Optimize on training window
    2. Test on out-of-sample window
    3. Roll forward and repeat
    """

    def __init__(
        self,
        strategy_class: type,
        parameter_ranges: List[ParameterRange],
        objective: str = "sharpe",
        windows: int = 5,
        train_ratio: float = 0.8
    ):
        """
        Initialize optimizer.

        Args:
            strategy_class: Strategy class to optimize
            parameter_ranges: Parameters to optimize
            objective: Optimization objective ("sharpe", "return", "calmar", etc.)
            windows: Number of walk-forward windows
            train_ratio: Ratio of data for training vs testing
        """
        self.strategy_class = strategy_class
        self.parameter_ranges = parameter_ranges
        self.objective = objective
        self.windows = windows
        self.train_ratio = train_ratio
        self.logger = logging.getLogger("optimization")

    def optimize(
        self,
        data: DataFeed,
        config: BacktestConfig,
        parallel: bool = True
    ) -> OptimizationResult:
        """
        Run walk-forward optimization.

        Args:
            data: Historical data
            config: Base backtest configuration
            parallel: Run backtests in parallel

        Returns:
            Optimization results with best parameters
        """
        # Create optimization windows
        windows = self._create_windows(data.start_time, data.end_time)

        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations()

        self.logger.info(
            f"Starting walk-forward optimization: "
            f"{len(windows)} windows, {len(param_combinations)} parameter sets"
        )

        # Run optimization for each window
        window_results = []
        for window in windows:
            self.logger.info(f"Optimizing window {window.window_id}")

            # Filter data for training period
            train_data = self._filter_data(data, window.train_start, window.train_end)

            # Find best parameters on training data
            best_params, best_score = self._optimize_window(
                train_data, config, param_combinations, parallel
            )

            # Test on out-of-sample data
            test_data = self._filter_data(data, window.test_start, window.test_end)
            test_result = self._run_single_backtest(
                test_data, config, best_params
            )

            window_results.append({
                'window_id': window.window_id,
                'train_period': (window.train_start, window.train_end),
                'test_period': (window.test_start, window.test_end),
                'best_params': best_params,
                'train_score': best_score,
                'test_score': self._get_objective_value(test_result),
                'test_metrics': test_result.metrics
            })

        # Select final parameters (average of best params across windows)
        final_params = self._select_final_parameters(window_results)

        # Run final backtest on entire dataset
        final_result = self._run_single_backtest(data, config, final_params)

        return OptimizationResult(
            best_params=final_params,
            best_score=self._get_objective_value(final_result),
            all_results=[],  # Can store all individual results if needed
            window_results=window_results,
            out_of_sample_performance=final_result
        )

    def _create_windows(
        self,
        start: datetime,
        end: datetime
    ) -> List[OptimizationWindow]:
        """Create walk-forward optimization windows."""
        total_duration = end - start
        window_duration = total_duration / self.windows

        train_duration = window_duration * self.train_ratio
        test_duration = window_duration * (1 - self.train_ratio)

        windows = []
        for i in range(self.windows):
            window_start = start + (window_duration * i)

            train_start = window_start
            train_end = train_start + train_duration
            test_start = train_end
            test_end = test_start + test_duration

            windows.append(OptimizationWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                window_id=i
            ))

        return windows

    def _generate_parameter_combinations(self) -> List[Dict[str, Any]]:
        """Generate all parameter combinations to test."""
        param_values = []
        param_names = []

        for param_range in self.parameter_ranges:
            param_names.append(param_range.name)
            param_values.append(param_range.get_values())

        # Generate all combinations
        combinations = []
        for values in itertools.product(*param_values):
            param_dict = dict(zip(param_names, values))
            combinations.append(param_dict)

        return combinations

    def _optimize_window(
        self,
        data: DataFeed,
        config: BacktestConfig,
        param_combinations: List[Dict[str, Any]],
        parallel: bool
    ) -> Tuple[Dict[str, Any], float]:
        """Optimize parameters on single window."""
        results = []

        if parallel:
            # Run backtests in parallel
            with ProcessPoolExecutor() as executor:
                futures = []
                for params in param_combinations:
                    future = executor.submit(
                        self._run_single_backtest,
                        data, config, params
                    )
                    futures.append((future, params))

                for future, params in futures:
                    try:
                        result = future.result(timeout=60)
                        score = self._get_objective_value(result)
                        results.append((params, score))
                    except Exception as e:
                        self.logger.error(f"Backtest failed for {params}: {e}")
                        results.append((params, float('-inf')))
        else:
            # Run sequentially
            for params in param_combinations:
                try:
                    result = self._run_single_backtest(data, config, params)
                    score = self._get_objective_value(result)
                    results.append((params, score))
                except Exception as e:
                    self.logger.error(f"Backtest failed for {params}: {e}")
                    results.append((params, float('-inf')))

        # Find best parameters
        best_params, best_score = max(results, key=lambda x: x[1])
        return best_params, best_score

    def _run_single_backtest(
        self,
        data: DataFeed,
        config: BacktestConfig,
        params: Dict[str, Any]
    ) -> BacktestResult:
        """Run single backtest with given parameters."""
        # Create strategy with parameters
        strategy = self.strategy_class(
            name=f"{self.strategy_class.__name__}_optimized",
            symbols=['BTCUSDT'],  # Should be passed properly
            config=params
        )

        # Run backtest
        engine = BacktestEngine()
        return engine.run(strategy, data, config)

    def _get_objective_value(self, result: BacktestResult) -> float:
        """Extract objective value from backtest result."""
        metrics = result.metrics

        if self.objective == "sharpe":
            return metrics.sharpe_ratio
        elif self.objective == "return":
            return metrics.total_return
        elif self.objective == "calmar":
            return metrics.calmar_ratio
        elif self.objective == "sortino":
            return metrics.sortino_ratio
        elif self.objective == "profit_factor":
            return metrics.profit_factor
        elif self.objective == "win_rate":
            return metrics.win_rate
        else:
            return metrics.total_return

    def _filter_data(
        self,
        data: DataFeed,
        start: datetime,
        end: datetime
    ) -> DataFeed:
        """Filter data to specific time period."""
        filtered_books = [
            book for book in data.order_books
            if start <= book.timestamp <= end
        ]

        filtered_trades = [
            trade for trade in data.trades
            if start <= trade.timestamp <= end
        ]

        filtered_alerts = [
            alert for alert in data.alerts
            if start <= alert.timestamp <= end
        ]

        return DataFeed(
            order_books=filtered_books,
            trades=filtered_trades,
            alerts=filtered_alerts
        )

    def _select_final_parameters(
        self,
        window_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Select final parameters from window results.

        Use voting or averaging approach.
        """
        if not window_results:
            return {}

        # Collect all parameter values
        param_votes = {}
        for result in window_results:
            best_params = result['best_params']
            for param, value in best_params.items():
                if param not in param_votes:
                    param_votes[param] = []
                param_votes[param].append(value)

        # Select most common value for each parameter
        final_params = {}
        for param, values in param_votes.items():
            if isinstance(values[0], (int, float)):
                # Use average for numeric parameters
                final_params[param] = sum(values) / len(values)
                if isinstance(values[0], int):
                    final_params[param] = int(round(final_params[param]))
            else:
                # Use most common value for categorical parameters
                final_params[param] = max(set(values), key=values.count)

        return final_params


class GridSearchOptimizer:
    """
    Simple grid search optimization for parameter tuning.

    Simpler alternative to walk-forward optimization.
    """

    def __init__(
        self,
        strategy_class: type,
        parameter_grid: Dict[str, List[Any]],
        objective: str = "sharpe"
    ):
        """
        Initialize grid search optimizer.

        Args:
            strategy_class: Strategy class to optimize
            parameter_grid: Dictionary of parameter names to values to test
            objective: Optimization objective
        """
        self.strategy_class = strategy_class
        self.parameter_grid = parameter_grid
        self.objective = objective
        self.logger = logging.getLogger("grid_search")

    def optimize(
        self,
        data: DataFeed,
        config: BacktestConfig,
        parallel: bool = True
    ) -> Dict[str, Any]:
        """
        Run grid search optimization.

        Returns:
            Best parameters found
        """
        # Generate parameter combinations
        param_names = list(self.parameter_grid.keys())
        param_values = list(self.parameter_grid.values())
        combinations = list(itertools.product(*param_values))

        self.logger.info(f"Testing {len(combinations)} parameter combinations")

        results = []
        engine = BacktestEngine()

        for combo in combinations:
            params = dict(zip(param_names, combo))

            try:
                # Create strategy with parameters
                strategy = self.strategy_class(
                    name=f"{self.strategy_class.__name__}_grid",
                    symbols=['BTCUSDT'],
                    config=params
                )

                # Run backtest
                result = engine.run(strategy, data, config)

                # Get objective value
                if self.objective == "sharpe":
                    score = result.metrics.sharpe_ratio
                elif self.objective == "return":
                    score = result.metrics.total_return
                elif self.objective == "calmar":
                    score = result.metrics.calmar_ratio
                else:
                    score = result.metrics.total_return

                results.append((params, score))

            except Exception as e:
                self.logger.error(f"Backtest failed for {params}: {e}")
                results.append((params, float('-inf')))

        # Find best parameters
        best_params, best_score = max(results, key=lambda x: x[1])

        self.logger.info(
            f"Best parameters: {best_params} with {self.objective}={best_score:.3f}"
        )

        return best_params