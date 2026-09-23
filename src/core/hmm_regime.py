"""HMM Regime Detector for risk overlay.

Uses a 3-state Gaussian HMM to classify daily volatility regimes.
State 0: Low Volatility
State 1: Transitional
State 2: High Volatility (Crisis)
"""
import os
import joblib
import logging
import numpy as np

try:
    from hmmlearn.hmm import GaussianHMM
except ImportError:
    GaussianHMM = None

log = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "hmm_model.pkl")

def train_model(returns_array: np.ndarray):
    """Offline tool to fit the 3-state HMM on a long history of daily returns."""
    if GaussianHMM is None:
        raise ImportError("hmmlearn is not installed.")
        
    model = GaussianHMM(n_components=3, covariance_type="full", n_iter=1000, random_state=42)
    model.fit(returns_array.reshape(-1, 1))
    
    # Sort states by variance so State 2 is always the highest volatility (Crisis)
    variances = np.array([np.diag(model.covars_[i]) for i in range(3)]).flatten()
    order = np.argsort(variances)
    
    model.means_ = model.means_[order]
    model.covars_ = model.covars_[order]
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    log.info(f"HMM model saved to {MODEL_PATH} with variances: {variances[order]}")
    return model

def load_model():
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            log.warning(f"Could not load HMM model: {e}")
    return None

def get_current_regime(recent_returns: np.ndarray) -> int:
    """Returns 0 (Low Vol), 1 (Medium), 2 (High/Crisis)."""
    if GaussianHMM is None:
        return 0
    model = load_model()
    if not model or len(recent_returns) == 0:
        return 0
    
    try:
        state_sequence = model.predict(recent_returns.reshape(-1, 1))
        return int(state_sequence[-1])
    except Exception as e:
        log.warning(f"HMM prediction failed: {e}")
        return 0
