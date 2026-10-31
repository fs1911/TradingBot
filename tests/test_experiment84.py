from src.backtest.experiments_84 import register, run_experiment84_report


def test_register_and_report():
    reg = register()
    assert len(reg) > 80 and reg["p"].between(0, 1).all()
    txt = run_experiment84_report()
    assert "Bonferroni" in txt and "Deflated Sharpe" in txt
