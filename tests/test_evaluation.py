import importlib.util
from decimal import Decimal


def test_typed_result_comparison_observes_order_multiplicity_and_nulls():
    assert importlib.util.find_spec("queryguard.evaluation"), "Independent evaluator missing"
    from queryguard.evaluation import same_results

    assert same_results(
        [[Decimal("1.000001"), None], [2, "x"]], [[2, "x"], [Decimal("1"), None]], ordered=False
    )
    assert not same_results([[1], [2]], [[2], [1]], ordered=True)
    assert not same_results([[1], [1]], [[1]], ordered=False)
    assert not same_results([[True]], [[1]], ordered=False)
    assert not same_results([["1"]], [[1]], ordered=False)
    assert not same_results([[None]], [[0]], ordered=False)


def test_evaluator_executes_independent_reference_and_detects_wrong_answer():
    import queryguard.evaluation as evaluation

    assert hasattr(evaluation, "evaluate_cases"), "Executed evaluator missing"
    from queryguard.providers import TemplateProvider

    case = {
        "id": "probe",
        "question": "How many orders are there?",
        "expected_status": "accepted",
        "reference_sql": "SELECT count(*) + 1 FROM analytics.orders",
        "ordered": False,
    }
    report = evaluation.evaluate_cases([case], TemplateProvider(), "schema-aware")
    assert report[0]["passed"] is False
    assert report[0]["reference_rows"][0][0]["value"] == "361"
    assert report[0]["actual_rows"][0][0]["value"] == "360"
