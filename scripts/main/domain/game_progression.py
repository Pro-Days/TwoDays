from __future__ import annotations


def get_exp_data() -> list[int]:
    # 경험치 테이블 생성 규칙을 한 곳에 두어 계산 로직과 분리
    return [0] + [int(100 * 1.02**i) for i in range(0, 200)]
