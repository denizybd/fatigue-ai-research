"""Non-material exact decision checks. Does not import project fit/result code."""
from __future__ import annotations

import json
import math
from fractions import Fraction as F
from pathlib import Path


def binary_loss(p_low: F, action: F, alpha: F = F(1, 10)) -> F:
    """W in {4,5}; p_low is P(W=4)."""
    result = F(0)
    for value, prob in ((F(4), p_low), (F(5), 1 - p_low)):
        residual = value - action
        result += prob * (alpha - int(residual < 0)) * residual
    return result


def binary_safe_action(p_low: F, alpha: F = F(1, 10)) -> F:
    # Largest minimizer; strict dangerous event W<a matters at atoms.
    return F(4) if p_low > alpha else F(5)


def main() -> None:
    alpha = F(1, 10)
    safe = 4.1
    minimax = 4 + math.sqrt(0.2)
    shifted = minimax - 4
    r1 = (shifted - 0.1) ** 2 / 2
    r2 = 0.105 - 0.1 * shifted
    assert abs(r1 - r2) < 1e-14
    assert shifted > 0.1
    uniform = {
        "models": ["Uniform(4,5)", "Uniform(5,6)"],
        "alpha": 0.1,
        "cap_log10_cycles": 6,
        "safe_min_q_action": safe,
        "unconstrained_minimax_pinball_action": minimax,
        "closed_form_action": "4+sqrt(0.2)",
        "risk_under_first_model_at_safe_action": 0.1,
        "risk_under_first_model_at_minimax_action": shifted,
        "worst_regret_at_safe_action": 0.095,
        "worst_regret_at_minimax_action": max(r1, r2),
        "derivation": "For x=a-4 in [.1,1], r1=(x-.1)^2/2 and r2=.105-.1*x. They cross at x=sqrt(.2); one is increasing and the other decreasing.",
    }

    # A coherent joint P_m(O,W), with P(O=L)=P(O=H)=1/2 under both.
    models = {
        "A": {"L": F(1, 4), "H": F(1, 20)},
        "B": {"L": F(9, 100), "H": F(1, 100)},
    }
    prior_p = {m: (d["L"] + d["H"]) / 2 for m, d in models.items()}
    prior_q = {m: binary_safe_action(p) for m, p in prior_p.items()}
    prior_action = min(prior_q.values())
    prior_raw = {m: binary_loss(p, prior_action) for m, p in prior_p.items()}
    prior_bayes = {m: binary_loss(p, prior_q[m]) for m, p in prior_p.items()}
    prior_regret = {m: prior_raw[m] - prior_bayes[m] for m in models}

    conditional_action = {
        outcome: min(binary_safe_action(d[outcome]) for d in models.values())
        for outcome in ("L", "H")
    }
    conditional_risk = {
        m: {o: (p if conditional_action[o] > 4 else F(0)) for o, p in d.items()}
        for m, d in models.items()
    }
    assert all(risk <= alpha for d in conditional_risk.values() for risk in d.values())
    future_raw = {}
    future_bayes = {}
    future_regret = {}
    identity_residual = {}
    for m, d in models.items():
        future_raw[m] = sum(binary_loss(p, conditional_action[o]) / 2 for o, p in d.items())
        future_bayes[m] = sum(binary_loss(p, binary_safe_action(p)) / 2 for p in d.values())
        future_regret[m] = future_raw[m] - future_bayes[m]
        assert future_regret[m] >= 0
        identity_residual[m] = (prior_raw[m] - future_raw[m]) - (
            prior_regret[m] - future_regret[m] + prior_bayes[m] - future_bayes[m]
        )
        assert identity_residual[m] == 0
        assert prior_bayes[m] - future_bayes[m] >= 0

    min_modelwise_gain = min(prior_regret[m] - future_regret[m] for m in models)
    worst_residual_reduction = max(prior_regret.values()) - max(future_regret.values())
    assert min_modelwise_gain == 0
    assert worst_residual_reduction == F(9, 200)
    assert min_modelwise_gain != worst_residual_reduction

    # An independent sentinel cannot change the query law, actions or losses.
    no_info = {
        m: sum(binary_loss(prior_p[m], prior_action) / 2 for _ in ("L", "H"))
        for m in models
    }
    assert no_info == prior_raw

    # The cap atom is safe because the dangerous event is strict.
    # P(W=4)=.05, P(W=6)=.95: a=6 has risk .05, while F(6)=1.
    cap_atom = {"P_W_below_cap": 0.05, "F_at_cap": 1.0, "safe_action": 6, "risk_at_safe_action": 0.05}
    assert cap_atom["risk_at_safe_action"] <= float(alpha)

    def scalarize(obj):
        if isinstance(obj, F):
            return {"exact_fraction": str(obj), "float": float(obj)}
        if isinstance(obj, dict):
            return {key: scalarize(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [scalarize(value) for value in obj]
        return obj

    receipt = {
        "scope": "Manufactured decision examples only. No material dataset, fitted model or phase6 output read.",
        "uniform": uniform,
        "coherent_binary": {
            "P_O_L": F(1, 2),
            "conditional_P_W4": models,
            "prior_P_W4": prior_p,
            "prior_safe_action": prior_action,
            "conditional_safe_action": conditional_action,
            "conditional_strict_risk": conditional_risk,
            "prior_raw_loss": prior_raw,
            "prior_Bayes_loss": prior_bayes,
            "prior_regret": prior_regret,
            "future_raw_loss": future_raw,
            "future_Bayes_loss": future_bayes,
            "future_conditional_regret": future_regret,
            "min_modelwise_regret_gain": min_modelwise_gain,
            "reduction_in_worst_conditional_regret": worst_residual_reduction,
            "oracle_identity_residual": identity_residual,
        },
        "independent_no_information_sentinel_loss_equals_prior": True,
        "cap_atom": cap_atom,
        "all_assertions_passed": True,
    }
    destination = Path(__file__).with_name("theory_check_receipt.json")
    destination.write_text(json.dumps(scalarize(receipt), indent=2) + "\n")
    print(json.dumps({"all_assertions_passed": True, "receipt": str(destination), "uniform_minimax_action": minimax}))


if __name__ == "__main__":
    main()
