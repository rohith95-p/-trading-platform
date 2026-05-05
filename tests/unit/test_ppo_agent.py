"""
Property-based tests for the PPO Agent, guardrails, and trading environment.

**Validates: Requirements 7 (PPO Reinforcement Learning Agent)**
"""

import os
import tempfile

import numpy as np
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.drl.ppo_agent import PPOAgent, HOLD, BUY, SELL, VALID_ACTIONS
from src.drl.guardrails import ConstitutionalGuardrails
from src.drl.training_env import TradingEnvironment, N_FEATURES, N_ACTIONS


state_strategy = st.lists(
    st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    min_size=N_FEATURES,
    max_size=N_FEATURES,
).map(np.array)

action_strategy = st.integers(min_value=0, max_value=2)


@given(state=state_strategy)
@settings(max_examples=100)
def test_predict_always_returns_valid_action(state):
    """PPOAgent.predict must always return 0, 1, or 2 regardless of input state."""
    agent = PPOAgent()
    action = agent.predict(state)
    assert action in VALID_ACTIONS, f"Expected action in {{0,1,2}}, got {action}"


@given(action=action_strategy, state=state_strategy)
@settings(max_examples=100)
def test_guardrails_override_to_hold_when_circuit_breaker_triggered(action, state):
    """When circuit_breaker_triggered=True, any non-HOLD action must be overridden to HOLD."""
    assume(action != HOLD)
    guardrails = ConstitutionalGuardrails()
    context = {"circuit_breaker_triggered": True}
    result = guardrails.check(action, state, context)
    assert result == HOLD


@given(action=action_strategy, state=state_strategy)
@settings(max_examples=50)
def test_guardrails_pass_through_when_no_rules_fire(action, state):
    """When no guardrail rules fire, the original action is returned unchanged."""
    guardrails = ConstitutionalGuardrails(max_leverage=10.0)
    context = {"circuit_breaker_triggered": False, "current_leverage": 1.0}
    result = guardrails.check(action, state, context)
    assert result == action


@given(
    leverage=st.floats(min_value=10.01, max_value=100.0, allow_nan=False, allow_infinity=False),
    state=state_strategy,
)
@settings(max_examples=50)
def test_guardrails_block_buy_when_leverage_exceeded(leverage, state):
    """BUY action must be overridden to HOLD when current leverage exceeds the limit."""
    guardrails = ConstitutionalGuardrails(max_leverage=10.0)
    context = {"circuit_breaker_triggered": False, "current_leverage": leverage}
    result = guardrails.check(BUY, state, context)
    assert result == HOLD


def test_save_load_round_trip():
    """After save() and load(), the agent produces the same action for the same state."""
    agent = PPOAgent()
    env = TradingEnvironment(price_data=np.linspace(100, 110, 30))
    agent.train(env, total_timesteps=30)

    rng = np.random.default_rng(0)
    states = [rng.standard_normal(N_FEATURES).astype(np.float32) for _ in range(10)]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "ppo_model")
        agent.save(path)
        agent2 = PPOAgent()
        agent2.load(path)
        for state in states:
            assert agent.predict(state) == agent2.predict(state)


@given(action=action_strategy)
@settings(max_examples=100)
def test_env_step_returns_valid_obs_shape(action):
    """TradingEnvironment.step must return an observation with shape (N_FEATURES,)."""
    env = TradingEnvironment()
    env.reset()
    result = env.step(action)
    obs = result[0]
    reward = result[1]
    done = result[2]
    info = result[-1]
    assert obs.shape == (N_FEATURES,)
    assert isinstance(reward, float)
    assert isinstance(done, bool)
    assert isinstance(info, dict)


def test_predict_returns_hold_when_untrained():
    agent = PPOAgent()
    state = np.zeros(N_FEATURES, dtype=np.float32)
    action = agent.predict(state)
    assert action == HOLD


def test_guardrail_override_count_increments():
    g = ConstitutionalGuardrails()
    assert g.override_count == 0
    g.override_action(BUY, "test reason")
    assert g.override_count == 1
    g.override_action(SELL, "another reason")
    assert g.override_count == 2


def test_env_reset_returns_correct_shape():
    env = TradingEnvironment()
    result = env.reset()
    obs = result[0] if isinstance(result, tuple) else result
    assert obs.shape == (N_FEATURES,)


def test_env_action_space_has_three_actions():
    env = TradingEnvironment()
    assert env.action_space.n == N_ACTIONS


def test_env_full_episode():
    env = TradingEnvironment()
    env.reset()
    done = False
    steps = 0
    while not done:
        action = env.action_space.sample()
        result = env.step(action)
        obs = result[0]
        done = result[2]
        steps += 1
        assert obs.shape == (N_FEATURES,)
    assert steps > 0


def test_agent_train_sets_model():
    agent = PPOAgent()
    assert not agent.is_trained()
    env = TradingEnvironment(price_data=np.linspace(100, 110, 30))
    agent.train(env, total_timesteps=30)
    assert agent.is_trained()


def test_predict_with_context_circuit_breaker():
    agent = PPOAgent()
    env = TradingEnvironment(price_data=np.linspace(100, 110, 30))
    agent.train(env, total_timesteps=30)
    state = np.ones(N_FEATURES, dtype=np.float32)
    action = agent.predict_with_context(state, {"circuit_breaker_triggered": True})
    assert action == HOLD
