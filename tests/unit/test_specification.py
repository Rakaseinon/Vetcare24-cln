"""Patrón Specification: composición AND / OR / NOT y razones de incumplimiento."""
import pytest

from src.domain.common import Specification

pytestmark = pytest.mark.unit


class Par(Specification[int]):
    nombre = "par"

    def is_satisfied_by(self, n: int) -> bool:
        return n % 2 == 0


class Mayor10(Specification[int]):
    nombre = "mayor_10"

    def is_satisfied_by(self, n: int) -> bool:
        return n > 10


@pytest.mark.parametrize("n,esperado", [(12, True), (11, False), (4, False), (3, False)])
def test_and(n, esperado):
    assert (Par() & Mayor10()).is_satisfied_by(n) is esperado


@pytest.mark.parametrize("n,esperado", [(12, True), (11, True), (4, True), (3, False)])
def test_or(n, esperado):
    assert (Par() | Mayor10()).is_satisfied_by(n) is esperado


def test_not():
    assert (~Par()).is_satisfied_by(3) and not (~Par()).is_satisfied_by(4)


def test_razones_de_incumplimiento():
    assert (Par() & Mayor10()).reasons(3) == ["par", "mayor_10"]
    assert (Par() & Mayor10()).reasons(4) == ["mayor_10"]
    assert (Par() & Mayor10()).reasons(12) == []
    assert (Par() | Mayor10()).reasons(3) == ["par", "mayor_10"]
    assert (Par() | Mayor10()).reasons(4) == []
    assert (~Par()).reasons(4) == ["NOT par"]
    assert (~Par()).reasons(3) == []


def test_nombre_compuesto():
    assert (Par() & ~Mayor10()).nombre == "(par AND NOT mayor_10)"
    assert Par().and_(Mayor10()).or_(Par()).nombre == "((par AND mayor_10) OR par)"
