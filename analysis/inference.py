"""Small-cluster inference for the in-position factor regression.

The in-position sample is 55 weekly observations drawn from 15 separate holding
episodes.  Clustering by episode is the right structure, but ordinary
cluster-robust ("CR1") standard errors are asymptotic in the *number of
clusters*, and fifteen is not many: CR1 is biased downward and its normal
reference distribution rejects too often.

Two standard corrections are implemented here.

``CR2`` is the bias-reduced linearisation of Bell and McCaffrey (2002): each
cluster's residuals are inflated by ``(I - H_gg)^{-1/2}`` before the meat matrix
is formed, which removes the leading bias term.  It is paired with
Bell--McCaffrey Satterthwaite degrees of freedom, which are typically far below
``G - 1`` and widen the reference distribution accordingly.

``wild_cluster_bootstrap`` is the restricted wild cluster bootstrap-t of Cameron,
Gelbach and Miller (2008), with Rademacher weights drawn once per cluster and
the null imposed on the residuals.  With 15 clusters there are 2^15 = 32,768
distinct weight vectors, so the bootstrap is not degenerate.  This is the
procedure generally recommended when the cluster count is small.

Neither is a way of recovering significance.  Both are expected to produce
larger p-values than CR1; that is the point.
"""

from __future__ import annotations

import numpy as np


def _cluster_slices(groups):
    groups = np.asarray(groups)
    return [np.where(groups == g)[0] for g in np.unique(groups)]


def _symmetric_inv_sqrt(matrix, tol=1e-12):
    """``M^{-1/2}`` for a symmetric positive semi-definite ``M``."""

    vals, vecs = np.linalg.eigh(matrix)
    vals = np.where(vals > tol, vals, tol)
    return vecs @ np.diag(vals ** -0.5) @ vecs.T


def cr2_inference(y, X, groups, coef_index):
    """CR2 standard error and Bell--McCaffrey Satterthwaite dof for one coefficient.

    Returns a dict with the coefficient, its CR2 standard error, the t-ratio,
    the Satterthwaite degrees of freedom, the two-sided p-value from a
    t-distribution on those dof, and the corresponding confidence interval.
    """

    from scipy import stats

    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta

    ell = np.zeros(k)
    ell[coef_index] = 1.0
    slices = _cluster_slices(groups)

    meat = np.zeros((k, k))
    for idx in slices:
        Xg = X[idx]
        Hg = Xg @ xtx_inv @ Xg.T
        Ag = _symmetric_inv_sqrt(np.eye(len(idx)) - Hg)
        adj = Xg.T @ Ag @ resid[idx]
        meat += np.outer(adj, adj)
    vcov = xtx_inv @ meat @ xtx_inv
    se = float(np.sqrt(ell @ vcov @ ell))

    # Bell-McCaffrey Satterthwaite degrees of freedom.
    annihilator = np.eye(n) - X @ xtx_inv @ X.T
    columns = []
    for idx in slices:
        Xg = X[idx]
        Ag = _symmetric_inv_sqrt(np.eye(len(idx)) - Xg @ xtx_inv @ Xg.T)
        columns.append(annihilator[:, idx] @ Ag @ Xg @ xtx_inv @ ell)
    G = np.column_stack(columns)
    GG = G.T @ G
    trace = float(np.trace(GG))
    dof = float(trace ** 2 / np.sum(GG * GG)) if np.sum(GG * GG) > 0 else float(len(slices) - 1)

    t_stat = float(beta[coef_index] / se) if se > 0 else np.nan
    p = float(2 * stats.t.sf(abs(t_stat), dof))
    crit = float(stats.t.ppf(0.975, dof))
    return {"b": float(beta[coef_index]), "se": se, "t": t_stat, "dof": dof, "p": p,
            "ci": [float(beta[coef_index] - crit * se), float(beta[coef_index] + crit * se)]}


def wild_cluster_bootstrap(y, X, groups, coef_index, reps=9999, seed=42):
    """Restricted wild cluster bootstrap-t p-value for ``beta[coef_index] == 0``.

    The null is imposed by re-fitting without the tested regressor, Rademacher
    weights are drawn once per cluster, and the bootstrap t-ratios use CR2 so
    that the reference distribution matches the statistic being compared.
    """

    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    groups = np.asarray(groups)
    observed = cr2_inference(y, X, groups, coef_index)["t"]

    keep = [j for j in range(X.shape[1]) if j != coef_index]
    Xr = X[:, keep]
    beta_r = np.linalg.pinv(Xr.T @ Xr) @ Xr.T @ y
    fitted_r = Xr @ beta_r
    resid_r = y - fitted_r

    uniq = np.unique(groups)
    index = {g: np.where(groups == g)[0] for g in uniq}
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(reps):
        weights = np.ones(len(y))
        draws = rng.choice([-1.0, 1.0], size=len(uniq))
        for g, w in zip(uniq, draws):
            weights[index[g]] = w
        y_star = fitted_r + weights * resid_r
        t_star = cr2_inference(y_star, X, groups, coef_index)["t"]
        if np.isfinite(t_star) and abs(t_star) >= abs(observed):
            count += 1
    return {"observed_t": float(observed), "reps": int(reps),
            "p": float((count + 1) / (reps + 1)), "weights": "Rademacher, one draw per cluster",
            "null_imposed": True}
