import numpy as np
from scipy import stats

def information_coefficient(signals: np.ndarray, forward_returns: np.ndarray) -> float:
    """Calculate the Information Coefficient (Pearson correlation) between signals and forward returns.
    
    Args:
        signals: The indicator values or strategy signals.
        forward_returns: The actual subsequent returns for the holding period.
    """
    valid = ~(np.isnan(signals) | np.isnan(forward_returns))
    if np.sum(valid) < 2:
        return 0.0
    return float(np.corrcoef(signals[valid], forward_returns[valid])[0, 1])

def icir(signals: np.ndarray, forward_returns: np.ndarray, window_size: int = 30) -> float:
    """Calculate the Information Coefficient to Information Ratio (ICIR).
    
    ICIR = mean(IC) / std(IC) over rolling windows.
    """
    valid = ~(np.isnan(signals) | np.isnan(forward_returns))
    s, r = signals[valid], forward_returns[valid]
    if len(s) < window_size * 2:
        return 0.0
        
    ics = []
    for i in range(0, len(s) - window_size, window_size):
        ic = np.corrcoef(s[i:i+window_size], r[i:i+window_size])[0, 1]
        if not np.isnan(ic):
            ics.append(ic)
            
    if len(ics) < 2 or np.std(ics) == 0:
        return 0.0
    return float(np.mean(ics) / np.std(ics))

def expected_max_sr(num_trials: int, sr_variance: float = 1.0) -> float:
    """Calculate the expected maximum Sharpe ratio from multiple independent trials.
    
    Equation 1 from "The Deflated Sharpe Ratio" (Bailey & Lopez de Prado, 2014)
    """
    if num_trials <= 1:
        return 0.0
    
    emc = 0.5772156649 # Euler-Mascheroni constant
    
    # Z^{-1} is the inverse CDF of standard normal
    z_inv_1 = stats.norm.ppf(1.0 - 1.0 / num_trials)
    z_inv_2 = stats.norm.ppf(1.0 - 1.0 / (num_trials * np.e))
    
    sr_0 = np.sqrt(sr_variance) * ((1 - emc) * z_inv_1 + emc * z_inv_2)
    return float(sr_0)

def deflated_sharpe_ratio(returns: np.ndarray, num_trials: int, sr_variance: float = 1.0, risk_free_rate: float = 0.0) -> float:
    """Calculate the Deflated Sharpe Ratio (DSR) to account for multiple testing and non-normality.
    
    Args:
        returns: Array of strategy returns.
        num_trials: Number of independent strategy configurations tested.
        sr_variance: Variance of the IS Sharpe ratios across all tested configurations.
                     Pass the actual computed variance from IS SRs, NOT 1.0.
                     If left at 1.0 (legacy), DSR will be severely underestimated for
                     low-frequency per-trade returns (bug: assumes unit-variance annualised SR).
    
    Note: When sr_variance is the default 1.0, the expected max SR at 140 trials is ~3.5,
    making DSR=0 for any strategy with per-trade SR < 3.5. Compute sr_variance from your
    actual IS Sharpe distribution before calling this.
    """
    if len(returns) < 3 or num_trials < 1:
        return 0.0
        
    # Convert returns to period SR
    period_std = np.std(returns)
    if period_std == 0:
        return 0.0
    
    sr = (np.mean(returns) - risk_free_rate) / period_std
    sr_0 = expected_max_sr(num_trials, sr_variance)
    
    t = len(returns)
    skew = stats.skew(returns)
    kurt = stats.kurtosis(returns, fisher=False) # Pearson's kurtosis
    
    num = (sr - sr_0) * np.sqrt(t - 1)
    den_sq = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr**2
    if den_sq <= 0:
        return 0.0
    den = np.sqrt(den_sq)
    
    dsr = stats.norm.cdf(num / den)
    return float(dsr)


def bonferroni_correction(p_value: float, num_tests: int) -> float:
    """Apply Bonferroni correction for multiple hypothesis testing."""
    return float(min(1.0, p_value * num_tests))
