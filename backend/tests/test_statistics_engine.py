import math
from app.services.statistics_engine import cohens_d_independent, cohens_dz, cronbach_alpha, describe, recommend

def test_describe():
    result=describe([1,2,3,4])
    assert result['n']==4
    assert result['mean']==2.5
    assert result['median']==2.5

def test_effect_sizes():
    assert cohens_d_independent([1,2,3],[2,3,4]) is not None
    assert cohens_dz([1,2,3],[2,3,5]) is not None

def test_cronbach():
    value=cronbach_alpha([[1,2,3],[2,3,4],[3,4,5],[4,5,6]])
    assert value is not None
    assert math.isclose(value,1.0,rel_tol=1e-6)

def test_recommendation():
    result=recommend('pre_post',True,'numeric',1)
    assert result['recommended_test']=='paired_t'
    assert result['required_columns']==['pre','post']
